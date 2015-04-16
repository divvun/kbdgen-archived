import copy
import os.path
import shutil
from collections import defaultdict
from textwrap import dedent, indent

import pycountry
from lxml import etree
from lxml.etree import Element, SubElement

from .base import *
from .. import boolmap, get_logger

logger = get_logger(__file__)

ANDROID_GLYPHS = {}

for api in range(16, 21+1):
    if api in (17, 18, 20):
        continue
    with open(os.path.join(os.path.dirname(__file__), 'bin',
            "android-glyphs-api%s.bin" % api), 'rb') as f:
        ANDROID_GLYPHS[api] = boolmap.BoolMap(f.read())

class AndroidGenerator(Generator):
    REPO = "giella-ime"
    ANDROID_NS = "http://schemas.android.com/apk/res/android"
    NS = "http://schemas.android.com/apk/res-auto"

    def _element(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k in ['keyLabel', 'additionalMoreKeys', 'keyHintLabel'] and\
                    v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.NS, k)] = v
        return Element(*args, **o)

    def _android_subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == 'keyLabel' and v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.ANDROID_NS, k)] = v
        return SubElement(*args, **o)

    def _subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == 'keyLabel' and v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.NS, k)] = v
        return SubElement(*args, **o)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def generate(self, base='.', sdk_base='./sdk'):
        sdk_base = os.getenv("ANDROID_SDK", sdk_base)

        if not self.sanity_checks():
            return

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        self.native_locale_workaround()

        self.get_source_tree(base, sdk_base)

        styles = [
            ('phone', 'xml'),
            ('tablet', 'xml-sw600dp')
        ]

        files = []

        layouts = defaultdict(list)

        for name, kbd in self._project.layouts.items():

            files += [
                ('res/xml/keyboard_layout_set_%s.xml' % name, self.kbd_layout_set(kbd)),
                ('res/xml/kbd_%s.xml' % name, self.keyboard(kbd))
            ]

            for style, prefix in styles:
                self.gen_key_width(kbd, style)

                files.append(("res/%s/rows_%s.xml" % (prefix, name),
                    self.rows(kbd, style)))

                for row in self.rowkeys(kbd, style):
                    row = ("res/%s/%s" % (prefix, row[0]), row[1])
                    files.append(row)

            layouts[kbd.target("android").get("minimumSdk", None)].append(kbd)
            self.update_strings_xml(kbd, base)

        self.update_method_xmls(layouts, base)

        files.append(self.create_ant_properties(self.is_release))

        self.save_files(files, base)

        self.update_localisation(base)

        self.generate_icons(base)

        self.build(base, self.is_release)

    def native_locale_workaround(self):
        for name, kbd in self._project.layouts.items():
            n = kbd.display_names.get(kbd.locale, None)
            if n is not None:
                kbd.display_names['zz'] = n
                del kbd.display_names[kbd.locale]

    def sanity_checks(self):
        sane = True

        pid = self._project.target('android').get('packageId')
        if pid is None:
            sane = False
            logger.error("no package ID provided for Android target.")

        for name, kbd in self._project.layouts.items():
            for dn_locale in kbd.display_names:
                if dn_locale in ['zz', kbd.locale]:
                    continue
                try:
                    pycountry.languages.get(alpha2=dn_locale)
                except KeyError:
                    sane = False
                    logger.error(("[%s] '%s' is not a supported locale. " +\
                          "You should provide the code in ISO 639-1 " +\
                          "format, if possible.") % (name, dn_locale))

            for mode, rows in kbd.modes.items():
                for n, row in enumerate(rows):
                    if len(row) > 11:
                        logger.warning(("[%s] row %s has %s keys. It is " +\
                               "recommended to have less than 12 keys per " +\
                               "row.") % (name, n+1, len(row)))

            self.detect_unavailable_glyphs_long_press(kbd, 16)
            self.detect_unavailable_glyphs_long_press(kbd, 19)
            self.detect_unavailable_glyphs_long_press(kbd, 21)
        return sane

    def _upd_locale(self, d, values):
        logger.info("Updating localisation for %s..." % d)

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
            node = SubElement(tree, 'string', name="english_ime_name")

        node.text = values['name'].replace("'", r"\'")

        with open(fn, 'w') as f:
            f.write(self._tostring(tree))

    def update_localisation(self, base):
        res_dir = os.path.join(base, 'deps', self.REPO, 'res')

        self._upd_locale(os.path.join(res_dir, "values"),
            self._project.locales['en'])

        for locale, values in self._project.locales.items():
            d = os.path.join(res_dir, "values-%s" % locale)
            if os.path.isdir(d):
                self._upd_locale(d, values)

    def generate_icons(self, base):
        icon = self._project.icon('android')
        if icon is None:
            logger.warning("no icon supplied!")
            return

        res_dir = os.path.join(base, 'deps', self.REPO, 'res')

        cmd_tmpl = "convert -resize %dx%d %s %s"

        for suffix, dimen in (
                ('hdpi', 72),
                ('mdpi', 48),
                ('xhdpi', 96),
                ('xxhdpi', 144)):
            mipmap_dir = "mipmap-%s" % suffix
            cmd = cmd_tmpl % (dimen, dimen, icon, os.path.join(
                res_dir, mipmap_dir, "ic_launcher_keyboard.png"))

            logger.info("Creating '%s' at size %dx%d" % (mipmap_dir, dimen, dimen))
            process = subprocess.Popen(cmd, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                logger.error(err.decode())
                logger.error("Application ended with error code %s." % process.returncode)
                # TODO throw exception instead.
                sys.exit(process.returncode)


    def build(self, base, release_mode=True):
        # TODO normal build
        logger.info("Building...")
        process = subprocess.Popen(['ant', 'release' if release_mode else 'debug'],
                    cwd=os.path.join(base, 'deps', self.REPO))
        process.wait()

        if not release_mode:
            fn = self._project.internal_name + "-debug.apk"
        else:
            fn = self._project.internal_name + "-release.apk"
            # TODO other release shi
        path = os.path.join(base, 'deps', self.REPO, 'bin')

        logger.info("Copying '%s' to build/ directory..." % fn)
        os.makedirs(os.path.join(base, 'build'), exist_ok=True)
        shutil.copy(os.path.join(path, fn), os.path.join(base, 'build'))

        logger.info("Done!")

    def _str_xml(self, val_dir, name, subtype):
        os.makedirs(val_dir, exist_ok=True)
        fn = os.path.join(val_dir, 'strings.xml')
        logger.info("Updating '%s'..." % fn)

        if not os.path.exists(fn):
            root = etree.XML("<resources/>")
        else:
            with open(fn) as f:
                root = etree.parse(f).getroot()

        SubElement(root,
            "string",
            name="subtype_%s" % subtype)\
            .text = name

        with open(fn, 'w') as f:
            f.write(self._tostring(root))

    def update_strings_xml(self, kbd, base):
        # TODO sanity check for non-existence directories
        # TODO run this only once preferably
        res_dir = os.path.join(base, 'deps', self.REPO, 'res')

        for locale, name in kbd.display_names.items():
            if locale == "en":
                val_dir = os.path.join(res_dir, 'values')
            else:
                val_dir = os.path.join(res_dir, 'values-%s' % locale)
            self._str_xml(val_dir, name, kbd.internal_name)

    def gen_method_xml(self, kbds, tree):
        root = tree.getroot()

        for kbd in kbds:
            self._android_subelement(root, 'subtype',
                icon="@drawable/ic_ime_switcher_dark",
                label="@string/subtype_%s" % kbd.internal_name,
                imeSubtypeLocale=kbd.locale,
                imeSubtypeMode="keyboard",
                imeSubtypeExtraValue="KeyboardLayoutSet=%s,AsciiCapable,EmojiCapable" % kbd.internal_name)

        return self._tostring(tree)


    def update_method_xmls(self, layouts, base):
        # TODO run this only once preferably

        base_layouts = layouts[None]
        del layouts[None]

        logger.info("Updating 'res/xml/method.xml'...")
        path = os.path.join(base, 'deps', self.REPO, 'res', '%s')
        fn = os.path.join(path, 'method.xml')

        with open(fn % 'xml') as f:
            tree = etree.parse(f)
        with open(fn % 'xml', 'w') as f:
            f.write(self.gen_method_xml(base_layouts, tree))

        for kl, vl in reversed(sorted(layouts.items())):
            for kr, vr in layouts.items():
                if kl >= kr:
                    continue
                layouts[kr] = vl + vr

        for api_ver, kbds in layouts.items():
            xmlv = "xml-v%s" % api_ver
            logger.info("Updating 'res/%s/method.xml'..." % xmlv)
            os.makedirs(path % xmlv, exist_ok=True)
            with open(fn % xmlv, 'w') as f:
                f.write(self.gen_method_xml(kbds, copy.deepcopy(tree)))

    def save_files(self, files, base):
        fn = os.path.join(base, 'deps', self.REPO)
        for k, v in files:
            with open(os.path.join(fn, k), 'w') as f:
                logger.info("Creating '%s'..." % k)
                f.write(v)

    def get_source_tree(self, base, sdk_base):
        if not os.path.exists(os.path.join(
            os.path.abspath(sdk_base), 'tools', 'android')):
            raise MissingApplicationException(
                    "Error: Could not find the Android SDK. " +\
                    "Ensure your environment is configured correctly, " +\
                    "specifically the ANDROID_SDK env variable.")

        deps_dir = os.path.join(base, 'deps')
        os.makedirs(deps_dir, exist_ok=True)

        logger.info("Preparing dependencies...")

        repo_dir = os.path.join(deps_dir, self.REPO)

        if os.path.isdir(repo_dir):
            git_update(repo_dir, self.branch, base)
        else:
            git_clone(self.repo, repo_dir, self.branch, base)

        logger.info("Create Android project...")

        cmd = "%s update project -n %s -t android-19 -p ." % (
            os.path.join(os.path.abspath(sdk_base), 'tools/android'),
            self._project.internal_name)
        process = subprocess.Popen(cmd, cwd=os.path.join(deps_dir, self.REPO),
                shell=True)
        process.wait()
        if process.returncode != 0:
            raise Exception("Application ended with error code %s." % process.returncode)

        rules_fn = os.path.join(deps_dir, self.REPO, 'custom_rules.xml')
        with open(rules_fn) as f:
            x = f.read()
        with open(rules_fn, 'w') as f:
            f.write(x.replace('GiellaIME', self._project.internal_name))

    def create_ant_properties(self, release_mode=False):
        if release_mode:
            data = dedent("""\
            package.name=%s
            key.store=%s
            key.alias=%s
            version.code=%s
            version.name=%s
            """ % (
                self._project.target('android')['packageId'],
                os.path.abspath(self._project.target('android')['keyStore']),
                self._project.target('android')['keyAlias'],
                self._project.build,
                self._project.version
            ))
        else:
            data = dedent("""\
            package.name=%s
            version.code=%s
            version.name=%s
            """ % (
                self._project.target('android')['packageId'],
                self._project.build,
                self._project.version
            ))

        return ('ant.properties', data)

    def kbd_layout_set(self, kbd):
        out = Element("KeyboardLayoutSet", nsmap={"latin": self.NS})

        kbd_str = "@xml/kbd_%s" % kbd.internal_name

        self._subelement(out, "Element", elementName="alphabet",
            elementKeyboard=kbd_str,
            enableProximityCharsCorrection="true")

        for name, kbd_str in (
            ("alphabetAutomaticShifted", kbd_str),
            ("alphabetManualShifted", kbd_str),
            ("alphabetShiftLocked", kbd_str),
            ("alphabetShiftLockShifted", kbd_str),
            ("symbols", "@xml/kbd_symbols"),
            ("symbolsShifted", "@xml/kbd_symbols_shift"),
            ("phone", "@xml/kbd_phone"),
            ("phoneSymbols", "@xml/kbd_phone_symbols"),
            ("number", "@xml/kbd_number")
        ):
            self._subelement(out, "Element", elementName=name, elementKeyboard=kbd_str)

        return self._tostring(out)

    def row_has_special_keys(self, kbd, n, style):
        for key, action in kbd.get_actions(style).items():
            if action.row == n:
                return True
        return False

    def rows(self, kbd, style):
        out = Element("merge", nsmap={"latin": self.NS})

        self._subelement(out, "include", keyboardLayout="@xml/key_styles_common")

        for n, values in enumerate(kbd.modes['default']):
            n += 1

            row = self._subelement(out, "Row")
            include = self._subelement(row, "include", keyboardLayout="@xml/rowkeys_%s%s" % (
                kbd.internal_name, n))

            if not self.row_has_special_keys(kbd, n, style):
                self._attrib(include, keyWidth='%.2f%%p' % (100 / len(values)))
            else:
                self._attrib(include, keyWidth='%.2f%%p' % self.key_width)

        # All the fun buttons!
        self._subelement(out, "include", keyboardLayout="@xml/row_qwerty4")

        return self._tostring(out)

    def gen_key_width(self, kbd, style):
        m = 0
        for row in kbd.modes['default']:
            r = len(row)
            if r > m:
               m = r

        vals = {
            "phone": 95,
            "tablet": 90
        }

        self.key_width = (vals[style] / m)

    def keyboard(self, kbd, **kwargs):
        out = Element("Keyboard", nsmap={"latin": self.NS})

        self._attrib(out, **kwargs)

        self._subelement(out, "include", keyboardLayout="@xml/rows_%s" % kbd.internal_name)

        return self._tostring(out)

    def rowkeys(self, kbd, style):
        # TODO check that lengths of both modes are the same
        for n in range(1, len(kbd.modes['default'])+1):
            merge = Element('merge', nsmap={"latin": self.NS})
            switch = self._subelement(merge, 'switch')

            case = self._subelement(switch, 'case',
                keyboardLayoutSetElement="alphabetManualShifted|alphabetShiftLocked|" +
                                         "alphabetShiftLockShifted")

            self.add_rows(kbd, n, kbd.modes['shift'][n-1], style, case)

            default = self._subelement(switch, 'default')

            self.add_rows(kbd, n, kbd.modes['default'][n-1], style, default)

            yield ('rowkeys_%s%s.xml' % (kbd.internal_name, n), self._tostring(merge))

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
            width += 'p'

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

        for key, action in kbd.get_actions(style).items():
            if action.row == n and action.position in [side, 'both']:
                self.add_button_type(key, action, row, tree, is_start)

    def add_rows(self, kbd, n, values, style, out):
        i = 1

        self.add_special_buttons(kbd, n, style, values, out, True)

        for key in values:
            more_keys = kbd.get_longpress(key)

            node = self._subelement(out, "Key", keyLabel=key)
            if n == 1:
                if i > 0 and i <= 10:
                    if i == 10:
                        i = 0
                    self._attrib(node,
                            keyHintLabel=str(i),
                            additionalMoreKeys=str(i))
                    if i > 0:
                        i += 1
                elif more_keys is not None:
                    self._attrib(node, keyHintLabel=more_keys[0])

            elif more_keys is not None:
                self._attrib(node, keyHintLabel=more_keys[0])

            if more_keys is not None:
                self._attrib(node, moreKeys=','.join(more_keys))

        self.add_special_buttons(kbd, n, style, values, out, False)

    def detect_unavailable_glyphs_long_press(self, layout, api_ver):
        glyphs = ANDROID_GLYPHS.get(api_ver, None)
        if glyphs is None:
            logger.warning("no glyphs file found for API %s! Can't detect " +
                  "missing characters from Android font!" % api_ver)
            return

        for vals in layout.longpress.values():
            for v in vals:
                for c in v:
                    if glyphs[ord(c)] is False:
                        logger.warning("[%s] '%s' (codepoint: U+%04X) " +
                                       "is not supported by API %s!" % (
                            layout.internal_name,
                            c, ord(c), api_ver))

    def detect_unavailable_glyphs_keys(self, key, api_ver):
        glyphs = ANDROID_GLYPHS.get(api_ver, None)
        if glyphs is None:
            logger.warning("no glyphs file found for API %s! Can't detect " +
                  "missing characters from Android font!" % api_ver)
            return

