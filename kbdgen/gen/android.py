import copy
import os.path
import shutil
import sys
import glob
import subprocess
from collections import defaultdict, OrderedDict, namedtuple
from pathlib import Path

from lxml import etree
from lxml.etree import Element, SubElement
import tarfile
import tempfile

from .base import Generator, run_process, MobileLayoutView
from ..filecache import FileCache
from ..base import get_logger
from .. import boolmap

logger = get_logger(__file__)


Action = namedtuple("Action", ["row", "position", "width"])

ANDROID_GLYPHS = {}

for api in (21, 23):
    with open(
        os.path.join(
            os.path.dirname(__file__), "bin", "android-glyphs-api%s.bin" % api
        ),
        "rb",
    ) as f:
        ANDROID_GLYPHS[api] = boolmap.BoolMap(f.read())


class AndroidGenerator(Generator):
    REPO = "giella-ime"
    ANDROID_NS = "http://schemas.android.com/apk/res/android"
    NS = "http://schemas.android.com/apk/res-auto"

    def _element(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k in ["keySpec", "additionalMoreKeys", "keyHintLabel"] and v in [
                "#",
                "@",
            ]:
                v = "\\" + v
            o["{%s}%s" % (self.NS, k)] = v
        return Element(*args, **o)

    def _android_subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == "keySpec" and v in ["#", "@"]:
                v = "\\" + v
            o["{%s}%s" % (self.ANDROID_NS, k)] = v
        return SubElement(*args, **o)

    def _subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == "keySpec" and v in ["#", "@"]:
                v = "\\" + v
            o["{%s}%s" % (self.NS, k)] = v
        return SubElement(*args, **o)

    def _tostring(self, tree):
        return etree.tostring(
            tree, pretty_print=True, xml_declaration=True, encoding="utf-8"
        ).decode()

    @property
    def android_target(self):
        return self._bundle.targets.get("android", {})

    @property
    def _version(self):
        return self.android_target.version

    @property
    def _build(self):
        return self.android_target.build

    @property
    def _name(self):
        return self._bundle.name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = FileCache()

    @property
    # @lru_cache(maxsize=1)
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "android" in v.modes or "mobile" in v.modes:
                o[k] = v
        return o

    def generate(self, base="."):
        if not self.sanity_check():
            logger.error("Sanity checks failed; aborting.")
            return

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        deps_dir = os.path.join(base, "deps")
        self.repo_dir = os.path.join(deps_dir, self.REPO)
        os.makedirs(deps_dir, exist_ok=True)

        tree_id = self.get_source_tree(base, repo=self.repo, branch=self.branch)
        self.native_locale_workaround(base)

        dsn = self.android_target.sentry_dsn
        if dsn is not None:
            self.add_sentry_dsn(dsn, base)

        styles = [("phone", "xml"), ("tablet", "xml-sw600dp")]

        files = []

        layouts = defaultdict(list)

        logger.info("Updating XML strings…")
        for name, kbd in self.supported_layouts.items():
            clean_name = name.lower().replace('-', '_')
            files += [
                (
                    "app/src/main/res/xml/keyboard_layout_set_%s.xml" % clean_name,
                    self.kbd_layout_set(clean_name, kbd),
                ),
                ("app/src/main/res/xml/kbd_%s.xml" % clean_name, self.keyboard(clean_name, kbd)),
            ]

            for style, prefix in styles:
                self.gen_key_width(kbd, style)

                files.append(
                    (
                        "app/src/main/res/%s/rows_%s.xml" % (prefix, clean_name),
                        self.rows(clean_name, kbd, style),
                    )
                )

                for row in self.rowkeys(clean_name, kbd, style):
                    row = ("app/src/main/res/%s/%s" % (prefix, row[0]), row[1])
                    files.append(row)

            layouts[self.layout_target(kbd).get("minimumSdk", None)].append((clean_name, kbd))
            self.update_strings_xml(clean_name, kbd, base)

        self.update_method_xmls(layouts, base)
        self.create_gradle_properties(base, self.is_release)
        self.save_files(files, base)

        # Add zhfst files if found
        self.add_zhfst_files(base)
        # self.update_dict_authority(base)
        self.update_localisation(base)
        self.generate_icons(base)
        self.build(base, tree_id, self.is_release)

    def native_locale_workaround(self, base):
        for name, kbd in self.supported_layouts.items():
            if len(name) <= 2:
                continue

            # locale = 'zz_%s' % kbd.locale
            # kbd.display_names[locale] = kbd.display_names[kbd.locale]
            # kbd._tree['locale'] = locale

            self.update_locale_exception(name, kbd, base)

    def _find_ndk_version(self):
        try:
            p = os.path.join(os.environ["NDK_HOME"], "source.properties")
            with open(p) as f:
                for line in f.readlines():
                    if line.startswith("Pkg.Revision"):
                        return [int(x) for x in line.split("=").pop().split(".")]
        except:
            return None

    def sanity_check(self):
        if super().sanity_check() is False: 
            return False

        sane = True

        if os.environ.get("JAVA_HOME", None) and not shutil.which("java"):
            logger.error("`java` not found on path and JAVA_HOME not set.")
            sane = False

        if os.environ.get("ANDROID_HOME", None) is None:
            logger.error("ANDROID_HOME must be provided and point to the Android SDK directory.")
            sane = False

        if os.environ.get("NDK_HOME", None) is None:
            logger.error("NDK_HOME must be provided and point to the Android NDK directory.")
            sane = False
        else:
            # Check for valid NDK version
            ndk_version = self._find_ndk_version()
            logger.debug("NDK version: %r" % ndk_version)
            if ndk_version is None or ndk_version[0] < 19 or (ndk_version[0] == 19 and ndk_version[1] < 2):
                logger.error("Your NDK is too old - 19.2 or higher is required. Your version: '%s'" % ".".join(ndk_version))
                sane = False

        if shutil.which("cargo") is None:
            logger.error("`cargo` could not be found. Please ensure it is on your PATH, or install Rust from <https://rustup.rs>.")
            sane = False

        if shutil.which("cargo-ndk") is None:
            logger.error("`cargo ndk` could not be found. Please run `cargo install cargo-ndk` to continue.")
            sane = False

        if self.is_release:
            key_store_path = self.environ_or_target("ANDROID_KEYSTORE", "keyStore")
            if key_store_path is None:
                logger.error(
                    "A keystore must be provided with target property `keyStore` "
                    + "or environment variable `ANDROID_KEYSTORE` for release builds."
                )
                sane = False

            key_alias = self.environ_or_target("ANDROID_KEYALIAS", "keyAlias")
            if key_alias is None:
                logger.error(
                    "A key alias must be provided with target property `keyAlias` "
                    + "or environment variable `ANDROID_KEYALIAS` for release builds."
                )
                sane = False

            store_pw = os.environ.get("STORE_PW", None)
            key_pw = os.environ.get("KEY_PW", None)
            if store_pw is None or key_pw is None:
                logger.error("STORE_PW and KEY_PW must be set for a release build.")
                sane = False

        pid = self.android_target.package_id
        if pid is None:
            sane = False
            logger.error("No package ID provided for Android target.")

        for name, kbd in self.supported_layouts.items():
            for dn_locale in kbd.display_names:
                if dn_locale in ["zz", name]:
                    continue

            for mode, rows in kbd.modes.items():
                for n, row in enumerate(rows):
                    if len(row) > 12:
                        logger.warning(
                            (
                                "[%s] row %s has %s keys. It is "
                                + "recommended to have 12 keys or less per "
                                + "row."
                            )
                            % (name, n + 1, len(row))
                        )
            for api_v in [21, 23]:
                if not self.detect_unavailable_glyphs(name, kbd, api_v):
                    sane = False

        return sane

    def _update_dict_auth_xml(self, auth, base):
        path = os.path.join(
            base, "deps", self.REPO, "app/src/main/res/values/dictionary-pack.xml"
        )
        with open(path) as f:
            tree = etree.parse(f)

        nodes = tree.xpath("string[@name='authority']")
        if len(nodes) == 0:
            logger.error("No authority string found in XML!")
            return

        nodes[0].text = auth

        with open(path, "w") as f:
            f.write(self._tostring(tree))

    def _update_dict_auth_java(self, auth, base):
        # ಠ_ಠ
        target = "com.android.inputmethod.dictionarypack.aosp"

        # (╯°□°）╯︵ ┻━┻
        src_path = (
            "app/src/main/java/com/android/inputmethod/"
            + "dictionarypack/DictionaryPackConstants.java"
        )
        path = os.path.join(base, "deps", self.REPO, src_path)

        # (┛◉Д◉)┛彡┻━┻
        with open(path) as f:
            o = f.read().replace(target, auth)
        with open(path, "w") as f:
            f.write(o)

    # def update_dict_authority(self, base):
    #     auth = "%s.dictionarypack" % self.android_target.package_id
    #     logger.info("Updating dict authority string to '%s'…" % auth)

    #     self._update_dict_auth_xml(auth, base)
    #     self._update_dict_auth_java(auth, base)

    def add_zhfst_files(self, build_dir):
        nm = "app/src/main/assets/dicts"
        dict_path = os.path.join(build_dir, "deps", self.REPO, nm)
        if os.path.exists(dict_path):
            shutil.rmtree(dict_path)
        os.makedirs(dict_path, exist_ok=True)

        files = glob.glob(os.path.join(self._bundle.path, "../*.zhfst"))
        if len(files) == 0:
            logger.warning("No ZHFST files found.")
            return

        path = os.path.join(
            build_dir, "deps", self.REPO, "app/src/main/res", "xml", "spellchecker.xml"
        )

        with open(path) as f:
            tree = etree.parse(f)
        root = tree.getroot()
        # Empty the file
        for child in root:
            root.remove(child)

        for fn in files:
            bfn = os.path.basename(fn)
            logger.info("Adding '%s' to '%s'…" % (bfn, nm))
            shutil.copyfile(fn, os.path.join(dict_path, bfn))

            lang, _ = os.path.splitext(os.path.basename(fn))

            if len(lang) > 2:
                lang = "zz_%s" % lang.upper()

            self._android_subelement(
                root, "subtype", label="@string/subtype_generic", subtypeLocale=lang
            )

        with open(path, "w") as f:
            f.write(self._tostring(tree))

    def _update_locale(self, d, values):
        fn = os.path.join(d, "strings-appname.xml")
        node = None

        if os.path.exists(fn):
            with open(fn) as f:
                tree = etree.parse(f)
            nodes = tree.xpath("string[@name='english_ime_name']")
            if len(nodes) > 0:
                node = nodes[0]
        else:
            tree = etree.XML("<resources/>")

        if node is None:
            node = SubElement(tree, "string", name="english_ime_name")

        node.text = values.name.replace("'", r"\'")

        with open(fn, "w") as f:
            f.write(self._tostring(tree))

    def update_localisation(self, base):
        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/res")

        logger.info("Updating localisation values…")

        self._update_locale(
            os.path.join(res_dir, "values"), self._bundle.project.locales["en"]
        )

        for locale, values in self._bundle.project.locales.items():
            d = os.path.join(res_dir, "values-%s" % locale)
            if os.path.isdir(d):
                self._update_locale(d, values)

    @property
    def android_resources(self):
        return self._bundle.resources("android")

    def generate_icons(self, base):
        icon = os.path.join(self.android_resources, "icon.png")
        if not os.path.exists(icon):
            logger.warning("no icon supplied!")
            return

        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/res")

        cmd_tmpl = "convert -resize %dx%d %s %s"

        for suffix, dimen in (
            ("mdpi", 48),
            ("hdpi", 72),
            ("xhdpi", 96),
            ("xxhdpi", 144),
            ("xxxhdpi", 192),
        ):
            mipmap_dir = "drawable-%s" % suffix
            cmd = cmd_tmpl % (
                dimen,
                dimen,
                icon,
                os.path.join(res_dir, mipmap_dir, "ic_launcher_keyboard.png"),
            )

            logger.info("Creating '%s' at size %dx%d" % (mipmap_dir, dimen, dimen))
            process = subprocess.Popen(
                cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
            )
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(err.decode())
                logger.error(
                    "Application ended with error code %s." % process.returncode
                )
                # TODO throw exception instead.
                sys.exit(process.returncode)

    def _gradle(self, *args):
        # HACK: let's be honest it's all hacks
        with open(os.path.join(self.repo_dir, "local.properties"), "a") as f:
            f.write("sdk.dir=%s\n" % os.environ["ANDROID_HOME"])
        cmd = ["./gradlew"] + list(args) + ["-Dorg.gradle.jvmargs=-Xmx4096M"]
        return run_process(cmd, cwd=self.repo_dir, show_output=True) == 0

    def build(self, base, tree_id, release_mode=True):
        targets = [
            ("armv7-linux-androideabi", "armeabi-v7a"),
            ("aarch64-linux-android", "arm64-v8a"),
        ]
        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/jniLibs")
        cwd = os.path.join(self.repo_dir, "..", "hfst-ospell-rs")

        if not self.cache.inject_directory_tree(tree_id, res_dir, self.repo_dir):
            logger.info("Building native components…")
            for (target, jni_name) in targets:
                logger.info("Building %s architecture…" % target)
                returncode = run_process(
                    [
                        "cargo",
                        "ndk",
                        "--android-platform",
                        "21",
                        "--target",
                        target,
                        "--",
                        "build",
                        "--release",
                        "--lib"
                    ],
                    cwd=cwd,
                    show_output=True,
                )

                if returncode != 0:
                    logger.error(
                        "Application ended with error code %s." % returncode
                    )
                    # TODO throw exception instead.
                    sys.exit(returncode)

                jni_dir = os.path.join(res_dir, jni_name)
                Path(jni_dir).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(
                    os.path.join(cwd, "target", target, "release/libdivvunspell.so"),
                    os.path.join(jni_dir, "libdivvunspell.so"),
                )

            self.cache.save_directory_tree(tree_id, self.repo_dir, res_dir)
        else:
            logger.info("Native components copied from cache.")

        logger.info("Generating .apk…")
        if not self._gradle("assembleRelease" if release_mode else "assembleDebug"):
            return 1

        if not release_mode:
            suffix = "debug"
        else:
            suffix = "release"

        path = os.path.join(base, "deps", self.REPO, "app/build/outputs/apk", suffix)
        fn = "app-%s.apk" % suffix
        out_fn = os.path.join(
            base, "%s-%s_%s.apk" % (self._name, self._version, suffix)
        )

        logger.info("Copying '%s' -> '%s'…" % (fn, out_fn))
        os.makedirs(base, exist_ok=True)

        shutil.copy(os.path.join(path, fn), out_fn)

    def _str_xml(self, val_dir, name, subtype):
        os.makedirs(val_dir, exist_ok=True)
        fn = os.path.join(val_dir, "strings.xml")

        if not os.path.exists(fn):
            root = etree.XML("<resources/>")
        else:
            with open(fn) as f:
                root = etree.parse(f).getroot()

        SubElement(root, "string", name="subtype_%s" % subtype).text = name

        with open(fn, "w") as f:
            f.write(self._tostring(root))

    def update_locale_exception(self, name, kbd, base):
        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/res")
        fn = os.path.join(res_dir, "values", "donottranslate.xml")

        logger.info("Adding '%s' to '%s'…" % (name, fn))

        with open(fn) as f:
            tree = etree.parse(f)

        clean_name = name.replace("-", "_")

        # Add to exception keys
        node = tree.xpath("string-array[@name='subtype_locale_exception_keys']")[0]
        SubElement(node, "item").text = clean_name

        node = tree.xpath(
            "string-array[@name='subtype_locale_displayed_in_root_locale']"
        )[0]
        SubElement(node, "item").text = clean_name

        SubElement(
            tree.getroot(), "string", name="subtype_in_root_locale_%s" % clean_name
        ).text = kbd.display_names[name]

        with open(fn, "w") as f:
            f.write(self._tostring(tree.getroot()))

    def add_sentry_dsn(self, dsn, base):
        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/res")
        fn = os.path.join(res_dir, "values", "donottranslate.xml")

        logger.info("Adding Sentry DSN to '%s'…" % fn)

        with open(fn) as f:
            tree = etree.parse(f)

        # Add to exception keys
        node = tree.xpath("string[@name='sentry_dsn']")[0]
        node.text = dsn

        with open(fn, "w") as f:
            f.write(self._tostring(tree.getroot()))

    def update_strings_xml(self, kbd_name, kbd, base):
        # TODO sanity check for non-existence directories
        # TODO run this only once preferably
        res_dir = os.path.join(base, "deps", self.REPO, "app/src/main/res")

        for locale, name in kbd.display_names.items():
            if len(locale) > 2:
                continue

            if locale == "en":
                val_dir = os.path.join(res_dir, "values")
            else:
                val_dir = os.path.join(res_dir, "values-%s" % locale)
            self._str_xml(val_dir, name, kbd_name.lower())

    def gen_method_xml(self, kbds, tree):
        root = tree.getroot()

        for (name, kbd) in kbds:
            self._android_subelement(
                root,
                "subtype",
                icon="@drawable/ic_ime_switcher_dark",
                label="@string/subtype_%s" % name.lower(),
                imeSubtypeLocale=name,
                imeSubtypeMode="keyboard",
                imeSubtypeExtraValue="KeyboardLayoutSet=%s,AsciiCapable,EmojiCapable"
                % name.lower()
            )

        return self._tostring(tree)

    def update_method_xmls(self, layouts, base):
        # None because no API version specified (nor needed)
        base_layouts = layouts[None]
        del layouts[None]

        logger.info("Updating method definitions…")
        path = os.path.join(base, "deps", self.REPO, "app/src/main/res", "%s")
        fn = os.path.join(path, "method.xml")

        with open(fn % "xml") as f:
            tree = etree.parse(f)
            root = tree.getroot()
            # Empty the method.xml file
            for child in root:
                root.remove(child)
        with open(fn % "xml", "w") as f:
            f.write(self.gen_method_xml(base_layouts, tree))

        for kl, vl in reversed(sorted(layouts.items())):
            for kr, vr in layouts.items():
                if kl >= kr:
                    continue
                layouts[kr] = vl + vr

        for api_ver, kbds in layouts.items():
            xmlv = "xml-v%s" % api_ver
            os.makedirs(path % xmlv, exist_ok=True)
            with open(fn % xmlv, "w") as f:
                f.write(self.gen_method_xml(kbds, copy.deepcopy(tree)))

    def save_files(self, files, base):
        fn = os.path.join(base, "deps", self.REPO)
        logger.info("Embedding generated keyboard XML files…")
        for k, v in files:
            with open(os.path.join(fn, k), "w") as f:
                f.write(v)

    def _unfurl_tarball(self, tarball, target_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarfile.open(tarball, "r:gz").extractall(str(tmpdir))
            target = [x for x in Path(tmpdir).iterdir() if x.is_dir()][0]
            os.makedirs(str(target_dir.parent), exist_ok=True)
            shutil.move(target, target_dir)

    def get_source_tree(self, base, repo="divvun/giella-ime", branch="master"):
        """
        Downloads the IME source from Github as a tarball, then extracts to deps
        dir.
        """
        logger.info("Getting source files from %s %s branch…" % (repo, branch))

        deps_dir = Path(os.path.join(base, "deps"))
        shutil.rmtree(str(deps_dir), ignore_errors=True)

        tarball = self.cache.download_latest_from_github(
            repo,
            branch,
            username=self._args.get("github_username", None),
            password=self._args.get("github_token", None),
        )
        hfst_ospell_tbl = self.cache.download_latest_from_github(
            "divvun/divvunspell",
            branch,
            username=self._args.get("github_username", None),
            password=self._args.get("github_token", None),
        )

        self._unfurl_tarball(tarball, deps_dir / self.REPO)

        shutil.rmtree(str(deps_dir / "../hfst-ospell-rs"), ignore_errors=True)
        self._unfurl_tarball(hfst_ospell_tbl, deps_dir / "hfst-ospell-rs")
        return hfst_ospell_tbl.split("/")[-1].split(".")[0]

    def environ_or_target(self, env_key, target_key):
        return os.environ.get(
            env_key, getattr(self.android_target, target_key, None)
        )

    def create_gradle_properties(self, base, release_mode=False):
        key_store_path = self.environ_or_target("ANDROID_KEYSTORE", "keyStore") or ""
        key_store = self._bundle.relpath(key_store_path)
        logger.debug("Key store: %s" % key_store)

        key_alias = self.environ_or_target("ANDROID_KEYALIAS", "keyAlias") or ""

        tmpl = """\
ext.app = [
    storeFile: "{store_file}",
    keyAlias: "{key_alias}",
    storePassword: "{store_pw}",
    keyPassword: "{key_pw}",
    packageName: "{pkg_name}",
    versionCode: {build},
    versionName: "{version}",
    playEmail: "{play_email}",
    playCredentials: "{play_creds}"
]
"""

        data = tmpl.format(
            store_file=os.path.abspath(key_store).replace('"', '\\"'),
            key_alias=key_alias.replace('"', '\\"'),
            version=self._version,
            build=self._build,
            pkg_name=self.android_target.package_id.replace('"', '\\"'),
            play_email=os.environ.get("PLAY_STORE_ACCOUNT", "").replace('"', '\\"'),
            play_creds=os.environ.get("PLAY_STORE_P12", "").replace('"', '\\"'),
            store_pw=os.environ.get("STORE_PW", "").replace('"', '\\"'),
            key_pw=os.environ.get("KEY_PW", "").replace('"', '\\"'),
        ).replace("$", "\\$")

        fn = os.path.join(base, "deps", self.REPO, "app/local.gradle")
        with open(fn, "w") as f:
            f.write(data)

    def kbd_layout_set(self, name, kbd):
        out = Element("KeyboardLayoutSet", nsmap={"latin": self.NS})

        # TODO: need a target override for legacy keyboards
        kbd_str = "@xml/kbd_%s" % name.lower()

        self._subelement(
            out,
            "Element",
            elementName="alphabet",
            elementKeyboard=kbd_str,
            enableProximityCharsCorrection="true",
        )

        for name, kbd_str in (
            ("alphabetAutomaticShifted", kbd_str),
            ("alphabetManualShifted", kbd_str),
            ("alphabetShiftLocked", kbd_str),
            ("alphabetShiftLockShifted", kbd_str),
            ("symbols", "@xml/kbd_symbols"),
            ("symbolsShifted", "@xml/kbd_symbols_shift"),
            ("phone", "@xml/kbd_phone"),
            ("phoneSymbols", "@xml/kbd_phone_symbols"),
            ("number", "@xml/kbd_number"),
        ):
            self._subelement(out, "Element", elementName=name, elementKeyboard=kbd_str)

        return self._tostring(out)

    def get_actions(self, layout, style):
        target = self.layout_target(layout) or {}
        actions = target.get("styles", {}).get(style, {}).get("actions", None)

        if actions is not None:
            return actions

        # time for defaults
        if style == "tablet":
            return {
                "backspace": [1, "right", "fill"],
                "enter": [2, "right", "fill"],
                "shift": [3, "both", "fill"]
            }
        else:
            return {
                "shift": [3, "left", "fill"],
                "backspace": [3, "right", "fill"]
            }
    
    def row_has_special_keys(self, kbd, n, style):
        for key, action in self.get_actions(kbd, style).items():
            if Action(*action).row == n:
                return True
        return False

    def rows(self, name, kbd, style):
        out = Element("merge", nsmap={"latin": self.NS})

        self._subelement(out, "include", keyboardLayout="@xml/key_styles_common")

        layout_view = MobileLayoutView(kbd, "default")
        for n, values in enumerate(layout_view.mode("default")):
            n += 1

            row = self._subelement(out, "Row")
            include = self._subelement(
                row,
                "include",
                keyboardLayout="@xml/rowkeys_%s%s" % (name.lower(), n),
            )

            if not self.row_has_special_keys(kbd, n, style):
                self._attrib(include, keyWidth="%.2f%%p" % (100 / len(values)))
            else:
                self._attrib(include, keyWidth="%.2f%%p" % self.key_width)

        # All the fun buttons!
        self._subelement(out, "include", keyboardLayout="@xml/row_qwerty4")

        return self._tostring(out)

    def gen_key_width(self, kbd, style):
        m = 0
        for row in MobileLayoutView(kbd, "android").mode("default"):
            r = len(row)
            if r > m:
                m = r

        vals = {"phone": 95, "tablet": 90}

        self.key_width = vals[style] / m

    def keyboard(self, name, kbd, **kwargs):
        out = Element("Keyboard", nsmap={"latin": self.NS})

        self._attrib(out, **kwargs)

        self._subelement(
            out, "include", keyboardLayout="@xml/rows_%s" % name.lower()
        )

        return self._tostring(out)

    def rowkeys(self, name, kbd, style):
        layout_view = MobileLayoutView(kbd, "android")
        # TODO check that lengths of both modes are the same
        for n in range(1, len(layout_view.mode("default")) + 1):
            merge = Element("merge", nsmap={"latin": self.NS})
            switch = self._subelement(merge, "switch")

            case = self._subelement(
                switch,
                "case",
                keyboardLayoutSetElement="alphabetManualShifted|alphabetShiftLocked|"
                + "alphabetShiftLockShifted",
            )

            self.add_rows(kbd, n, layout_view.mode("shift")[n - 1], style, case)

            default = self._subelement(switch, "default")

            self.add_rows(kbd, n, layout_view.mode("default")[n - 1], style, default)

            yield (
                "rowkeys_%s%s.xml" % (name.lower(), n),
                self._tostring(merge),
            )

    def _attrib(self, node, **kwargs):
        for k, v in kwargs.items():
            node.attrib["{%s}%s" % (self.NS, k)] = v

    def add_button_type(self, key, action, row, tree, is_start):
        node = self._element("Key")
        width = action.width

        if width == "fill":
            if is_start:
                width = "%.2f%%" % ((100 - (self.key_width * len(row))) / 2)
            else:
                width = "fillRight"
        elif width.endswith("%"):
            width += "p"

        if key == "backspace":
            self._attrib(node, keyStyle="deleteKeyStyle")
        if key == "enter":
            self._attrib(node, keyStyle="enterKeyStyle")
        if key == "shift":
            self._attrib(node, keyStyle="shiftKeyStyle")
        self._attrib(node, keyWidth=width)

        tree.append(node)

    def add_special_buttons(self, kbd, n, style, row, tree, is_start):
        side = "left" if is_start else "right"

        for key, action in self.get_actions(kbd, style).items():
            action = Action(*action)
            if action.row == n and action.position in [side, "both"]:
                self.add_button_type(key, action, row, tree, is_start)

    def add_rows(self, kbd, n, values, style, out):
        i = 1

        show_number_hints = self.layout_target(kbd).get("showNumberHints", True)

        self.add_special_buttons(kbd, n, style, values, out, True)

        for key in values:
            more_keys = kbd.longpress.get(key, None)
            node = self._subelement(out, "Key", keySpec=key)

            # If top row, and between 0 and 9 keys, show numeric hint
            is_numeric = n == 1 and i > 0 and i <= 10
            show_glyph_hint = more_keys is not None

            if show_glyph_hint:
                self._attrib(
                    node, keyHintLabel=more_keys[0], moreKeys=",".join(more_keys)
                )

            if is_numeric:
                # Handle 0 being last on a keyboard case
                if i == 10:
                    i = 0
                self._attrib(node, additionalMoreKeys=str(i))

                if show_number_hints:
                    self._attrib(node, keyHintLabel=str(i))

            if i > 0:
                i += 1

        self.add_special_buttons(kbd, n, style, values, out, False)

    def layout_target(self, layout):
        if layout.targets is not None:
            return layout.targets.get("android", {})
        return {}

    def detect_unavailable_glyphs(self, name, layout, api_ver):
        if self.layout_target(layout).get("minimumSdk", 0) > api_ver:
            return True

        glyphs = ANDROID_GLYPHS.get(api_ver, None)
        has_error = False

        if glyphs is None:
            logger.warning(
                (
                    "no glyphs file found for API %s! Can't detect "
                    + "missing characters from Android font!"
                )
                % api_ver
            )
            return

        for mode_name, vals in layout.modes.items():
            for v in vals:
                for c in v:
                    if len(c) > 1:
                        logger.debug("%s is several glyphs?" % c)
                        continue
                    if glyphs[ord(c)] is False:
                        logger.error(
                            (
                                "[%s] Key '%s' (codepoint: U+%04X) "
                                "is not supported by API %s! Set minimumSdk "
                                "to suppress this error."
                            )
                            % (name, c, ord(c), api_ver)
                        )
                        has_error = True

        for vals in layout.longpress.values():
            for v in vals:
                for c in v:
                    if glyphs[ord(c)] is False:
                        logger.debug(
                            (
                                "[%s] Long press key '%s' (codepoint: U+%04X) "
                                + "is not supported by API %s!"
                            )
                            % (name, c, ord(c), api_ver)
                        )

        return not has_error
