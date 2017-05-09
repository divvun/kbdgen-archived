import os.path
import shutil
import subprocess
import tempfile
import sys

from collections import defaultdict, OrderedDict
from textwrap import indent, dedent

from .. import get_logger
from .base import *
from .osxutil import *

logger = get_logger(__file__)

class OSXGenerator(Generator):
    def generate(self, base='.'):
        self.build_dir = os.path.abspath(base)

        o = OrderedDict()

        for name, layout in self._project.layouts.items():
            logger.info("Generating '%s'..." % name)
            o[name] = self.generate_xml(layout)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        logger.info("Creating bundle...")
        bundle_path = self.create_bundle(self.build_dir)
        res_path = os.path.join(bundle_path, "Contents", "Resources")

        translations = defaultdict(dict)

        for name, data in o.items():
            layout = self._project.layouts[name]
            fn = layout.internal_name#layout.display_names[layout.locale]

            for locale, lname in layout.display_names.items():
                translations[locale][fn] = lname

            logger.debug("%s.keylayout -> bundle" % fn)
            with open(os.path.join(res_path, "%s.keylayout" % fn), 'w') as f:
                f.write(data)

            self.write_icon(res_path, layout)

        self.write_localisations(res_path, translations)

        logger.info("Creating installer...")
        self.create_installer(bundle_path)
        logger.info("Done!")

    def generate_iconset(self, icon, output_fn):
        cmd_tmpl = "convert -resize {d}x{d} -background transparent -gravity center -extent {d}x{d} {src} {out}"

        files = (
            ("icon_16x16", 16),
            ("icon_16x16@2x", 32),
            ("icon_32x32", 32),
            ("icon_32x32@2x", 64)
        )

        iconset = tempfile.TemporaryDirectory(suffix=".iconset")

        for name, dimen in files:
            fn = "%s.png" % name
            cmd = cmd_tmpl.format(d=dimen, src=icon, out=os.path.join(iconset.name, fn))

            logger.info("Creating '%s.png' at size %dx%d" % (name, dimen, dimen))
            process = subprocess.Popen(cmd, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(err.decode())
                logger.error("Application ended with error code %s." % process.returncode)
                # TODO throw exception instead.
                sys.exit(process.returncode)
        
        process = subprocess.Popen(["iconutil", "--convert", "icns",
                                    "--output", output_fn, iconset.name],
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        
        out, err = process.communicate()
        if process.returncode != 0:
            logger.error(err.decode())
            logger.error("Application ended with error code %s." % process.returncode)
            # TODO throw exception instead.
            sys.exit(process.returncode)
        
    def write_icon(self, res_path, layout):
        icon = self._project.target('osx').get('icon', None)
        if icon is None:
            logger.warning("no icon for layout '%s'." % layout.internal_name)
            return

        iconpath = self._project.relpath(icon)

        fn = os.path.join(res_path, "%s.icns" % layout.internal_name)
        self.generate_iconset(iconpath, fn)

    def write_localisations(self, res_path, translations):
        for locale, o in translations.items():
            path = os.path.join(res_path, "%s.lproj" % locale)
            os.makedirs(path)

            with open(os.path.join(path, "InfoPlist.strings"), 'w') as f:
                for name, lname in o.items():
                    f.write('"%s" = "%s";\n' % (name, lname))

    def create_bundle(self, path):
        bundle_path = os.path.join(path, "%s.bundle" % self._project.internal_name)
        bundle_name = self._project.target('osx').get('bundleName', None)

        if bundle_name is None:
            raise Exception("Target 'osx' has no 'bundleName' property. "
                "Please fix your project YAML file.")

        os.makedirs(os.path.join(bundle_path, 'Contents', 'Resources'),
            exist_ok=True)

        bundle_id = "%s.keyboardlayout.%s" % (
                self._project.target('osx')['packageId'],
                self._project.internal_name
            )

        target_tmpl = indent(dedent("""\
<key>KLInfo_%s</key>
<dict>
    <key>TISInputSourceID</key>
    <string>%s.%s</string>
    <key>TISIntendedLanguage</key>
    <string>%s</string>
</dict>"""), "        ")

        targets = []
        for name, layout in self._project.layouts.items():
            name = layout.internal_name#layout.display_names[layout.locale]
            bundle_chunk = name.lower().replace(' ', '')
            targets.append(target_tmpl % (name, bundle_id, bundle_chunk,
                layout.locale))

        with open(os.path.join(bundle_path, 'Contents', "Info.plist"), 'w') as f:
            f.write(dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>CFBundleIdentifier</key>
        <string>%s</string>
        <key>CFBundleName</key>
        <string>%s</string>
        <key>CFBundleVersion</key>
        <string>%s</string>
%s
    </dict>
</plist>
                """) % (
                    bundle_id,
                    bundle_name,
                    self._project.build,
                    '\n'.join(targets)
                )
            )

        return bundle_path

    def create_installer(self, bundle):
        cmd = ['productbuild', '--component',
                bundle, '/Library/Keyboard Layouts',
                "%s.pkg" % self._project.internal_name]

        process = subprocess.Popen(cmd, cwd=self.build_dir,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        out, err = process.communicate()

        if process.returncode != 0:
            logger.error(err.decode())
            logger.error("Application ended with error code %s." % (
                    process.returncode))
            sys.exit(process.returncode)

    def generate_xml(self, layout):
        #name = layout.display_names[layout.locale]
        name = layout.internal_name
        out = OSXKeyLayout(name, random_id())

        dead_keys = set(itertools.chain.from_iterable(layout.dead_keys.values()))
        action_keys = set()
        for x in DictWalker(layout.transforms):
            for i in x[0] + (x[1],):
                action_keys.add(str(i))

        # Naively add all keys
        for mode_name in OSXKeyLayout.modes:
            # TODO throw on null
            mode = layout.modes.get(mode_name, None)
            if mode is None:
                msg = "layout '%s' has no mode '%s'" % (
                    layout.internal_name, mode_name)
                if mode_name.startswith('osx-'):
                    logger.debug(msg)
                else:
                    logger.warning(msg)
                continue

            # All keymaps must include a code 0
            out.set_key(mode_name, '', '0')

            if isinstance(mode, dict):
                keyiter = mode_iter(layout, mode_name)
            else:
                keyiter = itertools.chain.from_iterable(mode)

            for (iso, key) in zip(ISO_KEYS, keyiter):
                if key is None:
                    continue
                key_id = OSX_KEYMAP[iso]

                if key in layout.dead_keys.get(mode_name, []):
                    if key in layout.transforms:
                        out.set_deadkey(mode_name, key, key_id,
                                layout.transforms[key].get(' ', key))
                    else:
                        logger.warning("Dead key '%s' not found in mode '%s'; "
                            "build will continue, but please fix." % (
                                key, mode_name
                            ))
                        out.set_key(mode_name, key, key_id)
                else:
                    out.set_key(mode_name, key, key_id)

                # Now cater for transforms too
                if key in action_keys and key not in dead_keys:
                    out.set_transform_key(mode_name, key, key_id)

            # Space bar special case
            sp = layout.special.get('space', {}).get(mode_name, " ")
            out.set_key(mode_name, sp, "49")
            out.set_transform_key(mode_name, sp, "49")

            # Add hardcoded keyboard bits
            for key_id, key in OSX_HARDCODED.items():
                out.set_key(mode_name, key, key_id)

        class TransformWalker(DictWalker):
            def on_branch(self, base, branch):
                action_id = out.actions.get(branch) # "Key %s" % branch

                if base == () and len(out.action_cache[action_id].xpath('when[@state="none"]')) > 0:
                    return
                elif base == ():
                    when_state = "none"
                    next_state = out.states.get(branch) # "State %s" % branch
                else:
                    when_state = out.states.get("".join(base)) # "State %s" % "".join(base)
                    next_state = "%s%s" % (when_state, branch)

                logger.trace("Branch: %r" % ((action_id, when_state, next_state),))

                try:
                    out.add_transform(action_id, when_state, next=next_state)
                except Exception as e:
                    logger.error("[%s] Error while adding transform:\n%s\n%r" % (
                        layout.internal_name, e,
                        (action_id, when_state, next_state)))

            def on_leaf(self, base, branch, leaf):
                action_id = out.actions.get(branch) # "Key %s" % branch
                when_state = out.states.get("".join(base)) # "State %s" % "".join(base)

                logger.trace("Leaf: %r" % ((action_id, when_state, leaf),))
                try:
                    out.add_transform(action_id, when_state,
                                      output=str(leaf))
                except Exception as e:
                    logger.error("[%s] Error while adding transform:\n%s\n%r" % (
                        layout.internal_name, e, (action_id, when_state, leaf)))

        TransformWalker(layout.transforms)()

        return bytes(out).decode('utf-8')
