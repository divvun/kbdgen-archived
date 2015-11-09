import plistlib
from textwrap import dedent, indent

from .. import get_logger
from .base import *
from .osxutil import *

logger = get_logger(__file__)

class AppleiOSGenerator(Generator):
    def generate(self, base='.'):
        # TODO sanity checks

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        build_dir = os.path.join(base, 'build',
                'ios', self._project.target('ios')['packageId'])

        if os.path.isdir(build_dir):
            git_update(build_dir, self.branch, base, logger=logger.info)
        else:
            git_clone(self.repo, build_dir, self.branch, base,
                    logger=logger.info)

        path = os.path.join(build_dir,
            'TastyImitationKeyboard.xcodeproj', 'project.pbxproj')
        pbxproj = Pbxproj(path)

        pbxproj.clear_target_dependencies("HostingApp")
        pbxproj.clear_target_embedded_binaries("HostingApp")

        # Keyboard plist
        with open(os.path.join(build_dir, 'Keyboard',
                    'Info.plist'), 'rb') as f:
            plist = plistlib.load(f, dict_type=OrderedDict)

        for name, layout in self._project.layouts.items():
            out_dir = os.path.join(build_dir, 'Generated', name)
            os.makedirs(out_dir, exist_ok=True)

            # Generate target
            pbxproj.duplicate_target('Keyboard',
                    name, os.path.relpath(os.path.join(out_dir, 'Info.plist'), build_dir))
            pbxproj.add_appex_to_target_embedded_binaries("%s.appex" % name, "HostingApp")

            # Generated swift file
            fn = os.path.join(out_dir, 'KeyboardLayout_%s.swift' % name)
            with open(fn, 'w') as f:
                f.write(self.generate_file(layout))
            pbxproj.add_path(['Generated', name])
            ref = pbxproj.add_swift_file(os.path.basename(fn))
            pbxproj.add_ref_to_group(ref, ['Generated', name])
            pbxproj.add_source_ref_to_build_phase(ref, name)

            with open(os.path.join(out_dir, 'Info.plist'), 'wb') as f:
                self.update_kbd_plist(plist.copy(), layout, f)
            ref = pbxproj.add_plist_file('Info.plist')
            pbxproj.add_ref_to_group(ref, ['Generated', name])

        # Hosting app plist
        with open(os.path.join(build_dir, 'HostingApp',
                    'Info.plist'), 'rb') as f:
            plist = plistlib.load(f, dict_type=OrderedDict)

        with open(os.path.join(build_dir, 'HostingApp',
                    'Info.plist'), 'wb') as f:
            self.update_plist(plist, f)

        # Create locale strings
        self.localise_hosting_app(pbxproj, build_dir)
        self.create_locales(build_dir)

        # Stops the original keyboard being built.
        pbxproj.remove_target("Keyboard")

        # Update pbxproj with locales
        with open(path, 'w') as f:
            self.update_pbxproj(pbxproj, f)

        # Generate icons for hosting app
        self.gen_hosting_app_icons(build_dir)

        if self.is_release:
            self.build_release(base, build_dir)
        else:
            logger.info("You may now open TastyImitationKeyboard.xcodeproj in '%s'." %\
                    build_dir)

    def build_release(self, base_dir, build_dir):
        # TODO check signing ID exists in advance (in sanity checks)

        xcarchive = os.path.abspath(os.path.join(base_dir, 'build', "%s.xcarchive" %\
                self._project.internal_name))
        ipa = os.path.abspath(os.path.join(base_dir, 'build', "%s.ipa" %\
                self._project.internal_name))

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        if os.path.exists(ipa):
            os.remove(ipa)

        projpath = ":".join(os.path.abspath(os.path.join(build_dir,
            'TastyImitationKeyboard.xcodeproj'))[1:].split(os.sep))

        applescript = dedent("""'
        tell application "Xcode"
            open "%s"

        end tell
        '""") % projpath

        code_sign_id = self._project.target('ios').get('codeSignId', '')
        provisioning_profile_id = self._project.target('ios').get(
                'provisioningProfileId', '')

        cmd0 = """/usr/bin/osascript -e %s""" % applescript
        cmd1 = """xcodebuild -configuration Release -scheme HostingApp archive
        -archivePath "%s" CODE_SIGN_IDENTITY="%s" """.replace("\n", ' ') % (
                xcarchive, code_sign_id)
        cmd2 = """xcodebuild -exportArchive -exportFormat ipa
        -archivePath "%s" -exportPath "%s"
        -exportProvisioningProfile "%s"
        """.replace('\n', ' ') % (
                xcarchive, ipa, provisioning_profile_id)

        for cmd, msg in (
                (cmd0, "Generating schemes..."),
                (cmd1, "Building .xcarchive..."),
                (cmd2, "Building .ipa and signing..."),
                ):

            logger.info(msg)
            process = subprocess.Popen(cmd, cwd=build_dir, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(err.decode())
                logger.error("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        logger.info("Done! -> %s" % ipa)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def gen_hosting_app_icons(self, build_dir):
        if self._project.icon('ios') is None:
            logger.warning("no icon supplied!")
            return

        path = os.path.join(build_dir, 'HostingApp',
                'Images.xcassets', 'AppIcon.appiconset')

        with open(os.path.join(path, "Contents.json")) as f:
            contents = json.load(f, object_pairs_hook=OrderedDict)

        cmd_tmpl = "convert -background white -alpha remove -resize %dx%d %s %s"

        for obj in contents['images']:
            scale = int(obj['scale'][:-1])
            h, w = obj['size'].split('x')
            h = int(h) * scale
            w = int(w) * scale

            icon = self._project.icon('ios', w)
            fn = "%s-%s@%s.png" % (obj['idiom'], obj['size'], obj['scale'])
            obj['filename'] = fn
            cmd = cmd_tmpl % (w, h, icon, os.path.join(path, fn))

            logger.info("Creating '%s' from '%s'..." % (fn, icon))

            # TODO create generic `launch_process` util func
            process = subprocess.Popen(cmd, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(err.decode())
                logger.error("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)

        with open(os.path.join(path, "Contents.json"), 'w') as f:
            json.dump(contents, f)


    def get_translatables_from_storyboard(self, xml_fn):
        with open(xml_fn) as f:
            tree = etree.parse(f)

        o = []
        for key, node, attr_node in [(n.attrib['value'], n.getparent().getparent(), n)
                for n in tree.xpath("//*[@keyPath='translate']")]:
            if 'placeholder' in node.attrib:
                o.append(("%s.placeholder" % node.attrib['id'], key))
            if 'text' in node.attrib or\
                    node.find("string[@key='text']") is not None:
                o.append(("%s.text" % node.attrib['id'], key))
            state_node = node.find('state')
            if state_node is not None:
                o.append(("%s.%sTitle" % (node.attrib['id'], state_node.attrib['key']), key))
            attr_node.getparent().remove(attr_node)
        o.sort()

        with open(xml_fn, 'w') as f:
            f.write(self._tostring(tree))

        return o

    def localise_hosting_app(self, pbxproj, gen_dir):
        base_dir = os.path.join(gen_dir, "HostingApp")
        xml_fn = os.path.join(base_dir, "Base.lproj", "Main.storyboard")

        trans_pairs = self.get_translatables_from_storyboard(xml_fn)

        for locale, o in self._project.app_strings.items():
            lproj_dir = "%s.lproj" % locale
            path = os.path.join(base_dir, lproj_dir)
            os.makedirs(path, exist_ok=True)

            with open(os.path.join(path, 'Main.strings'), 'ab') as f:
                for oid_path, key in trans_pairs:
                    if key in o:
                        self.write_l10n_str(f, oid_path, o[key])
                    else:
                        f.write(("/* Missing translation: %s */\n" %
                            key).encode('utf-8'))

        ref = pbxproj.add_plist_strings_to_variant_group(
                self._project.app_strings.keys(), "Main.storyboard", "Main.strings")


    def write_l10n_str(self, f, key, value):
        f.write(('"%s" = %s;\n' % (
            key, json.dumps(value, ensure_ascii=False))).encode('utf-8'))

    def create_locales(self, gen_dir):
        for locale, attrs in self._project.locales.items():
            lproj_dir = locale if locale != "en" else "Base"
            lproj = os.path.join(gen_dir, 'HostingApp', '%s.lproj' % lproj_dir)
            os.makedirs(lproj, exist_ok=True)

            with open(os.path.join(lproj, 'InfoPlist.strings'), 'ab') as f:
                self.write_l10n_str(f, 'CFBundleName', attrs['name'])
                self.write_l10n_str(f, 'CFBundleDisplayName', attrs['name'])

        for name, layout in self._project.layouts.items():
            for locale, lname in layout.display_names.items():
                lproj_dir = locale if locale != "en" else "Base"
                lproj = os.path.join(gen_dir, 'Generated', name, '%s.lproj' % lproj_dir)
                os.makedirs(lproj, exist_ok=True)

                with open(os.path.join(lproj, 'InfoPlist.strings'), 'ab') as f:
                    self.write_l10n_str(f, 'CFBundleName', lname)
                    self.write_l10n_str(f, 'CFBundleDisplayName', lname)

    def get_layout_locales(self, layout):
        locales = set(layout.display_names.keys())
        locales.remove('en')
        locales.add("Base")
        locales.add(layout.locale)
        return locales

    def get_project_locales(self):
        locales = set(self._project.locales.keys())
        locales.remove('en')
        locales.add("Base")
        return locales

    def get_all_locales(self):
        o = self.get_project_locales()

        for layout in self._project.layouts.values():
            o |= self.get_layout_locales(layout)

        return sorted(list(o))

    def update_pbxproj(self, pbxproj, f):
        pbxproj.root['knownRegions'] = self.get_all_locales()

        ref = pbxproj.add_plist_strings_to_build_phase(
                self.get_project_locales(), "HostingApp")
        pbxproj.add_ref_to_group(ref, ["HostingApp", "Supporting Files"])

        for name, layout in self._project.layouts.items():
            ref = pbxproj.add_plist_strings_to_build_phase(
                    self.get_layout_locales(layout), name)
            pbxproj.add_ref_to_group(ref, ["Generated", name])

        f.write(str(pbxproj))

    def update_kbd_plist(self, plist, layout, f):
        bundle_id = "%s.%s" % (
                self._project.target('ios')['packageId'],
                layout.internal_name.replace("_", "-"))

        plist['CFBundleName'] = layout.display_names['en']
        plist['CFBundleDisplayName'] = layout.display_names['en']
        plist['NSExtension']['NSExtensionAttributes']['PrimaryLanguage'] =\
                layout.locale
        plist['NSExtension']['NSExtensionPrincipalClass'] =\
                "${PRODUCT_MODULE_NAME}.%s" % layout.internal_name
        plist['CFBundleIdentifier'] = bundle_id
        plist['CFBundleShortVersionString'] = self._project.version
        plist['CFBundleVersion'] = self._project.build

        plistlib.dump(plist, f)

    def update_plist(self, plist, f):
        plist['CFBundleName'] = self._project.target('ios')['bundleName']
        plist['CFBundleDisplayName'] = self._project.target('ios')['bundleName']
        plist['CFBundleIdentifier'] = self._project.target('ios')['packageId']
        plist['CFBundleShortVersionString'] = self._project.version
        plist['CFBundleVersion'] = self._project.build

        plistlib.dump(plist, f)

    def generate_file(self, layout):
        buf = io.StringIO()

        ret_str = layout.strings.get('return', 'return')
        space_str = layout.strings.get('space', 'space')
        longpress_str = ("%r" % layout.longpress)[1:-1].replace("'", '"')
        if len(longpress_str) == 0:
            longpress_str = '"":[""]'

        l10n_name = layout.display_names.get(layout.locale, None)
        if l10n_name is None:
            raise Exception("Keyboard requires localisation " +
                            "into its own locale. (%s missing.)" % l10n_name)

        buf.write(dedent("""\
        // GENERATED FILE: DO NOT EDIT.

        import UIKit

        class %s: GiellaKeyboard {
            required init(coder: NSCoder) {
                fatalError("init(coder:) has not been implemented")
            }

            init() {
                var keyNames = ["keyboard": "%s", "return": "%s", "space": "%s"]

                var kbd = Keyboard()

                let isPad = UIDevice.currentDevice().userInterfaceIdiom == UIUserInterfaceIdiom.Pad

                let longPresses = %s.getLongPresses()

        """ % (layout.internal_name, l10n_name, ret_str,
                    space_str, layout.internal_name)))

        row_count = 0

        action_keys_start = indent(dedent("""\
        kbd.addKey(Key(.Shift), row: 2, page: 0)

        """), ' ' * 8)

        buf.write(action_keys_start)

        key_loop = indent(dedent("""\
        for key in ["%s"] {
            var model = Key(.Character)
            if let lp = longPresses[key]? {
                model.setUppercaseLongPress(lp)
            }
            if let lp = longPresses[key.lowercaseString]? {
                model.setLowercaseLongPress(lp)
            }
            model.setLetter(key)
            kbd.addKey(model, row: %s, page: 0)
        }

        """), ' ' * 8)

        for row in layout.modes['shift']:
            logger.critical(row)
            buf.write(key_loop % ('", "'.join(row), row_count))
            row_count += 1

        # There's this awful bug with the Swift parser where any sufficiently
        # long static literal dictionary of arrays causes the indexer to
        # freak out and die. Xcode 800% CPU anyone?
        # Workaround is to generate it slowly.
        buf.write(indent(dedent("""\
            if isPad {
                var returnKey = Key(.Return)
                returnKey.uppercaseKeyCap = keyNames["return"]
                returnKey.uppercaseOutput = "\\n"
                returnKey.lowercaseOutput = "\\n"

                var commaKey = Key(.SpecialCharacter)
                commaKey.uppercaseKeyCap = "!\\n,"
                commaKey.uppercaseOutput = "!"
                commaKey.lowercaseOutput = ","

                var fullStopKey = Key(.SpecialCharacter)
                fullStopKey.uppercaseKeyCap = "?\\n."
                fullStopKey.uppercaseOutput = "?"
                fullStopKey.lowercaseOutput = "."

                kbd.addKey(Key(.Backspace), row: 0, page: 0)
                kbd.addKey(returnKey, row: 1, page: 0)
                kbd.addKey(commaKey, row: 2, page: 0)
                kbd.addKey(fullStopKey, row: 2, page: 0)
                kbd.addKey(Key(.Shift), row: 2, page: 0)
            } else {
                kbd.addKey(Key(.Backspace), row: 2, page: 0)
            }

            super.init(keyboard: kbd, keyNames: keyNames)
        }

        class func getLongPresses() -> [String: [String]] {
            var lps = [String: [String]]()
        """), ' ' * 4))

        for k, v in layout.longpress.items():
            buf.write(indent(dedent("""\
                lps["%s"] = %s
            """ % (k, json.dumps(v, ensure_ascii=False))), ' ' * 8))

        buf.write('        return lps\n    }\n}\n')

        return buf.getvalue()
