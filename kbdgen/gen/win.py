import io
import os
import os.path
import ntpath
import langcodes
import lcid as lcidlib
import unicodedata
import shutil
import concurrent.futures
import uuid
import re
import sys
import subprocess

from collections import OrderedDict
from distutils.dir_util import copy_tree
from textwrap import dedent

from ..base import get_logger
from ..filecache import FileCache
from .base import Generator, bind_iso_keys, run_process, mode_iter, DesktopLayoutView
from ..cldr import decode_u

logger = get_logger(__name__)

KBDGEN_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "divvun.no")

is_windows = sys.platform.startswith("win32") or sys.platform.startswith("cygwin")


def guid(kbd_id):
    return uuid.uuid5(KBDGEN_NAMESPACE, kbd_id)


# SC 53 is decimal, 39 is space
WIN_VK_MAP = bind_iso_keys(
    (
        "OEM_5",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
        "OEM_PLUS",
        "OEM_4",
        "Q",
        "W",
        "E",
        "R",
        "T",
        "Y",
        "U",
        "I",
        "O",
        "P",
        "OEM_6",
        "OEM_1",
        "A",
        "S",
        "D",
        "F",
        "G",
        "H",
        "J",
        "K",
        "L",
        "OEM_3",
        "OEM_7",
        "OEM_2",
        "OEM_102",
        "Z",
        "X",
        "C",
        "V",
        "B",
        "N",
        "M",
        "OEM_COMMA",
        "OEM_PERIOD",
        "OEM_MINUS",
    )
)

WIN_KEYMAP = bind_iso_keys(
    (
        "29",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "0a",
        "0b",
        "0c",
        "0d",
        "10",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "1a",
        "1b",
        "1e",
        "1f",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
        "2b",
        "56",
        "2c",
        "2d",
        "2e",
        "2f",
        "30",
        "31",
        "32",
        "33",
        "34",
        "35",
    )
)

DEFAULT_KEYNAMES = """\
KEYNAME

01	Esc
0e	Backspace
0f	Tab
1c	Enter
1d	Ctrl
2a	Shift
36	"Right Shift"
37	"Num *"
38	Alt
39	Space
3a	"Caps Lock"
3b	F1
3c	F2
3d	F3
3e	F4
3f	F5
40	F6
41	F7
42	F8
43	F9
44	F10
45	Pause
46	"Scroll Lock"
47	"Num 7"
48	"Num 8"
49	"Num 9"
4a	"Num -"
4b	"Num 4"
4c	"Num 5"
4d	"Num 6"
4e	"Num +"
4f	"Num 1"
50	"Num 2"
51	"Num 3"
52	"Num 0"
53	"Num Del"
54	"Sys Req"
57	F11
58	F12
7c	F13
7d	F14
7e	F15
7f	F16
80	F17
81	F18
82	F19
83	F20
84	F21
85	F22
86	F23
87	F24

KEYNAME_EXT

1c	"Num Enter"
1d	"Right Ctrl"
35	"Num /"
37	"Prnt Scrn"
38	"Right Alt"
45	"Num Lock"
46	Break
47	Home
48	Up
49	"Page Up"
4b	Left
4d	Right
4f	End
50	Down
51	"Page Down"
52	Insert
53	Delete
54	<00>
56	Help
5b	"Left Windows"
5c	"Right Windows"
5d	Application

"""


def win_filter(*args, force=False):
    def wf(v):
        """actual filter function"""
        if v is None:
            return "-1"

        v = str(v)
        if re.match(r"^\d{4}$", v):
            return v

        v = decode_u(v)

        if v == "\0":
            return "-1"

        # check for anything outsize A-Za-z range
        if not force and re.match("^[A-Za-z]$", v):
            return v

        return "%04x" % ord(v)

    return tuple(wf(i) for i in args)


# Grapheme clusters are known as 'ligatures' in Microsoft jargon.
# This naming is terrible so we're going to use glyphbomb instead.
def win_glyphbomb(v):
    o = tuple("%04x" % ord(c) for c in decode_u(v))
    if len(o) > 4:
        raise Exception(
            'Glyphbombs ("grapheme clusters") cannot be longer than 4 codepoints.'
        )
    return o


inno_langs = {"en": "English", "fi": "Finnish", "nb": "Norwegian"}

custom_msgs = {"Enable": {"en": "Enable %1", "fi": "Aktivoi %1", "nb": "Aktiver %1"}}


class WindowsGenerator(Generator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = FileCache()

    @property
    def win_target(self):
        return self._bundle.targets.get("win", {})

    @property
    def win_resources(self):
        return self._bundle.resources("win")

    def get_or_download_kbdi(self):
        if os.environ.get("KBDI", None) is not None:
            kbdi = os.environ["KBDI"]
            logger.info("Using kbdi provided by KBDI environment variable: '%s'" % kbdi)
            return kbdi
        kbdi_sha256 = "79c7cc003c0bf66e73c18f3980cf3a0d58966fb974090a94aaf6d9a7cd45aeb4"
        kbdi_url = "https://github.com/bbqsrc/kbdi/releases/download/v0.4.3/kbdi.exe"
        return self.cache.download(kbdi_url, kbdi_sha256)

    def get_or_download_kbdi_legacy(self):
        if os.environ.get("KBDI_LEGACY", None) is not None:
            kbdi = os.environ["KBDI_LEGACY"]
            logger.info(
                "Using kbdi-legacy provided by KBDI_LEGACY environment variable: '%s'"
                % kbdi
            )
            return kbdi
        kbdi_sha256 = "442303f689bb6c4ca668c28193d30b2cf27202265b5bc8adf0952473581337b2"
        kbdi_url = (
            "https://github.com/bbqsrc/kbdi/releases/download/v0.4.3/kbdi-legacy.exe"
        )
        return self.cache.download(kbdi_url, kbdi_sha256)

    def get_or_download_signcode(self):
        signcode_sha256 = (
            "b347a3bfe9a0370366a24cb4e535c8f7cc113e8903fd2e13ebe09595090d8d54"
        )
        signcode_url = "https://brendan.so/files/signcode.exe"
        return self.cache.download(signcode_url, signcode_sha256)

    @property
    # @lru_cache(maxsize=1)
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "win" in v.modes or "desktop" in v.modes:
                o[k] = v
        return o

    def generate(self, base="."):
        outputs = OrderedDict()

        if not self.satisfies_requirements():
            return

        if self.is_release:
            try:
                kbdi = self.get_or_download_kbdi()
                kbdi_legacy = self.get_or_download_kbdi_legacy()
            except Exception as e:
                logger.critical("kbdi did a fail")
                raise e
                return

        for locale, layout in self.supported_layouts.items():
            outputs[self._klc_get_name(locale, layout, False)] = self.generate_klc(
                locale, layout
            )

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        build_dir = os.path.abspath(base)
        os.makedirs(build_dir, exist_ok=True)

        signcode = self.get_or_download_signcode()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        try:
            futures = []

            for name, data in outputs.items():
                klc_path = os.path.join(build_dir, "%s.klc" % name)
                self.write_klc_file(klc_path, data)

                if self.is_release:
                    futures.append(
                        executor.submit(
                            self.build_dll, name, "i386", klc_path, signcode, build_dir
                        )
                    )
                    futures.append(
                        executor.submit(
                            self.build_dll, name, "amd64", klc_path, signcode, build_dir
                        )
                    )
                    futures.append(
                        executor.submit(
                            self.build_dll, name, "wow64", klc_path, signcode, build_dir
                        )
                    )

            for future in futures:
                future.result()
        finally:
            executor.shutdown()

        if self.is_release:
            self.copy_nlp_files(build_dir)

            for os_ in [("Windows 7", kbdi_legacy), ("Windows 8/8.1/10", kbdi)]:
                shutil.copyfile(os_[1], os.path.join(build_dir, "kbdi.exe"))
                self.generate_inno_script(os_[0], build_dir)
                self.build_installer(os_[0], build_dir)

    def copy_nlp_files(self, build_dir):
        target = self.win_target
        src_path = target.custom_locales
        if src_path is None:
            return

        src_path = self._bundle.relpath(src_path)

        nlp_path = os.path.join(build_dir, "nlp")
        copy_tree(src_path, nlp_path)

    def write_klc_file(self, filepath, data):
        logger.info("Writing '%s'…" % filepath)
        with open(filepath, "w", encoding="utf-16-le", newline="\r\n") as f:
            f.write("\ufeff")
            f.write(data)

    def get_inno_setup_dir(self):
        possibles = [os.environ.get("INNO_PATH", None)]
        if is_windows:
            possibles += [
                "C:\\Program Files\\Inno Setup 6",
                "C:\\Program Files (x86)\\Inno Setup 6",
            ]
        for p in possibles:
            if p is None:
                continue
            if os.path.isdir(p):
                return p

    def get_msklc_dir(self):
        possibles = [os.environ.get("MSKLC_PATH", None)]
        if is_windows:
            possibles += [
                "C:\\Program Files\\Microsoft Keyboard Layout Creator 1.4",
                "C:\\Program Files (x86)\\Microsoft Keyboard Layout Creator 1.4",
            ]
        for p in possibles:
            if p is None:
                continue
            if os.path.isdir(p):
                return p

    def get_mono_dir(self):
        possibles = [os.environ.get("MONO_PATH", None)]
        if is_windows:
            possibles += ["C:\\Program Files\\Mono", "C:\\Program Files (x86)\\Mono"]
        for p in possibles:
            if p is None:
                continue
            if os.path.isdir(p):
                return p

    def layout_target(self, layout):
        if layout.targets is not None:
            return layout.targets.get("win", {})
        return {}

    @property
    def codesign_pfx(self):
        return self.win_target.code_sign_pfx or os.environ.get("CODESIGN_PFX", None)

    def satisfies_requirements(self):
        if super().satisfies_requirements() is False:
            return False
        pfx = self.codesign_pfx
        codesign_pw = os.environ.get("CODESIGN_PW", None)

        if self.is_release and (pfx is None or codesign_pw is None):
            logger.error(
                "Environment variable CODESIGN_PW and/or CODESIGN_PFX must be set for a release build."
            )
            return False
        elif pfx is None:
            logger.warn("No code signing PFX was provided; setup will not be signed.")

        if self._bundle.project.organisation == "":
            logger.warn("Property 'organisation' is undefined for this project.")
        if self._bundle.project.copyright == "":
            logger.warn("Property 'copyright' is undefined for this project.")

        if self.win_target.version is None:
            logger.error(
                "Property 'targets.win.version' must be defined in the "
                + "project for this target."
            )
            return False

        guid = self.win_target.uuid
        if guid is None:
            logger.error(
                "Property 'targets.win.uuid' must be defined in the project "
                + "for this target."
            )
            return False
        try:
            uuid.UUID(guid)
        except Exception:
            logger.error("Property 'targets.win.uuid' is not a valid UUID.")
            return False

        for locale, layout in self.supported_layouts.items():
            lcid = lcidlib.get(locale)
            if lcid is None and self.layout_target(layout).get("locale", None) is None:
                logger.error(
                    dedent(
                        """\
                Layout '%s' specifies a locale not recognised by Windows.
                To solve this issue, insert the below into the relevant layout file with the ISO 639-3 code plus the written script of the language in BCP 47 format:

                targets:
                  win:
                    locale: xyz-Latn
                """  # noqa: E501
                    )
                    % locale
                )
                return False

            if (
                lcid is None
                and self.layout_target(layout).get("languageName", None) is None
            ):
                logger.error(
                    dedent(
                        """\
                Layout '%s' requires the display name for the language to be supplied.

                targets:
                  win:
                    languageName: Pig Latin
                """
                    )
                )

        fail = False
        ids = []
        for locale, layout in self.supported_layouts.items():
            id_ = self._klc_get_name(locale, layout)
            if id_ in ids:
                fail = True
                msg = (
                    "Duplicate id found for '%s': '%s'; "
                    + "set targets.win.id to override."
                )
                logger.error(msg, locale, id_)
            else:
                ids.append(id_)

        if fail:
            return False

        if not self.is_release:
            return True

        if not is_windows:
            # Check for wine
            if not shutil.which("wine"):
                logger.error("`wine` must exist on your PATH to build keyboard DLLs.")
                return False

            # Check wine version
            out, err = subprocess.Popen(
                ["wine", "--version"], stdout=subprocess.PIPE
            ).communicate()
            v_chunks = [int(x) for x in out.decode().split("-").pop().split(".")]
            if v_chunks[0] < 2 or (v_chunks[0] == 2 and v_chunks[1] < 10):
                logger.warn(
                    "Builds are not known to succeed with Wine versions less than "
                    + "2.10; here be dragons."
                )

        # Check for INNO_PATH
        if self.get_inno_setup_dir() is None:
            logger.error(
                "Inno Setup 6 must be installed or INNO_PATH environment variable must "
                + "point to the Inno Setup 6 directory."
            )
            return False

        # Check for MSKLC_PATH
        if self.get_msklc_dir() is None:
            logger.error(
                "Microsoft Keyboard Layout Creator 1.4 must be installed or MSKLC_PATH "
                + "environment variable must point to the MSKLC directory."
            )
            return False

        return True

    def _wine_path(self, thing):
        if is_windows:
            return ntpath.abspath(thing)
        else:
            return "Z:%s" % ntpath.abspath(thing)

    def _wine_cmd(self, *args):
        if is_windows:
            return args
        else:
            return ["wine"] + list(args)

    @property
    def _kbdutool(self):
        if is_windows:
            return "%s\\bin\\i386\\kbdutool.exe" % self.get_msklc_dir()
        else:
            return "%s/bin/i386/kbdutool.exe" % self.get_msklc_dir()

    def build_dll(self, name, arch, klc_path, signcode, build_dir):
        # x86, x64, wow64
        flags = {"i386": "-x", "amd64": "-m", "wow64": "-o"}

        flag = flags[arch]

        out_path = os.path.join(build_dir, arch)
        os.makedirs(out_path, exist_ok=True)

        logger.info("Building '%s' for %s…" % (name, arch))
        cmd = self._wine_cmd(
            self._kbdutool, "-n", flag, "-u", self._wine_path(klc_path)
        )
        run_process(cmd, cwd=out_path)

        pfx = self.codesign_pfx
        if pfx is None:
            logger.warn(
                "'%s' for %s was not code signed due to no codeSignPfx property."
                % (name, arch)
            )
            return

        logger.info("Signing '%s' for %s…" % (name, arch))
        pfx_path = self._wine_path(self._bundle.relpath(pfx))
        logger.debug("PFX path: %s", pfx_path)

        cmd = self._wine_cmd(
            self._wine_path(signcode),
            "-a",
            "sha1",
            "-t",
            "http://timestamp.verisign.com/scripts/timstamp.dll",
            "-pkcs12",
            pfx_path,
            "-$",
            "commercial",
            self._wine_path(os.path.join(out_path, "%s.dll" % name)),
        )
        run_process(cmd, cwd=out_path)

    @property
    def win_resources_list(self):
        try:
            return os.listdir(self.win_resources)
        except:
            return []

    def _generate_inno_languages(self):
        out = []

        license_locales = [
            os.path.splitext(x)[0].split(".").pop()
            for x in self.win_resources_list
            if os.path.splitext(x)[0].startswith("license.")
        ]

        en_license = None
        if os.path.exists(os.path.join(self.win_resources, "license.txt")):
            en_license = self._wine_path(
                os.path.join(self.win_resources, "license.txt")
            )

        readme_locales = [
            os.path.splitext(x)[0].split(".").pop()
            for x in self.win_resources_list
            if os.path.splitext(x)[0].startswith("readme.")
        ]

        en_readme = None
        if os.path.exists(os.path.join(self.win_resources, "readme.txt")):
            en_readme = self._wine_path(os.path.join(self.win_resources, "readme.txt"))

        for locale, attrs in self._bundle.project.locales.items():
            if locale not in inno_langs:
                logger.info("'%s' not supported by setup script; skipping." % locale)
                continue

            buf = io.StringIO()
            if locale == "en":
                buf.write('Name: "en"; MessagesFile: "compiler:Default.isl"')
            else:
                buf.write(
                    'Name: "%s"; MessagesFile: "compiler:Languages\\%s.isl"'
                    % (locale, inno_langs[locale])
                )

            p = None
            if locale in license_locales:
                p = self._wine_path(
                    os.path.join(self.win_resources, "license.%s.txt" % locale)
                )
            elif en_license is not None:
                p = en_license
            if p:
                buf.write('; LicenseFile: "%s"' % p)

            q = None
            if locale in readme_locales:
                q = self._wine_path(
                    os.path.join(self.win_resources, "readme.%s.txt" % locale)
                )
            elif en_readme is not None:
                q = en_readme
            if q:
                buf.write('; InfoBeforeFile: "%s"' % q)

            out.append(buf.getvalue())

        return "\n".join(out)

    def _generate_inno_custom_messages(self):
        """Writes out the localised name for the installer and Start Menu group"""
        buf = io.StringIO()

        for key in inno_langs.keys():
            if key not in self._bundle.project.locales:
                continue
            loc = self._bundle.project.locales.get(key, self.first_locale())
            buf.write("%s.AppName=%s\n" % (key, loc.name))
            buf.write("%s.Enable=%s\n" % (key, custom_msgs["Enable"][key]))
        return buf.getvalue()

    def _installer_fn(self, os_, name, version):
        if os_ == "Windows 7":
            return "%s_%s.win7.exe" % (name, version)
        else:
            return "%s_%s.exe" % (name, version)

    def first_locale(self):
        tag = next(iter(self._bundle.project.locales.keys()))
        return self._bundle.project.locales[tag]

    def _generate_inno_setup(self, app_url, os_):
        o = self._generate_inno_os_config(os_).strip() + "\n"
        pfx = self.codesign_pfx
        if pfx is None:
            return o
        pfx = self._bundle.relpath(pfx)
        app_name = self.first_locale().name

        o += (
            "SignTool=signtool -a sha1 "
            + "-t http://timestamp.verisign.com/scripts/timstamp.dll "
            + "-pkcs12 $q%s$q -$ commercial "
            + "-n $q%s$q -i $q%s$q $f"
        ) % (self._wine_path(pfx), app_name, app_url)
        return o

    def _generate_inno_os_config(self, os_):
        if os_ == "Windows 7":
            return dedent(
                """
            OnlyBelowVersion=0,6.3.9200
            """
            )
        else:
            return "MinVersion=0,6.3.9200"

    def generate_inno_script(self, os_, build_dir):
        logger.info("Generating Inno Setup script for %s…" % os_)
        target = self.win_target
        try:
            app_version = target.version
            app_publisher = self._bundle.project.organisation
            app_url = target.url
            if app_url is None:
                app_url = ""
            app_uuid = target.uuid
            if app_uuid.startswith("{"):
                app_uuid = app_uuid[1:]
            if app_uuid.endswith("}"):
                app_uuid = app_uuid[:-1]
        except KeyError as e:
            logger.error("Property %s is not defined at targets.win." % e)
            sys.exit(1)

        app_license_path = target.license_path
        if app_license_path is not None:
            app_license_path = self._bundle.relpath(app_license_path)

        app_readme_path = target.readme_path
        if app_readme_path is not None:
            app_readme_path = self._bundle.relpath(app_readme_path)

        script = """\
#define MyAppVersion "%s"
#define MyAppPublisher "%s"
#define MyAppURL "%s"
#define MyAppUUID "{{%s}"
#define BuildDir "%s"

[Setup]
AppId={#MyAppUUID}
AppName={cm:AppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\\{cm:AppName}
DisableDirPage=no
DefaultGroupName={cm:AppName}
OutputBaseFilename=install
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
AlwaysRestart=yes
AllowCancelDuringInstall=no
UninstallRestartComputer=yes
UninstallDisplayName={cm:AppName}
%s

[Languages]
%s

[CustomMessages]
%s

[Files]
Source: "{#BuildDir}\\kbdi.exe"; DestDir: "{app}"
Source: "{#BuildDir}\\i386\\*"; DestDir: "{sys}"; Check: not Is64BitInstallMode; Flags: restartreplace uninsrestartdelete
Source: "{#BuildDir}\\amd64\\*"; DestDir: "{sys}"; Check: Is64BitInstallMode; Flags: restartreplace uninsrestartdelete
Source: "{#BuildDir}\\wow64\\*"; DestDir: "{syswow64}"; Check: Is64BitInstallMode; Flags: restartreplace uninsrestartdelete
        """.strip() % (  # noqa: E501
            app_version,
            app_publisher,
            app_url,
            app_uuid,
            self._wine_path(build_dir),
            self._generate_inno_setup(app_url, os_),
            self._generate_inno_languages(),
            self._generate_inno_custom_messages(),
        )

        # TODO: add an actual thing for this
        custom_locales = getattr(target, "customLocales", None)

        if custom_locales is not None:
            custom_locales_path = self._bundle.relpath(custom_locales)
            locales = [
                os.path.splitext(x)[0]
                for x in os.listdir(custom_locales_path)
                if x.endswith(".nlp")
            ]
            reg = []

            for l in locales:
                o = (
                    dedent(
                        """
                Root: HKLM; Subkey: "SYSTEM\\CurrentControlSet\\Control\\Nls\\CustomLocale";
                ValueType: string; ValueName: "{locale}"; ValueData: "{locale}"; Flags: uninsdeletevalue
                """  # noqa: E501
                    )
                    .strip()
                    .replace("\n", " ")
                    .format(locale=l)
                )
                reg.append(o)

            script += """Source: "{#BuildDir}\\nlp\\*"; """
            script += """DestDir: "{win}\\Globalization"; """
            script += """Flags: restartreplace uninsrestartdelete\n"""

            script += "\n[Registry]\n"
            script += "\n".join(reg)
            script += "\n"

        # Add Run section
        run_scr = io.StringIO()
        run_scr.write("[Run]\n")
        uninst_scr = io.StringIO()
        uninst_scr.write("[UninstallRun]\n")
        icons_scr = io.StringIO()
        icons_scr.write("[Icons]\n")

        # Pre-install clean script
        run_scr.write(
            'Filename: "{app}\\kbdi.exe"; Parameters: "clean"; '
            "Flags: runhidden waituntilterminated\n"
        )

        for locale, layout in self.supported_layouts.items():
            kbd_id = self._klc_get_name(locale, layout)
            dll_name = "%s.dll" % kbd_id
            language_code = self.layout_target(layout).get("locale", locale)
            language_name = self.layout_target(layout).get("languageName", None)
            if language_name is not None:
                logger.info(
                    "Using language name '%s' for layout '%s'."
                    % (language_name, locale)
                )
            else:
                logger.info(
                    (
                        "Using Windows default language name for layout '%s'; this "
                        + "can be overridden by providing a value for "
                        + "targets.win.languageName."
                    )
                    % locale
                )
            guid_str = "{%s}" % str(guid(kbd_id)).upper()

            # Install script
            run_scr.write('Filename: "{app}\\kbdi.exe"; Parameters: "keyboard_install')
            run_scr.write(' -t ""%s""' % language_code)  # BCP 47 tag
            if language_name:
                run_scr.write(' -l ""%s""' % language_name)  # Language display name
            run_scr.write(' -g ""{%s""' % guid_str)  # Product code
            run_scr.write(" -d %s" % dll_name)  # Layout DLL
            run_scr.write(
                ' -n ""%s""' % layout.display_names[locale]
            )  # Layout native display name
            run_scr.write(" -e")  # Enable layout after installing it
            run_scr.write('"; Flags: runhidden waituntilterminated\n')

            # Enablement icon
            icons_scr.write(
                'Name: "{group}\\{cm:Enable,%s}"; ' % layout.display_names[locale]
            )
            icons_scr.write('Filename: "{app}\\kbdi.exe"; ')
            icons_scr.write(
                'Parameters: "keyboard_enable -g ""{%s"" -t %s"; '
                % (guid_str, language_code)
            )
            icons_scr.write(
                "Flags: runminimized preventpinning excludefromshowinnewinstall\n"
            )

            # Uninstall script
            uninst_scr.write(
                'Filename: "{app}\\kbdi.exe"; Parameters: "keyboard_uninstall'
            )
            uninst_scr.write(
                ' ""{%s"""; Flags: runhidden waituntilterminated\n' % guid_str
            )

        script = "\n\n".join(
            (script, run_scr.getvalue(), uninst_scr.getvalue(), icons_scr.getvalue())
        )

        fn_os = "all" if os_ != "Windows 7" else "win7"
        with open(
            os.path.join(build_dir, "install.%s.iss" % fn_os),
            "w",
            encoding="utf-8-sig",
            newline="\r\n",
        ) as f:
            f.write(script)

    def build_installer(self, os_, build_dir):
        logger.info("Building installer for %s…" % os_)
        iscc = os.path.join(self.get_inno_setup_dir(), "ISCC.exe")
        output_path = self._wine_path(build_dir)
        fn_os = "all" if os_ != "Windows 7" else "win7"
        script_path = self._wine_path(os.path.join(build_dir, "install.%s.iss" % fn_os))

        name = self.first_locale().name
        version = self.win_target.version

        cmd = self._wine_cmd(
            iscc,
            "/O%s" % output_path,
            "/Ssigntool=%s $p" % self._wine_path(self.get_or_download_signcode()),
            script_path,
        )
        logger.trace(cmd)
        run_process(cmd, cwd=build_dir)

        fn = self._installer_fn(os_, name.replace(" ", "_"), version)
        shutil.move(os.path.join(build_dir, "install.exe"), os.path.join(build_dir, fn))

        logger.info("Installer generated at '%s'." % os.path.join(build_dir, fn))

    def _klc_get_name(self, locale, layout, show_errors=True):
        id_ = self.layout_target(layout).get("id", None)
        if id_ is not None:
            if len(id_) != 5 and show_errors:
                logger.warning(
                    "Keyboard id '%s' should be exactly 5 characters, got %d."
                    % (id_, len(id_))
                )
            return "kbd" + id_
        return "kbd" + re.sub(r"[^A-Za-z0-9-]", "", locale)[:5]

    def override_locale(self, locale, layout):
        l = self.layout_target(layout).get("locale", locale)
        if lcidlib.get(l) is not None:
            logger.trace("Override locale: %r", l)
            return l

        o = langcodes.Language.get(l)
        if o.script is None:
            o.script = "Latn"
        if o.region is None:
            o.region = "001"

        # The language object is weirdly immutable, so feed it itself.
        o = langcodes.Language.make(**o.to_dict()).to_tag()
        logger.trace("Override locale: %r", o)
        return o

    def _klc_write_headers(self, locale, layout, buf):
        buf.write(
            'KBD\t%s\t"%s"\n\n'
            % (self._klc_get_name(locale, layout, False), layout.display_names[locale])
        )

        copyright_ = self._bundle.project.copyright or r"¯\_(ツ)_/¯"
        organisation = self._bundle.project.organisation or r"¯\_(ツ)_/¯"
        override_locale = self.override_locale(locale, layout)

        buf.write('COPYRIGHT\t"%s"\n\n' % copyright_)
        buf.write('COMPANY\t"%s"\n\n' % organisation)
        buf.write('LOCALENAME\t"%s"\n\n' % override_locale)

        lcid = (
            lcidlib.get_hex8(override_locale) or lcidlib.get_hex8(locale) or "00002000"
        )

        buf.write('LOCALEID\t"%s"\n\n' % lcid)
        buf.write("VERSION\t1.0\n\n")
        # 0: default, 1: shift, 2: ctrl, 6: altGr/ctrl+alt, 7: shift+6
        buf.write("SHIFTSTATE\n\n0\n1\n2\n6\n7\n\n")

        buf.write("LAYOUT       ;\n\n")
        buf.write(
            "//SC\tVK_ \t\tCaps\tNormal\tShift\tCtrl\tAltGr\tAltShft\t-> Output\n"
        )
        buf.write(
            "//--\t----\t\t----\t------\t-----\t----\t-----\t-------\t   ------\n\n"
        )

    def _klc_write_keys(self, locale, layout, buf):
        col0 = mode_iter(locale, layout, "default", "win", required=True)
        col1 = mode_iter(locale, layout, "shift", "win")
        col2 = mode_iter(locale, layout, "ctrl", "win")
        col6 = mode_iter(locale, layout, "alt", "win")
        col7 = mode_iter(locale, layout, "alt+shift", "win")
        alt_caps = mode_iter(locale, layout, "alt+caps", "win")
        caps = mode_iter(locale, layout, "caps", "win")
        caps_shift = mode_iter(locale, layout, "caps+shift", "win")

        # Hold all the glyphbombs
        glyphbombs = []

        for (sc, vk, c0, c1, c2, c6, c7, cap, scap, acap) in zip(
            WIN_KEYMAP.values(),
            WIN_VK_MAP.values(),
            col0,
            col1,
            col2,
            col6,
            col7,
            caps,
            caps_shift,
            alt_caps,
        ):

            cap_mode = 0
            if cap is not None and c0 != cap and c1 != cap:
                cap_mode = "SGCap"
            elif cap is None:
                cap_mode += 1 if c0 != c1 else 0
                cap_mode += 4 if c6 != c7 else 0
            else:
                cap_mode += 1 if cap == c1 else 0
                cap_mode += 4 if acap == c7 else 0
            cap_mode = str(cap_mode)

            if len(vk) < 8:
                vk += "\t"
            buf.write("%s\t%s\t%s" % (sc, vk, cap_mode))

            # n is the col number for glyphbombs.
            for n, mode, key in (
                (0, "default", c0),
                (1, "shift", c1),
                (2, "ctrl", c2),
                (3, "alt", c6),
                (4, "alt+shift", c7),
            ):

                filtered = decode_u(key or "")
                if key is not None and len(filtered) > 1:
                    buf.write("\t%%")
                    glyphbombs.append((filtered, (vk, str(n)) + win_glyphbomb(key)))
                else:
                    buf.write("\t%s" % win_filter(key))
                    dead_keys = layout.dead_keys or {}
                    if key in dead_keys.get(mode, []):
                        buf.write("@")

            buf.write("\t// %s %s %s %s %s\n" % (c0, c1, c2, c6, c7))

            if cap_mode == "SGCap":
                if cap is not None and len(win_glyphbomb(cap)) > 1:
                    cap = None
                    logger.error(
                        "Caps key '%s' is a glyphbomb and cannot be used in Caps Mode."
                        % cap
                    )

                if scap is not None and len(win_glyphbomb(scap)) > 1:
                    scap = None
                    msg = (
                        "Caps+Shift key '%s' is a glyphbomb and "
                        + "cannot be used in Caps Mode."
                    )
                    logger.error(msg % cap)

                buf.write(
                    "-1\t-1\t\t0\t%s\t%s\t\t\t\t// %s %s\n"
                    % (win_filter(cap, scap) + (cap, scap))
                )

        # Space, such special case oh my.
        buf.write("39\tSPACE\t\t0\t")
        if layout.space is None or layout.space.get("win", None) is None:
            buf.write("0020\t0020\t0020\t-1\t-1\n")
        else:
            o = layout.space.get("win")
            buf.write(
                "%s\t%s\t%s\t%s\t%s\n"
                % win_filter(
                    o.get("default", "0020"),
                    o.get("shift", "0020"),
                    o.get("ctrl", "0020"),
                    o.get("alt", None),
                    o.get("alt+shift", None),
                )
            )

        # Decimal key on keypad.
        decimal = layout.decimal or "."
        buf.write(
            "53\tDECIMAL\t\t0\t%s\t%s\t-1\t-1\t-1\n\n" % win_filter(decimal, decimal)
        )

        # Glyphbombs!
        if len(glyphbombs) > 0:
            buf.write("LIGATURE\n\n")
            buf.write("//VK_\tMod#\tChr0\tChr1\tChr2\tChr3\n")
            buf.write("//----\t----\t----\t----\t----\t----\n\n")
            for original, col in glyphbombs:
                more_tabs = len(col) - 7
                buf.write(
                    "%s\t\t%s%s\t// %s\n"
                    % (col[0], "\t".join(col[1:]), "\t" * more_tabs, original)
                )
            buf.write("\n")

        # Deadkeys!
        transforms = layout.transforms or {}
        for basekey, o in transforms.items():
            if len(basekey) != 1:
                logger.warning(
                    ("Base key '%s' invalid for Windows deadkeys; skipping.") % basekey
                )
                continue

            buf.write("DEADKEY\t%s\n\n" % win_filter(basekey))
            for key, output in o.items():
                if key == " ":
                    continue

                key = str(key)
                output = str(output)

                if len(key) != 1 or len(output) != 1:
                    logger.debug(
                        ("%s%s -> %s is invalid for Windows " + "deadkeys; skipping.")
                        % (basekey, key, output)
                    )
                    continue
                buf.write(
                    "%s\t%s\t// %s -> %s\n"
                    % (win_filter(key, output, force=True) + (key, output))
                )

            # Create fallback key from space, or the basekey.
            output = o.get(" ", basekey)
            buf.write("0020\t%s\t//   -> %s\n\n" % (win_filter(output)[0], output))

    def _klc_write_deadkey_names(self, layout, buf):
        buf.write("KEYNAME_DEAD\n\n")

        transforms = layout.transforms or {}
        for basekey, o in transforms.items():
            if len(basekey) != 1:
                logger.warning(
                    ("Base key '%s' invalid for Windows " + "deadkeys; skipping.")
                    % basekey
                )
                continue

            buf.write(
                '%s\t"%s"\n' % (win_filter(basekey)[0], unicodedata.name(basekey))
            )

    def _klc_write_footer(self, locale, layout, buf):
        language_name = self.layout_target(layout).get("languageName", "Undefined")
        lcid = lcidlib.get(locale) or 0x0C00
        layout_name = layout.display_names[locale]

        buf.write("\nDESCRIPTIONS\n\n")
        buf.write("%04x\t%s\n" % (lcid, layout_name))

        buf.write("\nLANGUAGENAMES\n\n")
        buf.write("%04x\t%s\n" % (lcid, language_name))

        buf.write("ENDKBD\n")

    def generate_klc(self, locale, layout):
        buf = io.StringIO()

        self._klc_write_headers(locale, layout, buf)
        self._klc_write_keys(locale, layout, buf)
        buf.write(DEFAULT_KEYNAMES)
        self._klc_write_deadkey_names(layout, buf)
        self._klc_write_footer(locale, layout, buf)

        return buf.getvalue()
