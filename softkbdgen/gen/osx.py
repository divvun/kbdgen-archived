import os.path
import shutil
import subprocess

from textwrap import indent, dedent

from .. import get_logger
from .base import *
from .osxutil import *

logger = get_logger(__file__)

class OSXGenerator(Generator):
    def generate(self, base='.'):
        self.build_dir = os.path.abspath(os.path.join(base, 'build',
                'osx', self._project.internal_name))

        o = OrderedDict()

        for name, layout in self._project.layouts.items():
            logger.info("Generating '%s'..." % name)
            o[name] = self.generate_xml(layout)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        bundle = os.path.join(self.build_dir,
                 "%s.bundle" % self._project.internal_name)

        logger.info("Creating bundle...")
        bundle_path = self.create_bundle(self.build_dir)
        res_path = os.path.join(bundle_path, "Contents", "Resources")

        for name, data in o.items():
            layout = self._project.layouts[name]
            fn = layout.display_names[layout.locale]
            logger.debug("%s.keylayout -> bundle" % fn)
            with open(os.path.join(res_path, "%s.keylayout" % fn), 'w') as f:
                f.write(data)

        logger.info("Creating installer...")
        self.create_installer(bundle_path)
        logger.info("Done!")

    def create_bundle(self, path):
        bundle_path = os.path.join(path, "%s.bundle" % self._project.internal_name)
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
            name = layout.display_names[layout.locale]
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
                    self._project.target('osx')['bundleName'],
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
        name = layout.display_names[layout.locale]
        out = OSXKeyLayout(name, random_id())

        if 'osx-cmd' not in layout.modes:
            layout.modes['osx-cmd'] = OSXKeyLayout.DEFAULT_CMD
        if 'osx-cmd+shift' not in layout.modes:
            layout.modes['osx-cmd+shift'] = OSXKeyLayout.DEFAULT_CMD_SHIFT

        action_keys = set()
        for x in DictWalker(layout.transforms):
            for i in x[:-1]:
                action_keys.add(str(i))

        # Naively add all keys
        for mode_name in OSXKeyLayout.modes:
            # TODO throw on null
            mode = layout.modes.get(mode_name, None)
            if mode is None:
                logger.warning("layout '%s' has no mode '%s'" % (
                    layout.internal_name, mode_name))
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
                    out.set_deadkey(mode_name, key, key_id,
                            layout.transforms[key].get(' ', key))
                else:
                    out.set_key(mode_name, key, key_id)

                # Now cater for transforms too
                if key in action_keys:
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
                action_id = "Key %s" % branch

                if base == ():
                    when_state = "none"
                    next_state = "State %s" % branch
                else:
                    when_state = "State %s" % "".join(base)
                    next_state = "%s%s" % (when_state, branch)

                logger.trace("Branch: %r" % ((action_id, when_state, next_state),))

                try:
                    out.add_transform(action_id, when_state, next=next_state)
                except Exception as e:
                    logger.error("[%s] Error while adding transform:\n%s\n%r" % (
                        layout.internal_name, e,
                        (action_id, when_state, next_state)))

            def on_leaf(self, base, branch, leaf):
                action_id = "Key %s" % branch
                when_state = "State %s" % "".join(base)

                logger.trace("Leaf: %r" % ((action_id, when_state, leaf),))
                try:
                    out.add_transform(action_id, when_state,
                                      output=str(leaf))
                except Exception as e:
                    logger.error("[%s] Error while adding transform:\n%s\n%r" % (
                        layout.internal_name, e, (action_id, when_state, leaf)))

        TransformWalker(layout.transforms)()

        return bytes(out).decode('utf-8')

