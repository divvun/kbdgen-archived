import os.path
import shutil
import subprocess
import tempfile
import sys
import lxml.etree

from lxml.etree import Element, SubElement
from collections import defaultdict, OrderedDict
from textwrap import indent, dedent

from .. import get_logger
from .base import *
from .osxutil import *
from os import listdir

logger = get_logger(__file__)

class OSXGenerator(PhysicalGenerator):
    @property
    def disable_transforms(self):
        return "disable-transforms" in self._args["flags"]

    def generate(self, base='.'):
        self.build_dir = os.path.abspath(base)

        if self.disable_transforms:
            logger.critical("Dead keys and transforms will not be generated (disable-transforms)")

        o = OrderedDict()
            
        for name, layout in self.supported_layouts.items():
            try:
                self.validate_layout(layout)
            except Exception as e:
                logger.error("[%s] Error while validating layout:\n%s" % (
                        layout.internal_name, e))
                continue

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
            layout = self.supported_layouts[name]
            fn = layout.internal_name

            for locale, lname in layout.display_names.items():
                translations[locale][fn] = lname

            logger.debug("%s.keylayout -> bundle" % fn)
            with open(os.path.join(res_path, "%s.keylayout" % fn), 'w') as f:
                f.write(data)

            self.write_icon(res_path, layout)

        self.write_localisations(res_path, translations)

        logger.info("Creating installer...")
        pkg_path = self.create_installer(bundle_path)

        if self.is_release:
            logger.info("Signing installer...")
            self.sign_installer(pkg_path)

        logger.info("Done!")

    def generate_iconset(self, icon, output_fn):
        cmd_tmpl = "convert -resize {d}x{d} -background transparent -gravity center -extent {d}x{d}"

        files = (
            ("icon_16x16", 16),
            ("icon_16x16@2x", 32),
            ("icon_32x32", 32),
            ("icon_32x32@2x", 64)
        )

        iconset = tempfile.TemporaryDirectory(suffix=".iconset")

        for name, dimen in files:
            fn = "%s.png" % name
            cmd = cmd_tmpl.format(d=dimen).split(" ") + [icon, os.path.join(iconset.name, fn)]
            logger.info("Creating '%s.png' at size %dx%d" % (name, dimen, dimen))
            run_process(cmd)
        
        cmd = ["iconutil", "--convert", "icns",
               "--output", output_fn, iconset.name]
        run_process(cmd)

        iconset.cleanup()
        
    def write_icon(self, res_path, layout):
        icon = layout.target('osx').get('icon', None)

        # Get base icon
        if icon is None:
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
        # Bundle ID must contain be in format *.keyboardlayout.<name>
        # Failure to do so and the bundle will not be detected as a keyboard bundle
        bundle_id = "%s.keyboardlayout.%s" % (
                self._project.target('osx')['packageId'],
                self._project.internal_name
            )
        bundle_path = os.path.join(path, "%s.bundle" % bundle_id)
        bundle_name = self._project.target('osx').get('bundleName', None)

        if bundle_name is None:
            raise Exception("Target 'osx' has no 'bundleName' property. "
                "Please fix your project YAML file.")

        os.makedirs(os.path.join(bundle_path, 'Contents', 'Resources'),
            exist_ok=True)

        target_tmpl = indent(dedent("""\
<key>KLInfo_%s</key>
<dict>
    <key>TISInputSourceID</key>
    <string>%s.%s</string>
    <key>TISIntendedLanguage</key>
    <string>%s</string>
</dict>"""), "        ")

        targets = []
        for name, layout in self.supported_layouts.items():
            name = layout.internal_name
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
        <key>CFBundleShortVersionString</key>
        <string>%s</string>
%s
    </dict>
</plist>
                """) % (
                    bundle_id,
                    bundle_name,
                    self._project.target("osx").get("build", "1"),
                    self._project.target("osx").get("version", "0.0.0"),
                    '\n'.join(targets)
                )
            )

        return bundle_path

    def generate_distribution_xml(self, component_fn, working_dir):
        dist_fn = os.path.join(working_dir.name, "distribution.xml")
        bundle_name = self._project.target('osx').get('bundleName', None)
        bundle_id = self._project.target('osx')['packageId']

        root = etree.fromstring("""<installer-gui-script minSpecVersion="2" />""") #tree.getroot()

        SubElement(root, "title").text = bundle_name
        SubElement(root, "options", customize="never", rootVolumeOnly="true")

        choices_outline = SubElement(root, "choices-outline")
        line = SubElement(choices_outline, "line", choice="default")
        SubElement(line, "line", choice=bundle_id)

        SubElement(root, "choice", id="default")
        choice = SubElement(root, "choice", id=bundle_id, visible="false")
        SubElement(choice, "pkg-ref", id=bundle_id)

        SubElement(root, "pkg-ref", id=bundle_id, version="0", auth="root").text = os.path.basename(component_fn)

        target = self._project.target('osx')

        bg = target.get('background', None)
        if bg is not None:
            SubElement(root, 'background', file=bg, alignment="bottomleft")

        for key in ("license", "welcome", "readme", "conclusion"):
            fn = target.get(key, None)
            if fn is not None:
                SubElement(root, key, file=fn)

        with open(dist_fn, 'wb') as f:
            f.write(etree.tostring(root, 
                xml_declaration=True,
                encoding='utf-8',
                pretty_print=True))
        
        return dist_fn

    def create_component_pkg(self, bundle, version, working_dir):
        pkg_name = "%s.pkg" % self._project.target('osx')['packageId']
        pkg_path = os.path.join(working_dir.name, pkg_name)

        cmd = ['pkgbuild', 
               '--component', os.path.join(working_dir.name, bundle),
               '--ownership', 'recommended',
               "--install-location", '/Library/Keyboard Layouts',
               "--version", version,
               pkg_path]

        out, err = run_process(cmd, self.build_dir)

        return pkg_path

    def create_installer(self, bundle):
        working_dir = tempfile.TemporaryDirectory()
        version = self._project.target("osx").get("version", None)

        if version is None:
            logger.warn("No version for installer specified; defaulting to '0.0.0'.")
            version = "0.0.0"

        component_pkg_path = self.create_component_pkg(bundle, version, working_dir)
        
        resources = self._project.target("osx").get("resources", None)
        if resources is not None:
            resources = self._project.relpath(resources)

        dist_xml_path = self.generate_distribution_xml(
            component_pkg_path, working_dir)

        pkg_name = "%s %s.unsigned.pkg" % (self._project.target('osx')['bundleName'], version)

        cmd = ['productbuild',
               "--distribution", dist_xml_path,
               "--version", version,
               '--package-path', working_dir.name]
        
        if resources is not None:
            cmd += ["--resources", resources]
               
        cmd += [pkg_name]

        run_process(cmd, self.build_dir)

        working_dir.cleanup()
        return os.path.join(self.build_dir, pkg_name)
    
    def sign_installer(self, pkg_path):
        version = self._project.target("osx").get("version", None)

        if version is None:
            logger.critical("A version must be defined for a signed package. Add a version property to targets.osx in your project.yaml.")
            sys.exit(1)

        signed_path = "%s %s.pkg" % (self._project.target('osx')['bundleName'], version)

        sign_id = self._project.target('osx').get("codeSignId", None)

        if sign_id is None:
            logger.error("No signing identify found; skipping.")
            return

        cmd = ['productsign', '--sign', sign_id, pkg_path, signed_path]
        run_process(cmd, self.build_dir)

        cmd = ['pkgutil', '--check-signature', signed_path]
        out, err = run_process(cmd, self.build_dir)

        logger.info(out.decode().strip())

    def generate_xml(self, layout):
        #name = layout.display_names[layout.locale]
        name = layout.internal_name
        out = OSXKeyLayout(name, random_id())
        walker_errors = 0

        dead_keys = set(itertools.chain.from_iterable(layout.dead_keys.values()))
        action_keys = set()
        for x in DictWalker(layout.transforms):
            for i in x[0] + (x[1],):
                action_keys.add(str(i))

        # Naively add all keys
        for mode_name in OSXKeyLayout.modes:
            logger.trace("BEGINNING MODE: %r" % mode_name)
            
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

            logger.trace("Dead keys - mode:%r keys:%r" % (mode_name, layout.dead_keys.get(mode_name, [])))

            for iso, key in mode.items():
                if key is None:
                    key = ""

                key_id = OSX_KEYMAP[iso]

                if self.disable_transforms:
                    out.set_key(mode_name, key, key_id)
                    continue

                if key in layout.dead_keys.get(mode_name, []):
                    logger.trace("Dead key found - mode:%r key:%r" % (mode_name, key))
                    
                    if key in layout.transforms:
                        logger.trace("Set deadkey - mode:%r key:%r id:%r" % (mode_name, key, key_id))
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
                    logger.trace("Transform - mode:%r key:%r id:%r" % (mode_name, key, key_id))
                    out.set_transform_key(mode_name, key, key_id)

            # Space bar special case
            sp = layout.special.get('space', {}).get(mode_name, " ")
            out.set_key(mode_name, sp, "49")
            if not self.disable_transforms:
                out.set_transform_key(mode_name, sp, "49")

            # Add hardcoded keyboard bits
            for key_id, key in OSX_HARDCODED.items():
                out.set_key(mode_name, key, key_id)

        class TransformWalker(DictWalker):
            def on_branch(self, base, branch):
                logger.trace("BRANCH: %r" % branch)
                if branch not in dead_keys or not out.actions.has(branch):
                    logger.error("Transform %r not supported; is a deadkey missing?" % branch)
                    return False

                action_id = out.actions.get(branch) # "Key %s" % branch

                if base == ():
                    action = out.action_cache.get(action_id, None)
                    if action is not None:
                        if len(action.xpath('when[@state="none"]')) > 0:
                            return
                    when_state = "none"
                    next_state = out.states.get(branch) # "State %s" % branch
                else:
                    when_state = out.states.get("".join(base)) # "State %s" % "".join(base)
                    next_state = "%s%s" % (when_state, branch)

                logger.trace("Branch: action:%r when:%r next:%r" % (action_id, when_state, next_state))

                try:
                    out.add_transform(action_id, when_state, next=next_state)
                except Exception as e:
                    w()
                    logger.error("[%s] Error while adding branch transform:\n%s\n%r" % (
                        layout.internal_name, e,
                        (branch, action_id, when_state, next_state)))

            def on_leaf(self, base, branch, leaf):
                if not out.actions.has(branch):
                    logger.debug("Leaf transform %r not supported. Is a deadkey missing?" % branch)
                    return

                action_id = out.actions.get(branch) # "Key %s" % branch
                when_state = out.states.get("".join(base)) # "State %s" % "".join(base)

                logger.trace("Leaf: action:%r when:%r leaf:%r" % (action_id, when_state, leaf))
                try:
                    out.add_transform(action_id, when_state,
                                      output=str(leaf))
                except Exception as e:
                    w()
                    logger.error("[%s] Error while adding leaf transform:\n%s\n%r" % (
                        layout.internal_name, e, (action_id, when_state, leaf)))
        
        if not self.disable_transforms:
            TransformWalker(layout.transforms)()

        return bytes(out).decode('utf-8')
