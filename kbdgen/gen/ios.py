import plistlib
import sys
import re
import shutil
import glob
import multiprocessing
import tarfile
import tempfile
from textwrap import dedent, indent
from pathlib import Path

from .. import get_logger
from ..filecache import FileCache
from .base import *
from .osxutil import *

logger = get_logger(__file__)

VERSION_RE = re.compile(r'Xcode (\d+)\.(\d+)')

class AppleiOSGenerator(Generator):
    @property
    def _version(self):
        return self._project.target("ios").get("version", self._project.version)

    @property
    def _build(self):
        return self._project.target("ios").get("build", self._project.build)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = FileCache()

    def get_source_tree(self, base, repo="divvun/giellakbd-ios", branch="master"):
        """Downloads the IME source from Github as a tarball, then extracts to deps dir."""
        logger.info("Getting source files…")

        deps_dir = Path(os.path.join(base, 'ios-build'))
        shutil.rmtree(str(deps_dir), ignore_errors=True)

        tarball = self.cache.download_latest_from_github(repo, branch)

        with tempfile.TemporaryDirectory() as tmpdir:
            tarfile.open(tarball, 'r:gz').extractall(str(tmpdir))
            target = [x for x in Path(tmpdir).iterdir() if x.is_dir()][0]
            os.makedirs(str(deps_dir.parent), exist_ok=True) 
            Path(target).rename(deps_dir)

    @property
    def pkg_id(self):
        return self._project.target('ios')['packageId'].replace("_", "-")

    def generate(self, base='.'):
        if not self.ensure_xcode_version():
            return

        if not self.sanity_check():
            return

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        self.get_source_tree(base, branch=self.branch)
        deps_dir = os.path.join(base, 'ios-build')

        path = os.path.join(deps_dir,
                            'GiellaKeyboard.xcodeproj', 
                            'project.pbxproj')
        if not os.path.isfile(path):
            logger.error("No Xcode project found. Did you use the correct repository?")
            return
        pbxproj = Pbxproj(path)

        layouts = []
        for name, layout in self.supported_layouts.items():
            layouts.append(self.generate_json_layout(name, layout))

        fn = os.path.join(deps_dir, "Keyboard", "KeyboardDefinitions.json")
        with open(fn, 'w') as f:
            json.dump(layouts, f, indent=2)

        plist_path = os.path.join(deps_dir, 'HostingApp', 'Info.plist')

        # Hosting app plist
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f, dict_type=OrderedDict)
        with open(plist_path, 'wb') as f:
            self.update_plist(plist, f)

        kbd_plist_path = os.path.join(deps_dir, 'Keyboard', 'Info.plist')
        dev_team = self._project.target("ios").get("codeSignId", None)

        with open(kbd_plist_path, 'rb') as f:
            kbd_plist = plistlib.load(f, dict_type=OrderedDict)

            for n, layout in enumerate(self.supported_layouts.values()):
                name = layout.internal_name
                os.makedirs(os.path.join(deps_dir, 'Keyboard', name), exist_ok=True)
                plist_gpath = os.path.join('Keyboard', name, "Info.plist")
                ref = pbxproj.create_plist_file("Info.plist")
                pbxproj.add_path(['Keyboard', name])
                pbxproj.add_ref_to_group(ref, ['Keyboard', name])

                new_plist_path = os.path.join(deps_dir, plist_gpath)
                with open(new_plist_path, 'wb') as f:
                    self.update_kbd_plist(kbd_plist, f, layout, n)
                #pbx_target, appex_ref = 
                pbxproj.duplicate_target("Keyboard", name, plist_gpath)
                pbxproj.set_target_package_id(name, "%s.%s" % (self.pkg_id, name.replace("_", "-")))
                if dev_team is not None:
                    pbxproj.set_target_build_setting(name, "DEVELOPMENT_TEAM", dev_team)

                pbxproj.add_appex_to_target_embedded_binaries("%s.appex" % name, "HostingApp")

        pbxproj.remove_target("Keyboard")

        # Set package ids properly
        pbxproj.set_target_package_id("HostingApp", self.pkg_id)
        if dev_team is not None:
            pbxproj.set_target_build_setting("HostingApp", "DEVELOPMENT_TEAM", dev_team)

        # Create locale strings
        self.create_locales(pbxproj, deps_dir)
        
        # Update pbxproj with locales
        with open(path, 'w') as f:
            self.update_pbxproj(pbxproj, f)

        # Generate icons for hosting app
        self.gen_hosting_app_icons(deps_dir)

        # Add correct ids for entitlements
        self.update_app_group_entitlements(deps_dir)

        if self.is_release:
            self.build_release(base, deps_dir)
        else:
            # self.build_debug(base, deps_dir)
            logger.info("You may now open '%s/GiellaKeyboard.xcodeproj'." %\
                    deps_dir)

    def _update_app_group_entitlements(self, group_id, subpath, deps_dir):
        plist_path = os.path.join(deps_dir, subpath)
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f, dict_type=OrderedDict)
            plist["com.apple.security.application-groups"] = [group_id]        
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)

    def update_app_group_entitlements(self, deps_dir):
        group_id = "group.%s" % self.pkg_id
        logger.info("Setting app group to '%s'…" % group_id)

        self._update_app_group_entitlements(group_id, 
            "HostingApp/HostingApp.entitlements", deps_dir)
        self._update_app_group_entitlements(group_id, 
            "Keyboard/Keyboard.entitlements", deps_dir)

    def ensure_xcode_version(self):
        if shutil.which('xcodebuild') is None:
            logger.error("'xcodebuild' could not be found on your PATH. Please " +
                "ensure Xcode and its associated command line tools are installed.")
            return False

        process = subprocess.Popen(['xcodebuild', '-version'],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            logger.error(err.decode().strip())
            logger.error("Application ended with error code %s." % process.returncode)
            sys.exit(process.returncode)

        v = VERSION_RE.match(out.decode().split('\n')[0].strip())
        major = int(v.groups()[0])
        minor = int(v.groups()[1])

        logger.debug("Xcode version: %s.%s" % (major, minor))

        if major >= 8 or (major == 7 and minor >= 1):
            return True

        logger.error("Your version of Xcode is too old. You need 7.1 or later.")
        return False

    def ensure_ios_autotools(self):
        msg = "'%s' could not be found on your PATH. Please ensure bbqsrc/ios-autotools is installed."

        if shutil.which('iconfigure') is None:
            logger.error(msg % 'iconfigure')
            return False

        if shutil.which('autoframework') is None:
            logger.error(msg % 'autoframework')
            return False

        return True

    def build_debug(self, base_dir, deps_dir):
        cmd = 'xcodebuild -configuration Debug -target HostingApp ' + \
              '-jobs %s ' % multiprocessing.cpu_count() + \
              'CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO'
        process = subprocess.Popen(cmd,
                    cwd=os.path.join(deps_dir), shell=True)
        process.wait()

        if process.returncode != 0:
            logger.error("Application ended with error code %s." % process.returncode)
            sys.exit(process.returncode)

    def build_release(self, base_dir, deps_dir):
        build_dir = deps_dir
        # TODO check signing ID exists in advance (in sanity checks)
        xcarchive = os.path.abspath(os.path.join(build_dir, "%s.xcarchive" %\
                self._project.internal_name))
        plist = os.path.join(build_dir, 'opts.plist')
        ipa = os.path.abspath(os.path.join(build_dir, "%s.ipa" %\
                self._project.internal_name))

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        if os.path.exists(ipa):
            os.remove(ipa)

        projpath = ":".join(os.path.abspath(os.path.join(deps_dir,
            'GiellaKeyboard.xcodeproj'))[1:].split(os.sep))

        # code_sign_id = self._project.target('ios').get('codeSignId', '')
        # logger.debug(code_sign_id)
        provisioning_profile_id = self._project.target('ios').get(
                'provisioningProfileId', None)

        if provisioning_profile_id is None:
            raise Exception("provisioningProfileId cannot be null")

        plist_obj = {
            "method": "app-store",
            "provisioningProfiles": {}
        }

        for item in self.all_bundle_ids():
            plist_obj["provisioningProfiles"][item] = provisioning_profile_id

        with open(plist, 'wb') as f:
            plistlib.dump(plist_obj, f)

        cmd1 = 'xcodebuild -configuration Release -scheme HostingApp ' + \
                'archive -archivePath "%s" ' % xcarchive + \
                '-jobs %s ' % multiprocessing.cpu_count() + \
                'PROVISIONING_PROFILE="%s"' % provisioning_profile_id
        cmd2 = """xcodebuild -exportArchive
                -archivePath "%s" -exportPath "%s"
                -exportOptionsPlist "%s"
                """.replace('\n', ' ') % (xcarchive, ipa, plist)

        for cmd, msg in (
                (cmd1, "Building .xcarchive…"),
                (cmd2, "Building .ipa and signing…"),
            ):

            logger.info(msg)
            logger.debug(cmd)
            process = subprocess.Popen(cmd, cwd=deps_dir, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(out.decode().strip())
                logger.error(err.decode().strip())
                logger.error("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        logger.info("Done! -> %s" % ipa)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def add_zhfst_files(self, build_dir):
        nm = 'dicts.bundle'
        path = os.path.join(build_dir, nm)
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)

        files = glob.glob(os.path.join(self._project.path, '*.zhfst'))
        if len(files) == 0:
            logger.warning("No ZHFST files found.")
            return

        for fn in files:
            bfn = os.path.basename(fn)
            logger.info("Adding '%s' to '%s'…" % (bfn, nm))
            shutil.copyfile(fn, os.path.join(path, bfn))

    def gen_hosting_app_icons(self, build_dir):
        if self._project.icon('ios') is None:
            logger.warning("no icon supplied!")
            return

        path = os.path.join(build_dir, 'HostingApp',
                'Images.xcassets', 'AppIcon.appiconset')

        with open(os.path.join(path, "Contents.json")) as f:
            contents = json.load(f, object_pairs_hook=OrderedDict)

        cmd_tmpl = "convert -resize {h}x{w} -background white -alpha remove -gravity center -extent {h}x{w} {src} {out}"

        for obj in contents['images']:
            scale = float(obj['scale'][:-1])
            h, w = obj['size'].split('x')
            h = float(h) * scale
            w = float(w) * scale

            icon = self._project.icon('ios', w)
            fn = "%s-%s@%s.png" % (obj['idiom'], obj['size'], obj['scale'])
            obj['filename'] = fn
            cmd = cmd_tmpl.format(h=h, w=w, src=icon, out=os.path.join(path, fn))

            logger.info("Creating '%s' from '%s'…" % (fn, icon))

            run_process(cmd.split(" "))

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

    def write_l10n_str(self, f, key, value):
        f.write(('"%s" = %s;\n' % (
            key, json.dumps(value, ensure_ascii=False))).encode('utf-8'))

    def create_locales(self, pbxproj, gen_dir):
        about_dir = self._project.target("ios").get("aboutDir", None)
        about_locales = []

        # If aboutDir is set, get the supported locales
        if about_dir is not None:
            about_dir = self._project.relpath(about_dir)
            about_locales = [os.path.splitext(x)[0] for x in os.listdir(about_dir) if x.endswith(".txt")]
        
        for locale, attrs in self._project.locales.items():
            lproj_dir = locale if locale != "en" else "Base"
            lproj = os.path.join(gen_dir, 'HostingApp', '%s.lproj' % lproj_dir)
            os.makedirs(lproj, exist_ok=True)

            with open(os.path.join(lproj, 'InfoPlist.strings'), 'ab') as f:
                self.write_l10n_str(f, 'CFBundleName', attrs['name'])
                self.write_l10n_str(f, 'CFBundleDisplayName', attrs['name'])
            
            # Add About.txt to the lproj if exists
            if locale in about_locales:
                about_file = os.path.join(about_dir, "%s.txt" % locale)
                shutil.copyfile(about_file, os.path.join(lproj, "About.txt"))

                if lproj_dir != "Base":
                    file_ref = pbxproj.create_text_file(locale, "About.txt")
                    pbxproj.add_file_ref_to_variant_group(file_ref, "About.txt")

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

        for layout in self.supported_layouts.values():
            o |= self.get_layout_locales(layout)

        return sorted(list(o))

    def update_pbxproj(self, pbxproj, f):
        pbxproj.root['knownRegions'] = self.get_all_locales()

        ref = pbxproj.add_plist_strings_to_build_phase(
                self.get_project_locales(), "HostingApp")
        pbxproj.add_ref_to_group(ref, ["HostingApp", "Supporting Files"])

        # for name, layout in self.supported_layouts.items():
        #     ref = pbxproj.add_plist_strings_to_build_phase(
        #             self.get_layout_locales(layout), name)
        #     pbxproj.add_ref_to_group(ref, ["Generated", name])

        f.write(str(pbxproj))

    def all_bundle_ids(self):
        out = []
        for n, layout in enumerate(self.supported_layouts.values()):
            bundle_id = "%s.%s" % (self.pkg_id, layout.internal_name.replace("_", "-"))
            out.append(bundle_id)
        return out

    def update_kbd_plist(self, plist, f, layout, n):
        pkg_id = self.pkg_id
        bundle_id = "%s.%s" % (pkg_id, layout.internal_name.replace("_", "-"))
        
        plist['CFBundleName'] = layout.native_display_name # self._project.target('ios')['bundleName']
        plist['CFBundleDisplayName'] = layout.native_display_name # self._project.target('ios')['bundleName']
        plist['CFBundleShortVersionString'] = self._version
        plist['CFBundleVersion'] = self._build
        plist['LSApplicationQueriesSchemes'][0] = pkg_id
        plist['NSExtension']['NSExtensionAttributes']['PrimaryLanguage'] = layout.locale
        plist['DivvunKeyboardIndex'] = n

        plistlib.dump(plist, f)

    def update_plist(self, plist, f):
        pkg_id = self.pkg_id

        plist['CFBundleName'] = self._project.target('ios')['bundleName']
        plist['CFBundleDisplayName'] = self._project.target('ios')['bundleName']
        plist['CFBundleShortVersionString'] = self._version
        plist['CFBundleVersion'] = self._build
        plist['CFBundleURLTypes'][0]['CFBundleURLSchemes'][0] = pkg_id
        plist['LSApplicationQueriesSchemes'][0] = pkg_id

        plistlib.dump(plist, f)

    def generate_json_layout(self, name, layout):
        local_name = layout.display_names.get(layout.locale, None)
        if local_name is None:
            raise Exception(("Keyboard '%s' requires localisation " +
                            "into its own locale.") % layout.internal_name)
        
        out = OrderedDict()

        out['name'] = local_name
        out['internalName'] = name
        out["return"] = layout.strings.get('return', 'return')
        out["space"] = layout.strings.get('space', 'space')
        out["longPress"] = layout.longpress
        out["normal"] = layout.modes['mobile-default']
        out["shifted"] = layout.modes['mobile-shift']

        return out
