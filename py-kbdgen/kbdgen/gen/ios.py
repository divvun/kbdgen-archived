import plistlib
import sys
import re
import shutil
import glob
import multiprocessing
import tarfile
import tempfile
import os
import json
import subprocess
import xml.etree.ElementTree as etree

from collections import OrderedDict
from pathlib import Path

from ..base import get_logger
from ..filecache import FileCache
from .base import Generator, run_process, MobileLayoutView, TabletLayoutView
from .osxutil import Pbxproj

logger = get_logger(__name__)

VERSION_RE = re.compile(r"Xcode (\d+)\.(\d+)")


class AppleiOSGenerator(Generator):
    @property
    def _version(self):
        return self.ios_target.version

    @property
    def _build(self):
        return self.ios_target.build

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = FileCache()

    def _unfurl_tarball(self, tarball, target_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarfile.open(tarball, "r:gz").extractall(str(tmpdir))
            target = [x for x in Path(tmpdir).iterdir() if x.is_dir()][0]
            os.makedirs(str(target_dir.parent), exist_ok=True)
            shutil.move(target, target_dir)

    @property
    def github_username(self):
        x = self._args.get("github_username", None)
        if x is None:
            x = os.environ.get("GITHUB_USERNAME", None)
        return x

    @property
    def github_token(self):
        x = self._args.get("github_token", None)
        if x is None:
            x = os.environ.get("GITHUB_TOKEN", None)
        return x

    def get_source_tree(self, base):
        """
        Downloads the IME source from Github as a tarball, then extracts to deps dir.
        """
        logger.info("Getting source files…")

        deps_dir = Path(os.path.join(base, "ios-build"))
        shutil.rmtree(str(deps_dir), ignore_errors=True)

        logger.trace("Github username: %r" % self.github_username)

        repo = self._args["kbd_repo"]
        branch = self._args["kbd_branch"]
        tarball = self.cache.download_latest_from_github(
            repo, branch, username=self.github_username, password=self.github_token,
        )

        self._unfurl_tarball(tarball, deps_dir)

    @property
    def ios_target(self):
        return self._bundle.targets.get("ios", {})

    @property
    def pkg_id(self):
        return self.ios_target.package_id.replace("_", "-")

    def layout_target(self, layout):
        if layout.targets is not None:
            return layout.targets.get("ios", {})
        return {}

    @property
    def app_name(self):
        return self._bundle.project.locales["en"].name

    def command_ids(self):
        return ",".join([self.pkg_id] + self.all_bundle_ids())

    def command_init(self):
        if os.environ.get("PRODUCE_USERNAME", None) is None:
            logger.error(
                "You need to supply your Fastlane username as env var PRODUCE_USERNAME."
            )
            sys.exit(100)

        cmds = []

        # Create base ID on the App Store
        cmd = ["fastlane", "produce", "-a", self.pkg_id, "--app_name", self.app_name]
        cmds.append(cmd)

        # Create all sub-ids for given keyboards
        for id_ in self.all_bundle_ids():
            cmd = [
                "fastlane",
                "produce",
                "-a",
                id_,
                "--app_name",
                "%s: %s" % (self.app_name, id_.split(".").pop()),
                "--skip_itc",
            ]
            cmds.append(cmd)

        # Create a group for this
        cmd = [
            "fastlane",
            "produce",
            "group",
            "-g",
            "group.%s" % self.pkg_id,
            "-n",
            "%s Group" % self.app_name,
        ]
        cmds.append(cmd)

        # Enable groups support for each id
        for id_ in [self.pkg_id] + self.all_bundle_ids():
            cmd = ["fastlane", "produce", "enable_services", "-a", id_, "--app-group"]
            cmds.append(cmd)

        # Add all the ids to the group
        for id_ in [self.pkg_id] + self.all_bundle_ids():
            cmd = [
                "fastlane",
                "produce",
                "associate_group",
                "-a",
                id_,
                "group.%s" % self.pkg_id,
            ]
            cmds.append(cmd)

        # Run all the commands!
        for cmd in cmds:
            return_code = run_process(cmd, show_output=True)
            if return_code != 0:
                logger.error("Application ended with error code %s." % (return_code))
                sys.exit(return_code)

    def process_command(self, command):
        if command == "ids":
            print(self.command_ids())
            return
        if command == "init":
            self.command_init()
            return

    @property
    # @lru_cache(maxsize=1)
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "ios" in v.modes or "mobile" in v.modes:
                o[k] = v
        return o

    def satisfies_requirements(self):
        if not super().satisfies_requirements():
            return False

        if self.is_release and self.team_id is None:
            logger.error("TEAM_ID must be set.")
            return False

        if self.is_release and self.sign_id is None:
            logger.error("CODE_SIGN_ID must be set.")
            return False

        if shutil.which("convert") is None:
            logger.error("`convert` not found. Is imagemagick installed?")
            return False

        return True

    def generate(self, base="."):
        command = self._args.get("command", None)
        if command is not None:
            self.process_command(command)
            return

        if not self.ensure_xcode_version():
            return

        if not self.ensure_cocoapods():
            return

        if not self.satisfies_requirements():
            return

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        self.get_source_tree(base)
        deps_dir = os.path.join(base, "ios-build")

        path = os.path.join(deps_dir, "GiellaKeyboard.xcodeproj", "project.pbxproj")
        if not os.path.isfile(path):
            logger.error("No Xcode project found. Did you use the correct repository?")
            return
        pbxproj = Pbxproj(path)

        layouts = []
        for name, layout in self.supported_layouts.items():
            layouts.append(self.generate_json_layout(name, layout))

        fn = os.path.join(deps_dir, "Keyboard", "Models", "KeyboardDefinitions.json")
        with open(fn, "w") as f:
            json.dump(layouts, f, indent=2, ensure_ascii=False)

        plist_path = os.path.join(deps_dir, "HostingApp", "Info.plist")

        # Hosting app plist
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f, dict_type=OrderedDict)
        with open(plist_path, "wb") as f:
            self.update_plist(plist, f)

        kbd_plist_path = os.path.join(deps_dir, "Keyboard", "Info.plist")
        dev_team = self.team_id

        with open(kbd_plist_path, "rb") as f:
            kbd_plist = plistlib.load(f, dict_type=OrderedDict)

            for n, (locale, layout) in enumerate(self.supported_layouts.items()):
                native_name = layout.display_names[locale]
                kbd_pkg_id = self.kbd_pkg_id(locale)
                suffix = kbd_pkg_id.split(".")[-1]

                os.makedirs(os.path.join(deps_dir, "Keyboard", suffix), exist_ok=True)
                plist_gpath = os.path.join("Keyboard", suffix, "Info.plist")
                ref = pbxproj.create_plist_file("Info.plist")
                pbxproj.add_path(["Keyboard", suffix])
                pbxproj.add_ref_to_group(ref, ["Keyboard", suffix])

                new_plist_path = os.path.join(deps_dir, plist_gpath)
                with open(new_plist_path, "wb") as f:
                    self.update_kbd_plist(kbd_plist, f, locale, native_name, layout, n)
                pbxproj.duplicate_target("Keyboard", suffix, plist_gpath)
                pbxproj.set_target_package_id(suffix, kbd_pkg_id)
                if dev_team is not None:
                    pbxproj.set_target_build_setting(
                        suffix, "DEVELOPMENT_TEAM", dev_team
                    )

                pbxproj.add_appex_to_target_embedded_binaries(
                    "%s.appex" % suffix, "HostingApp"
                )

        pbxproj.remove_appex_from_target_embedded_binaries(
            "Keyboard.appex", "HostingApp"
        )
        pbxproj.remove_target("Keyboard")

        # Set package ids properly
        pbxproj.set_target_package_id("HostingApp", self.pkg_id)
        if dev_team is not None:
            pbxproj.set_target_build_setting("HostingApp", "DEVELOPMENT_TEAM", dev_team)

        # Create locale strings
        self.create_locales(pbxproj, deps_dir)

        # Update pbxproj with locales
        with open(path, "w") as f:
            self.update_pbxproj(pbxproj, f)

        # Generate icons for hosting app
        self.gen_hosting_app_icons(deps_dir)

        # Add correct ids for entitlements
        self.update_app_group_entitlements(deps_dir)

        # Install CocoaPods deps
        self.run_cocoapods(deps_dir)

        # Add ZHFST files
        self.add_zhfst_files(deps_dir)

        if self.is_release:
            self.build_release(base, deps_dir, path, pbxproj)
        else:
            # self.build_debug(base, deps_dir)
            logger.info("You may now open '%s/GiellaKeyboard.xcworkspace'." % deps_dir)

    def run_cocoapods(self, deps_dir):
        logger.info("Installing CocoaPods dependencies…")

        return_code = run_process(
            ["pod", "install", "--repo-update"], cwd=deps_dir, show_output=True
        )
        if return_code != 0:
            logger.warn("`pod install --repo-update` returned code %s." % return_code)

        # Azure cache doesn't clear...
        return_code = run_process(["pod", "update"], cwd=deps_dir, show_output=True)
        if return_code != 0:
            logger.warn("`pod update` returned code %s." % return_code)

    def _update_app_group_entitlements(self, group_id, subpath, deps_dir):
        plist_path = os.path.join(deps_dir, subpath)
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f, dict_type=OrderedDict)
            plist["com.apple.security.application-groups"] = [group_id]
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)

    def _update_settings_bundle_group_id(self, group_id, subpath, deps_dir):
        plist_path = os.path.join(deps_dir, subpath)
        with open(plist_path, "rb") as f:
            plist = plistlib.load(f, dict_type=OrderedDict)
            plist["ApplicationGroupContainerIdentifier"] = group_id
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)

    def update_app_group_entitlements(self, deps_dir):
        group_id = "group.%s" % self.pkg_id
        logger.info("Setting app group to '%s'…" % group_id)

        self._update_app_group_entitlements(
            group_id, "HostingApp/HostingApp.entitlements", deps_dir
        )
        self._update_app_group_entitlements(
            group_id, "Keyboard/Keyboard.entitlements", deps_dir
        )

        self._update_settings_bundle_group_id(
            group_id, "HostingApp/Settings.bundle/Root.plist", deps_dir
        )

    def ensure_cocoapods(self):
        if shutil.which("pod") is None:
            logger.error(
                "'pod' could not be found on your PATH. Please "
                + "ensure CocoaPods is installed (`gem install cocoapods`)."
            )
            return False
        return True

    def ensure_xcode_version(self):
        if shutil.which("xcodebuild") is None:
            logger.error(
                "'xcodebuild' could not be found on your PATH. Please "
                + "ensure Xcode and its associated command line tools are installed."
            )
            return False

        process = subprocess.Popen(
            ["xcodebuild", "-version"], stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
        out, err = process.communicate()
        if process.returncode != 0:
            logger.error(err.decode().strip())
            logger.error("Application ended with error code %s." % process.returncode)
            sys.exit(process.returncode)

        v = VERSION_RE.match(out.decode().split("\n")[0].strip())
        major = int(v.groups()[0])
        minor = int(v.groups()[1])

        logger.debug("Xcode version: %s.%s" % (major, minor))

        if major >= 10:
            return True

        logger.error("Your version of Xcode is too old. You need 10.0 or later.")
        return False

    def embed_provisioning_profiles(self, pbxproj_path, pbxproj, deps_dir):
        logger.info("Embedding provisioning profiles…")

        o = {}

        for item in self.all_bundle_ids() + [self.pkg_id]:
            name = item.split(".")[-1] if item != self.pkg_id else "HostingApp"
            logger.trace("Profile name: %r" % name)

            profile = self.load_provisioning_profile(item, deps_dir)
            logger.debug(
                "Profile: %s %s -> %s" % (profile["UUID"], profile["Name"], name)
            )
            pbxproj.set_target_build_setting(
                name, "PROVISIONING_PROFILE", profile["UUID"]
            )
            pbxproj.set_target_build_setting(
                name, "PROVISIONING_PROFILE_SPECIFIER", profile["Name"]
            )
            o[item] = profile["UUID"]

        with open(pbxproj_path, "w") as f:
            f.write(str(pbxproj))
        return o

    def load_provisioning_profile(self, item, deps_dir):
        cmd = "security cms -D -i %s.mobileprovision" % item
        out, err = run_process(cmd.split(" "), cwd=deps_dir)
        return plistlib.loads(out)

    def build_debug(self, base_dir, deps_dir):
        cpu_count = multiprocessing.cpu_count()
        cmd = (
            "xcodebuild -configuration Debug -scheme HostingApp "
            + "-allowProvisioningUpdates -jobs %s " % cpu_count
            + 'CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO'
        )
        process = subprocess.Popen(cmd, cwd=os.path.join(deps_dir), shell=True)
        process.wait()

        if process.returncode != 0:
            logger.error("Application ended with error code %s." % process.returncode)
            sys.exit(process.returncode)

    @property
    def team_id(self):
        return self.ios_target.team_id or os.environ.get("TEAM_ID")

    @property
    def sign_id(self):
        return self.ios_target.code_sign_id or os.environ.get("CODE_SIGN_ID")

    def build_release(self, base_dir, deps_dir, pbxproj_path, pbxproj):
        build_dir = deps_dir
        xcarchive = os.path.abspath(
            os.path.join(build_dir, "%s.xcarchive" % self.pkg_id)
        )
        plist = os.path.abspath(os.path.join(build_dir, "opts.plist"))
        ipa = os.path.abspath(os.path.join(build_dir, "ipa"))

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        if os.path.exists(ipa):
            os.remove(ipa)

        code_sign_id = self.sign_id

        if code_sign_id is None:
            raise Exception("codeSignId cannot be null")

        team_id = self.team_id

        if team_id is None:
            raise Exception("teamId cannot be null")

        plist_obj = {
            "teamID": team_id,
            "method": "app-store",
            "provisioningProfiles": {},
        }

        env = dict(**os.environ)

        if self._args.get("ci", False):
            logger.info("Doing a CI build!")
            logger.info("Setting up keychain…")

            match_name = "fastlane_tmp_keychain"
            match_pw = ""

            env["MATCH_KEYCHAIN_NAME"] = match_name
            env["MATCH_KEYCHAIN_PASSWORD"] = match_pw

            cmds = [
                'security create-keychain -p "%s" %s.keychain' % (match_pw, match_name),
                "security default-keychain -s %s.keychain" % match_name,
                'security unlock-keychain -p "%s" %s.keychain' % (match_pw, match_name),
                "security set-keychain-settings -t 7200 -u %s.keychain" % match_name,
            ]

            for cmd in cmds:
                logger.debug(cmd)
                returncode = run_process(cmd, env=env, shell=True, show_output=True)
                if returncode != 0:
                    # oN eRrOr GoTo NeXt
                    logger.warn("Application ended with error code %s." % returncode)

        logger.info("Downloading signing certificates…")
        cmd = "fastlane match appstore --app_identifier=%s" % self.command_ids()
        logger.debug(cmd)
        returncode = run_process(
            cmd, env=env, cwd=deps_dir, shell=True, show_output=True
        )
        if returncode != 0:
            logger.error("Application ended with error code %s." % returncode)
            sys.exit(returncode)

        logger.info("Downloading provisioning profiles…")
        for item in self.all_bundle_ids() + [self.pkg_id]:
            cmd = "fastlane sigh -a %s -b %s -z -q %s.mobileprovision" % (
                item,
                team_id,
                item,
            )
            logger.debug(cmd)
            returncode = run_process(
                cmd, env=env, cwd=deps_dir, shell=True, show_output=True
            )
            if returncode != 0:
                logger.error("Application ended with error code %s." % returncode)
                sys.exit(returncode)

        plist_obj["provisioningProfiles"] = self.embed_provisioning_profiles(
            pbxproj_path, pbxproj, deps_dir
        )

        with open(plist, "wb") as f:
            plistlib.dump(plist_obj, f)

        # cmd = "cargo lipo --targets aarch64-apple-ios,x86_64-apple-ios,armv7-apple-ios --release -vv"
        # logger.info("Running divvunspell build...")
        # logger.debug(cmd)
        # returncode = run_process(cmd, cwd=os.path.join(deps_dir, "Dependencies", "hfst-ospell-rs"), shell=True, show_output=True)
        # if returncode != 0:
        #     logger.error("Application ended with error code %s." % returncode)
        #     sys.exit(returncode)

        cmd1 = (
            'xcodebuild archive -archivePath "%s" ' % xcarchive
            + "-workspace GiellaKeyboard.xcworkspace -configuration Release "
            + "-scheme HostingApp "
            + "-jobs %s " % multiprocessing.cpu_count()
            + 'CODE_SIGN_IDENTITY="%s" ' % code_sign_id
            + "DEVELOPMENT_TEAM=%s" % team_id
        )

        # if self._args.get("ci", False):
        #     cmd1 += " OTHER_CODE_SIGN_FLAGS=\"--keychain build\""

        cmd2 = (
            "xcodebuild -exportArchive "
            + '-archivePath "%s" -exportPath "%s" ' % (xcarchive, ipa)
            + '-exportOptionsPlist "%s" ' % plist
        )

        for cmd, msg in (
            (cmd1, "Building .xcarchive…"),
            (cmd2, "Building .ipa and signing…"),
        ):
            logger.info(msg)
            logger.debug(cmd)
            returncode = run_process(
                cmd, cwd=deps_dir, env=env, shell=True, show_output=True
            )
            if returncode != 0:
                logger.error("Application ended with error code %s." % returncode)
                sys.exit(returncode)

        # if os.path.exists(xcarchive):
        #     shutil.rmtree(xcarchive)
        logger.info("Done! -> %s" % ipa)

    def _tostring(self, tree):
        return etree.tostring(
            tree, pretty_print=True, xml_declaration=True, encoding="utf-8"
        ).decode()

    def add_zhfst_files(self, build_dir):
        nm = "dicts.bundle"
        path = os.path.join(build_dir, nm)
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)

        use_bhfst = self.ios_target.bhfst or False

        if use_bhfst:
            files = glob.glob(os.path.join(self._bundle.path, "../*.bhfst"))
            if len(files) == 0:
                logger.warning("No BHFST files found.")
                return

            for fn in files:
                bfn = os.path.basename(fn)
                logger.info("Adding '%s' to '%s'…" % (bfn, nm))
                shutil.copyfile(fn, os.path.join(path, bfn))
        else:
            files = glob.glob(os.path.join(self._bundle.path, "../*.zhfst"))
            if len(files) == 0:
                logger.warning("No ZHFST files found.")
                return

            for fn in files:
                bfn = os.path.basename(fn)
                logger.info("Adding '%s' to '%s'…" % (bfn, nm))
                shutil.copyfile(fn, os.path.join(path, bfn))

    @property
    def ios_resources(self):
        return self._bundle.resources("ios")

    def gen_hosting_app_icons(self, build_dir):
        icon = os.path.join(self.ios_resources, "icon.png")

        if not os.path.exists(icon):
            if self.is_release:
                logger.error("No icon supplied, but is required for a release build!")
                sys.exit(1)
            else:
                logger.warning("no icon supplied!")
            return

        path = os.path.join(
            build_dir, "HostingApp", "Images.xcassets", "AppIcon.appiconset"
        )

        with open(os.path.join(path, "Contents.json")) as f:
            contents = json.load(f, object_pairs_hook=OrderedDict)

        cmd_tmpl = "convert -resize {h}x{w} -background white -alpha remove -gravity center -extent {h}x{w} {src} {out}"
        work_items = []

        for obj in contents["images"]:
            scale = float(obj["scale"][:-1])
            h, w = obj["size"].split("x")
            h = float(h) * scale
            w = float(w) * scale

            fn = "%s-%s@%s.png" % (obj["idiom"], obj["size"], obj["scale"])
            obj["filename"] = fn
            cmd = cmd_tmpl.format(h=h, w=w, src=icon, out=os.path.join(path, fn))

            msg = "Creating '%s' from '%s'…" % (fn, icon)
            work_items.append((msg, run_process(cmd.split(" "), return_process=True)))

        for (msg, process) in work_items:
            logger.info(msg)
            process.wait()

        with open(os.path.join(path, "Contents.json"), "w") as f:
            json.dump(contents, f)

    def get_translatables_from_storyboard(self, xml_fn):
        with open(xml_fn) as f:
            tree = etree.parse(f)

        o = []
        for key, node, attr_node in [
            (n.attrib["value"], n.getparent().getparent(), n)
            for n in tree.findall("//*[@keyPath='translate']")
        ]:
            if "placeholder" in node.attrib:
                o.append(("%s.placeholder" % node.attrib["id"], key))
            if "text" in node.attrib or node.find("string[@key='text']") is not None:
                o.append(("%s.text" % node.attrib["id"], key))
            state_node = node.find("state")
            if state_node is not None:
                o.append(
                    ("%s.%sTitle" % (node.attrib["id"], state_node.attrib["key"]), key)
                )
            attr_node.getparent().remove(attr_node)
        o.sort()

        with open(xml_fn, "w") as f:
            f.write(self._tostring(tree))

        return o

    def write_l10n_str(self, f, key, value):
        f.write(
            ('"%s" = %s;\n' % (key, json.dumps(value, ensure_ascii=False))).encode(
                "utf-8"
            )
        )

    def create_locales(self, pbxproj, gen_dir):
        about_dir = self.ios_target.about_dir
        about_locales = []

        # If aboutDir is set, get the supported locales
        if about_dir is not None:
            about_dir = self._bundle.relpath(about_dir)
            about_locales = [
                os.path.splitext(os.path.basename(x))[0]
                for x in os.listdir(about_dir)
                if x.endswith(".txt")
            ]

        for locale, attrs in self._bundle.project.locales.items():
            lproj_dir = locale if locale != "en" else "Base"
            lproj = os.path.join(gen_dir, "HostingApp", "%s.lproj" % lproj_dir)
            os.makedirs(lproj, exist_ok=True)

            with open(os.path.join(lproj, "InfoPlist.strings"), "ab") as f:
                self.write_l10n_str(f, "CFBundleName", attrs.name)
                self.write_l10n_str(f, "CFBundleDisplayName", attrs.name)

            # Add About.txt to the lproj if exists
            if locale in about_locales:
                about_file = os.path.join(about_dir, "%s.txt" % locale)
                shutil.copyfile(about_file, os.path.join(lproj, "About.txt"))

                if lproj_dir != "Base":
                    file_ref = pbxproj.create_text_file(locale, "About.txt")
                    pbxproj.add_file_ref_to_variant_group(file_ref, "About.txt")

    def get_layout_locales(self, name, layout):
        locales = set(layout.display_names.keys())
        locales.remove("en")
        locales.add("Base")
        locales.add(name)
        return locales

    def get_project_locales(self):
        locales = set(self._bundle.project.locales.keys())
        locales.remove("en")
        locales.add("Base")
        return locales

    def get_all_locales(self):
        o = self.get_project_locales()

        for name, layout in self.supported_layouts.items():
            o |= self.get_layout_locales(name, layout)

        return sorted(list(o))

    def update_pbxproj(self, pbxproj, f):
        pbxproj.root["knownRegions"] = self.get_all_locales()

        ref = pbxproj.add_plist_strings_to_build_phase(
            self.get_project_locales(), "HostingApp"
        )
        pbxproj.add_ref_to_group(ref, ["HostingApp", "Supporting Files"])

        # for name, layout in self.supported_layouts.items():
        #     ref = pbxproj.add_plist_strings_to_build_phase(
        #             self.get_layout_locales(layout), name)
        #     pbxproj.add_ref_to_group(ref, ["Generated", name])

        f.write(str(pbxproj))

    def kbd_pkg_id(self, locale):
        layout = self.supported_layouts[locale]
        suffix = self.layout_target(layout).get("legacyName", locale).replace("_", "-")
        bundle_id = "%s.%s" % (self.pkg_id, suffix)
        return bundle_id

    def all_bundle_ids(self):
        out = []
        for locale in self.supported_layouts.keys():
            out.append(self.kbd_pkg_id(locale))
        return out

    def update_kbd_plist(self, plist, f, locale, native_name, layout, n):
        pkg_id = self.pkg_id

        plist["CFBundleName"] = native_name
        plist["CFBundleDisplayName"] = native_name
        plist["CFBundleShortVersionString"] = str(self._version)
        plist["CFBundleVersion"] = str(self._build)
        plist["LSApplicationQueriesSchemes"][0] = pkg_id
        plist["NSExtension"]["NSExtensionAttributes"]["PrimaryLanguage"] = locale
        plist["DivvunKeyboardIndex"] = n

        dsn = self.ios_target.sentry_dsn
        if dsn is not None:
            plist["SentryDSN"] = dsn

        plistlib.dump(plist, f)

    def update_plist(self, plist, f):
        pkg_id = self.pkg_id

        dsn = self.ios_target.sentry_dsn
        if dsn is not None:
            plist["SentryDSN"] = dsn

        plist["CFBundleName"] = self.ios_target.bundle_name
        plist["CFBundleDisplayName"] = self.ios_target.bundle_name
        plist["CFBundleShortVersionString"] = str(self._version)
        plist["CFBundleVersion"] = str(self._build)
        plist["CFBundleURLTypes"][0]["CFBundleURLSchemes"][0] = pkg_id
        plist["LSApplicationQueriesSchemes"][0] = pkg_id

        plistlib.dump(plist, f)

    def generate_json_layout(self, name, layout):
        local_name = layout.display_names.get(name, None)
        if local_name is None:
            raise Exception(
                "Keyboard '%s' requires localisation into its own locale." % name
            )

        out = OrderedDict()

        all_dead_keys = layout.dead_keys or {}
        dead_keys = {
            "iphone": all_dead_keys.get("ios", {}),
            "ipad-9in": all_dead_keys.get("ipad-9in", {}),
            "ipad-12in": all_dead_keys.get("ipad-12in", {}),
        }

        out["name"] = local_name
        out["locale"] = name
        out["return"] = layout.strings._return
        out["space"] = layout.strings.space
        out["longPress"] = layout.longpress
        out["deadKeys"] = dead_keys
        out["transforms"] = layout.transforms

        iphone = out["iphone"] = {}
        ipad_9in = out["ipad-9in"] = {}
        ipad_12in = out["ipad-12in"] = {}

        view = MobileLayoutView(layout, "ios")
        iphone["normal"] = view.mode("default")
        iphone["shifted"] = view.mode("shift")
        iphone["symbols-1"] = view.mode("symbols-1")
        iphone["symbols-2"] = view.mode("symbols-2")

        view = TabletLayoutView(layout, "ipad-9in")
        ipad_9in["normal"] = view.mode("default")
        ipad_9in["shifted"] = view.mode("shift")
        ipad_9in["alt"] = view.mode("alt")
        ipad_9in["alt+shift"] = view.mode("alt+shift")
        ipad_9in["symbols-1"] = view.mode("symbols-1")
        ipad_9in["symbols-2"] = view.mode("symbols-2")

        view = TabletLayoutView(layout, "ipad-12in")
        ipad_12in["normal"] = view.mode("default")
        ipad_12in["shifted"] = view.mode("shift")
        ipad_12in["alt"] = view.mode("alt")
        ipad_12in["alt+shift"] = view.mode("alt+shift")
        ipad_12in["symbols-1"] = view.mode("symbols-1")
        ipad_12in["symbols-2"] = view.mode("symbols-2")

        return out
