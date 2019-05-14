import os.path
import shutil
import itertools
import tempfile
import sys
import re
from lxml import etree
import binascii

from lxml.etree import SubElement
from collections import defaultdict, OrderedDict
from textwrap import indent, dedent

from ..base import get_logger
from .base import PhysicalGenerator, run_process, DictWalker, DesktopLayoutView
from .osxutil import OSXKeyLayout, OSX_HARDCODED, OSX_KEYMAP

logger = get_logger(__file__)

INVERTED_ID_RE = re.compile(r"[^A-Za-z0-9]")


class MacGenerator(PhysicalGenerator):
    @property
    def disable_transforms(self):
        return "disable-transforms" in self._args["flags"]

    @property
    def mac_target(self):
        return self._bundle.targets.get("mac", {})

    @property
    def mac_resources(self):
        return self._bundle.resources("mac")

    @property
    # @lru_cache(maxsize=1)
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "mac" in v.modes or "desktop" in v.modes:
                o[k] = v
        return o

    @property
    def sign_id(self):
        return self.mac_target.code_sign_id or os.environ.get("CODE_SIGN_ID")

    def sanity_check(self):
        if super().sanity_check() is False:
            return False

        if shutil.which("pkgbuild") is None:
            logger.error("'pkgbuild' not found on PATH; are you running on macOS?")
            return False

        if shutil.which("productbuild") is None:
            logger.error("'productbuild' not found on PATH; are you running on macOS?")
            return False

        if self.sign_id is None:
            logger.error("No signing identify found, release build not possible.")
            logger.error("Add `codeSignId` property to mac target yaml or set CODE_SIGN_ID environment variable.")
            return False

        fail = False
        ids = []
        for locale, layout in self.supported_layouts.items():
            id_ = self._layout_name(locale, layout)
            if id_ in ids:
                logger.error("A duplicate internal name was detected: '%s'." % id_)
            else:
                ids.append(id_)
        if fail:
            logger.error(
                "macOS keyboard internal names are converted to only contain "
                + "A-Z, a-z, and 0-9.  Please ensure your internal names are "
                + "still unique after this process."
            )
        return not fail

    def generate(self, base="."):
        if not self.sanity_check():
            return

        self.build_dir = os.path.abspath(base)

        # Flag used for debugging, not for general use and undocumented
        if self.disable_transforms:
            logger.critical(
                "Dead keys and transforms will not be generated (disable-transforms)"
            )

        o = OrderedDict()

        for name, layout in self.supported_layouts.items():
            try:
                self.validate_layout(layout, "mac")
            except Exception as e:
                logger.error(
                    "[%s] Error while validating layout:\n%s"
                    % (name, e)
                )
                raise e
                return

            logger.info("Generating '%s'…" % name)
            o[name] = self.generate_xml(name, layout)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        logger.info("Creating bundle…")
        bundle_path = self.create_bundle(self.build_dir)
        res_path = os.path.join(bundle_path, "Contents", "Resources")

        translations = defaultdict(dict)

        for name, data in o.items():
            layout = self.supported_layouts[name]
            fn = self._layout_name(name, layout)

            for locale, lname in layout.display_names.items():
                translations[locale][fn] = lname

            logger.debug("%s.keylayout -> bundle" % fn)
            with open(os.path.join(res_path, "%s.keylayout" % fn), "w") as f:
                f.write(data)

            self.write_icon(res_path, name, layout)

        self.write_localisations(res_path, translations)

        logger.info("Creating installer…")
        pkg_path = self.create_installer(bundle_path)

        if self.is_release:
            logger.info("Signing installer…")
            self.sign_installer(pkg_path)
        else:
            logger.info("Installer generated at '%s'." % pkg_path)

    def generate_iconset(self, icon, output_fn):
        cmd_tmpl = (
            "convert -resize {d}x{d} -background transparent "
            + "-gravity center -extent {d}x{d}"
        )

        files = (
            ("icon_16x16", 16),
            ("icon_16x16@2x", 32),
            ("icon_32x32", 32),
            ("icon_32x32@2x", 64),
        )

        iconset = tempfile.TemporaryDirectory(suffix=".iconset")

        for name, dimen in files:
            fn = "%s.png" % name
            cmd = cmd_tmpl.format(d=dimen).split(" ") + [
                icon,
                os.path.join(iconset.name, fn),
            ]
            logger.info("Creating '%s.png' at size %dx%d" % (name, dimen, dimen))
            run_process(cmd)

        cmd = ["iconutil", "--convert", "icns", "--output", output_fn, iconset.name]
        run_process(cmd)

        iconset.cleanup()

    def layout_target(self, layout):
        if layout.targets is not None:
            return layout.targets.get("mac", {})
        return {}

    def write_icon(self, res_path, name, layout):
        try:
            for x in os.listdir(self.mac_resources):
                if x.startswith("icon.%s." % name):
                    icon = x
                    break
            else:
                logger.warning("no icon for layout '%s'." % name)
                return
        except:
            logger.debug("No resources directory.")
            return

        iconpath = os.path.join(self.mac_resources, icon)

        fn = os.path.join(res_path, "%s.icns" % self._layout_name(name, layout))
        self.generate_iconset(iconpath, fn)

    def write_localisations(self, res_path, translations):
        for locale, o in translations.items():
            path = os.path.join(res_path, "%s.lproj" % locale)
            os.makedirs(path)

            with open(os.path.join(path, "InfoPlist.strings"), "w") as f:
                for name, lname in o.items():
                    f.write('"%s" = "%s";\n' % (name, lname))

    def _layout_name(self, locale, layout):
        return INVERTED_ID_RE.sub("", locale)

    def create_bundle(self, path):
        # Bundle ID must contain be in format *.keyboardlayout.<name>
        # Failure to do so and the bundle will not be detected as a keyboard bundle
        bundle_id = "%s.keyboardlayout.%s" % (
            self.mac_target.package_id,
            self._bundle.name
        )

        bundle_path = os.path.join(path, "%s.bundle" % bundle_id)
        if os.path.exists(bundle_path):
            shutil.rmtree(bundle_path)
        bundle_name = self.mac_target.bundle_name

        if bundle_name is None:
            raise Exception(
                "Target 'osx' has no 'bundleName' property. "
                "Please fix your project YAML file."
            )

        os.makedirs(os.path.join(bundle_path, "Contents", "Resources"), exist_ok=True)

        target_tmpl = indent(
            dedent(
                """\
<key>KLInfo_%s</key>
<dict>
    <key>TISInputSourceID</key>
    <string>%s.%s</string>
    <key>TISIntendedLanguage</key>
    <string>%s</string>
</dict>"""
            ),
            "        ",
        )

        targets = []
        for name, layout in self.supported_layouts.items():
            layout_name = self._layout_name(name, layout)
            targets.append(
                target_tmpl % (layout_name, bundle_id, layout_name, name)
            )

        with open(os.path.join(bundle_path, "Contents", "Info.plist"), "w") as f:
            f.write(
                dedent(
                    """\
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
                """  # noqa: E501
                )
                % (
                    bundle_id,
                    bundle_name,
                    self.mac_target.build,
                    self.mac_target.version,
                    "\n".join(targets),
                )
            )

        return bundle_path

    def generate_distribution_xml(self, component_fn, working_dir):
        dist_fn = os.path.join(working_dir.name, "distribution.xml")
        bundle_name = self.mac_target.bundle_name
        # Root "bundle id" is used as a unique key only in the pkg xml
        bundle_id = self.mac_target.package_id

        root = etree.fromstring("""<installer-gui-script minSpecVersion="2" />""")

        SubElement(root, "title").text = bundle_name
        SubElement(root, "options", customize="never", rootVolumeOnly="true")

        choices_outline = SubElement(root, "choices-outline")
        line = SubElement(choices_outline, "line", choice="default")
        SubElement(line, "line", choice=bundle_id)

        SubElement(root, "choice", id="default")
        choice = SubElement(root, "choice", id=bundle_id, visible="false")
        SubElement(choice, "pkg-ref", id=bundle_id)

        SubElement(
            root,
            "pkg-ref",
            id=bundle_id,
            version="0",
            auth="root",
            onConclusion="RequireRestart",
        ).text = os.path.basename(component_fn)

        bg = self.resource_with_prefix("background")
        if bg is not None:
            SubElement(root, "background", file=bg, alignment="bottomleft")

        for key in ("license", "welcome", "readme", "conclusion"):
            fn = self.resource_with_prefix(key)
            if fn is not None:
                SubElement(root, key, file=fn)

        with open(dist_fn, "wb") as f:
            f.write(
                etree.tostring(
                    root, xml_declaration=True, encoding="utf-8", pretty_print=True
                )
            )

        return dist_fn

    def resource_with_prefix(self, fn_prefix):
        try:
            files = os.listdir(self.mac_resources)
        except Exception:
            # No directory, no problem.
            return None
        
        for fn in files:
            if fn_prefix == os.path.splitext(fn)[0]:
                return os.path.join(self.mac_resources, fn)
        return None

    def create_component_pkg(self, bundle, version, working_dir):
        pkg_name = "%s.pkg" % self.mac_target.package_id
        pkg_path = os.path.join(working_dir.name, pkg_name)

        cmd = [
            "pkgbuild",
            "--component",
            os.path.join(working_dir.name, bundle),
            "--ownership",
            "recommended",
            "--install-location",
            "/Library/Keyboard Layouts",
            "--version",
            version,
            pkg_path,
        ]

        out, err = run_process(cmd, self.build_dir)

        return pkg_path

    def create_installer(self, bundle):
        working_dir = tempfile.TemporaryDirectory()
        version = self.mac_target.version

        if version is None:
            logger.warn("No version for installer specified; defaulting to '0.0.0'.")
            version = "0.0.0"

        component_pkg_path = self.create_component_pkg(bundle, version, working_dir)

        resources = self.mac_resources
        if resources is not None:
            resources = self._bundle.relpath(resources)

        dist_xml_path = self.generate_distribution_xml(component_pkg_path, working_dir)

        bundle_name = self.mac_target.bundle_name.replace(" ", "_")
        pkg_name = "%s_%s.unsigned.pkg" % (bundle_name, version)

        cmd = [
            "productbuild",
            "--distribution",
            dist_xml_path,
            "--version",
            version,
            "--package-path",
            working_dir.name,
        ]

        if resources is not None:
            cmd += ["--resources", resources]

        cmd += [pkg_name]

        run_process(cmd, self.build_dir)

        working_dir.cleanup()
        return os.path.join(self.build_dir, pkg_name)

    def sign_installer(self, pkg_path):
        version = self.mac_target.version

        if version is None:
            logger.critical(
                "A version must be defined for a signed package. Add a version "
                + "property to targets.osx in your project.yaml."
            )
            sys.exit(1)

        signed_path = "%s %s.pkg" % (self.mac_target.bundle_name, version)

        cmd = ["productsign", "--sign", self.sign_id, pkg_path, signed_path]
        run_process(cmd, self.build_dir)

        cmd = ["pkgutil", "--check-signature", signed_path]
        out, err = run_process(cmd, self.build_dir)

        logger.info(out.decode().strip())
        logger.info(
            "Installer generated at '%s'." % os.path.join(self.build_dir, signed_path)
        )

    def _layout_id(self, name) -> str:
        return str(
            -min(
                max(binascii.crc_hqx(name.encode("utf-8"), 0) // 2, 1),
                32768,
            )
        )

    def _numpad(self, decimal):
        return (
            (65, decimal),
            (67, "*"),
            (69, "+"),
            (75, "/"),
            (78, "-"),
            (81, "="),
            (82, "0"),
            (83, "1"),
            (84, "2"),
            (85, "3"),
            (86, "4"),
            (87, "5"),
            (88, "6"),
            (89, "7"),
            (91, "8"),
            (92, "9")
        )

    def generate_xml(self, name, layout):
        name = self._layout_name(name, layout)
        out = OSXKeyLayout(name, self._layout_id(name))

        layout_view = DesktopLayoutView(layout, "mac")

        # Create list to ignore false negatives for different targets
        dead_key_lists = [v for v in [k.values() for k in layout.dead_keys.values()]]
        all_dead_keys = set(itertools.chain.from_iterable([k for sublist in dead_key_lists for k in sublist]))
        
        dead_keys = set(itertools.chain.from_iterable(layout_view.dead_keys().values()))
        action_keys = set()
        for x in DictWalker(layout.transforms):
            for i in x[0] + (x[1],):
                action_keys.add(str(i))

        # Naively add all keys
        for mode_name in OSXKeyLayout.modes:
            logger.trace("BEGINNING MODE: %r" % mode_name)

            mode = layout_view.mode(mode_name)
            if mode is None:
                msg = "layout '%s' has no mode '%s'" % (name, mode_name)
                if mode_name.startswith("cmd") or mode_name.startswith("caps"):
                    logger.debug(msg)
                else:
                    logger.warning(msg)
                continue

            # All keymaps must include a code 0
            out.set_key(mode_name, "", "0")

            logger.trace(
                "Dead keys - mode:%r keys:%r"
                % (mode_name, layout.dead_keys.get(mode_name, []))
            )

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
                        logger.trace(
                            "Set deadkey - mode:%r key:%r id:%r"
                            % (mode_name, key, key_id)
                        )
                        out.set_deadkey(
                            mode_name, key, key_id, layout.transforms[key].get(" ", key)
                        )
                    else:
                        logger.warning(
                            "Dead key '%s' not found in mode '%s'; "
                            "build will continue, but please fix." % (key, mode_name)
                        )
                        out.set_key(mode_name, key, key_id)
                else:
                    out.set_key(mode_name, key, key_id)

                # Now cater for transforms too
                if key in action_keys and key not in dead_keys:
                    logger.trace(
                        "Transform - mode:%r key:%r id:%r" % (mode_name, key, key_id)
                    )
                    out.set_transform_key(mode_name, key, key_id)

            # Space bar special case
            if layout.space is not None:
                sp = layout.space.get("mac", {}).get(mode_name, " ")
            else:
                sp = " "

            out.set_key(mode_name, sp, "49")
            if not self.disable_transforms and len(layout.transforms) > 0:
                out.set_transform_key(mode_name, sp, "49")

            # Add hardcoded keyboard bits
            for key_id, key in OSX_HARDCODED.items():
                out.set_key(mode_name, key, key_id)

            # Add numpad
            decimal = "." if mode_name == "ctrl" else (layout.decimal or ".")
            for key_id, key in self._numpad(decimal):
                out.set_key(mode_name, str(key), str(key_id))

        class TransformWalker(DictWalker):
            def on_branch(self, base, branch):
                logger.debug("BRANCH: %r" % branch)
                if branch not in dead_keys or not out.actions.has(branch):
                    if branch in all_dead_keys:
                        logger.debug("Transform %r not supported by current target." % branch)
                    else:
                        logger.error(
                            "Transform %r not supported; is a deadkey missing?" % branch
                        )
                    return False

                action_id = out.actions.get(branch)  # "Key %s" % branch

                if base == ():
                    action = out.action_cache.get(action_id, None)
                    if action is not None:
                        if len(action.xpath('when[@state="none"]')) > 0:
                            return
                    when_state = "none"
                    next_state = out.states.get(branch)  # "State %s" % branch
                else:
                    when_state = out.states.get(
                        "".join(base)
                    )  # "State %s" % "".join(base)
                    next_state = "%s%s" % (when_state, branch)

                logger.trace(
                    "Branch: action:%r when:%r next:%r"
                    % (action_id, when_state, next_state)
                )

                try:
                    out.add_transform(action_id, when_state, next=next_state)
                except Exception as e:
                    logger.error(
                        "[%s] Error while adding branch transform:\n%s\n%r"
                        % (
                            name,
                            e,
                            (branch, action_id, when_state, next_state),
                        )
                    )

            def on_leaf(self, base, branch, leaf):
                if not out.actions.has(branch):
                    logger.debug(out.actions)
                    logger.debug(
                        "Leaf (%r) transform %r not supported. Is a deadkey missing?"
                        % (leaf, branch)
                    )
                    return

                action_id = out.actions.get(branch)  # "Key %s" % branch
                when_state = out.states.get("".join(base))  # "State %s" % "".join(base)

                logger.trace(
                    "Leaf: action:%r when:%r leaf:%r" % (action_id, when_state, leaf)
                )
                try:
                    out.add_transform(action_id, when_state, output=str(leaf))
                except Exception as e:
                    logger.error(
                        "[%s] Error while adding leaf transform:\n%s\n%r"
                        % (name, e, (action_id, when_state, leaf))
                    )

        if not self.disable_transforms:
            TransformWalker(layout.transforms)()

        return bytes(out).decode("utf-8")
