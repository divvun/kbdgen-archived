from lxml import etree
from lxml.etree import Element, SubElement

import os
import os.path
import shutil
import subprocess
import copy

class Generator:
    def __init__(self, tree):
        self._tree = tree

class AndroidGenerator(Generator):
    ANDROID_NS="http://schemas.android.com/apk/res/android"
    NS = "http://schemas.android.com/apk/res/com.android.inputmethod.latin"

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
        self.get_source_tree(base, sdk_base)
        name = self._tree.name

        styles = [
            ('phone', 'xml'),
            ('tablet', 'xml-sw600dp')
        ]

        files = [
            ('xml/keyboard_layout_set_%s.xml' % name, self.kbd_layout_set()),
            ('xml/kbd_%s.xml' % name, self.keyboard())
        ]

        for style, prefix in styles:
            self.gen_key_width(style)

            files.append(("%s/rows_%s.xml" % (prefix, name), self.rows(style)))

            for row in self.rowkeys(style):
                row = ("%s/%s" % (prefix, row[0]), row[1])
                files.append(row)

        files.append(self.update_method_xml())

        self.save_files(files, base)

        self.build(base)

    def build(self, base, debug=True):
        # TODO normal build
        print("Building...")
        process = subprocess.Popen(['ant', 'debug'], 
                    cwd=os.path.join(base, 'deps', 'LatinIME', 'java'))
        process.wait()

        fn = "LatinIME-debug.apk"
        path = os.path.join(base, 'deps', 'LatinIME', 'java', 'bin')

        print("Copying '%s' to build/ directory..." % fn)
        os.makedirs(os.path.join(base, 'build'), exist_ok=True)
        shutil.copy(os.path.join(path, fn), os.path.join(base, 'build'))

        print("Done!")

    def update_method_xml(self, base='.'):
        print("Updating method.xml...")
        fn = os.path.join(base, 'deps', 'LatinIME', 'java',
                    'res', 'xml', 'method.xml')

        with open(fn) as f:
            tree = etree.parse(f)

        self._android_subelement(tree.getroot(), 'subtype',
            icon="@drawable/ic_ime_switcher_dark",
            label=self._tree.display_name,
            imeSubtypeLocale=self._tree.locales[0],
            imeSubtypeMode="keyboard",
            imeSubtypeExtraValue="KeyboardLayoutSet=%s,AsciiCapable,EmojiCapable" % self._tree.name)

        return ('xml/method.xml', self._tostring(tree))

    def save_files(self, files, base):
        fn = os.path.join(base, 'deps', 'LatinIME', 'java', 'res')
        for k, v in files:
            with open(os.path.join(fn, k), 'w') as f:
                print("Saving file '%s'..." % k)
                f.write(v)

    def get_source_tree(self, base, sdk_base):
        # TODO check SDK base is valid

        tag = 'android-4.4.4_r2.0.1'

        deps_dir = os.path.join(base, 'deps')
        os.makedirs(deps_dir, exist_ok=True)

        processes = []

        repos = [
            ('LatinIME', 'https://android.googlesource.com/platform/packages/inputmethods/LatinIME'),
            ('inputmethodcommon', 'https://android.googlesource.com/platform/frameworks/opt/inputmethodcommon')]

        for d, url in repos:
            cmd = ['git', 'clone', url]
            cwd = deps_dir

            if os.path.isdir(os.path.join(deps_dir, d)):
                continue

            print("Cloning repository '%s'..." % d)
            processes.append(subprocess.Popen(cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE))

        for process in processes:
            output = process.communicate()
            if process.returncode != 0:
                raise Exception(output[1])

        processes = []

        for d, url in repos:
            print("Updating repository '%s'..." % d)

            cmd = "git checkout master; git reset --hard; git clean -f; git pull; git checkout tags/%s" % tag
            cwd = os.path.join(deps_dir, d)

            processes.append(subprocess.Popen(cmd, cwd=cwd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE))

        for process in processes:
            output = process.communicate()
            if process.returncode != 0:
                raise Exception(output[1])

        print("Copying relevant files from 'inputmethodcommon' to 'LatinIME'...")

        src = os.path.join(deps_dir, 'inputmethodcommon', 'java', 'com')
        dst = os.path.join(deps_dir, 'LatinIME', 'java', 'src')

        cmd = ['cp', '-r', src, dst]
        process = subprocess.Popen(cmd, cwd=base,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.communicate()
        if process.returncode != 0:
            raise Exception(output[1])

        print("Create Android project...")

        cmd = "%s update project -n LatinIME -t android-19 -p ." % \
            os.path.join(os.path.abspath(sdk_base), 'tools/android')
        process = subprocess.Popen(cmd, cwd=os.path.join(deps_dir, 'LatinIME', 'java'),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.communicate()
        if process.returncode != 0:
            raise Exception(output[1])

        print("Updating build.xml...")

        self.update_build_xml(base, sdk_base)

        os.makedirs(os.path.join(deps_dir, 'LatinIME', 'java', 'libs'), exist_ok=True)

        print("Copying support libraries from Android SDK...")
        shutil.copy(os.path.join(sdk_base, "extras/android/support/v4/android-support-v4.jar"),
                    os.path.join(deps_dir, 'LatinIME', 'java', 'libs'))

    def update_build_xml(self, base, sdk_base):
        base_buildxml_fn = os.path.join(sdk_base, 'tools', 'ant', 'build.xml')
        buildxml_fn = os.path.join(base, 'deps', 'LatinIME', 'java', 'build.xml')

        with open(base_buildxml_fn) as f:
            base_buildxml = etree.parse(f)

        with open(buildxml_fn) as f:
            buildxml = etree.parse(f)

        root = buildxml.getroot()
        #print(self._tostring(root[-1]))
        #root.remove(root[-1])

        #for node in base_buildxml.getroot().getchildren():
        #    root.append(node)

        target = base_buildxml.xpath('target[@name="-package-resources"]')[0]
        print(self._tostring(target)
)
        SubElement(target[1][0], 'nocompress', extension='dict')
        root.insert(len(root)-1, target)

        with open(buildxml_fn, 'w') as f:
            f.write(self._tostring(root))

    def kbd_layout_set(self):
        out = Element("KeyboardLayoutSet", nsmap={"latin": self.NS})

        kbd = "@xml/kbd_%s" % self._tree.name

        self._subelement(out, "Element", elementName="alphabet",
            elementKeyboard=kbd,
            enableProximityCharsCorrection="true")

        for name, kbd in (
            ("alphabetAutomaticShifted", kbd),
            ("alphabetManualShifted", kbd),
            ("alphabetShiftLocked", kbd),
            ("alphabetShiftLockShifted", kbd),
            ("symbols", "@xml/kbd_symbols"),
            ("symbolsShifted", "@xml/kbd_symbols_shift"),
            ("phone", "@xml/kbd_phone"),
            ("phoneSymbols", "@xml/kbd_phone_symbols"),
            ("number", "@xml/kbd_number")
        ):
            self._subelement(out, "Element", elementName=name, elementKeyboard=kbd)

        return self._tostring(out)

    def row_has_special_keys(self, n, style):
        for key, action in self._tree.get_actions(style).items():
            if action.row == n:
                return True
        return False

    def rows(self, style):
        out = Element("merge", nsmap={"latin": self.NS})

        self._subelement(out, "include", keyboardLayout="@xml/key_styles_common")

        for n, values in enumerate(self._tree.modes['default']):
            n += 1

            row = self._subelement(out, "Row")
            include = self._subelement(row, "include", keyboardLayout="@xml/rowkeys_%s%s" % (
                self._tree.name, n))

            if not self.row_has_special_keys(n, style):
                self._attrib(include, keyWidth='%.2f%%p' % (100 / len(values)))
            else:
                self._attrib(include, keyWidth='%.2f%%p' % self.key_width)

        # All the fun buttons!
        self._subelement(out, "include", keyboardLayout="@xml/row_qwerty4")

        return self._tostring(out)

    def gen_key_width(self, style):
        m = 0
        for row in self._tree.modes['default']:
            r = len(row)
            if r > m:
               m = r

        vals = {
            "phone": 95,
            "tablet": 90
        }

        self.key_width = (vals[style] / m)

    def keyboard(self, **kwargs):
        out = Element("Keyboard", nsmap={"latin": self.NS})

        self._attrib(out, **kwargs)

        self._subelement(out, "include", keyboardLayout="@xml/rows_%s" % self._tree.name)

        return self._tostring(out)

    def rowkeys(self, style):
        # TODO check that lengths of both modes are the same
        for n in range(1, len(self._tree.modes['default'])+1):
            merge = Element('merge', nsmap={"latin": self.NS})
            switch = self._subelement(merge, 'switch')

            case = self._subelement(switch, 'case',
                keyboardLayoutSetElement="alphabetManualShifted|alphabetShiftLocked|" +
                                         "alphabetShiftLockShifted")

            self.add_rows(n, self._tree.modes['shift'][n-1], style, case)

            default = self._subelement(switch, 'default')

            self.add_rows(n, self._tree.modes['default'][n-1], style, default)

            yield ('rowkeys_%s%s.xml' % (self._tree.name, n), self._tostring(merge))

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

    def add_special_buttons(self, n, style, row, tree, is_start):
        side = "left" if is_start else "right"

        for key, action in self._tree.get_actions(style).items():
            if action.row == n and action.position in [side, 'both']:
                self.add_button_type(key, action, row, tree, is_start)

    def add_rows(self, n, values, style, out):
        i = 1

        self.add_special_buttons(n, style, values, out, True)

        for key in values:
            more_keys = self._tree.get_longpress(key)

            node = self._subelement(out, "Key", keyLabel=key)
            if n == 1:
                if i > 0 and i <= 10:
                    if i == 10:
                        i = 0
                    self._attrib(node, keyHintLabel=str(i), additionalMoreKeys=str(i))
                    if i > 0:
                        i += 1
                elif more_keys is not None:
                    self._attrib(node, keyHintLabel=more_keys[0])

            elif more_keys is not None:
                self._attrib(node, moreKeys=','.join(more_keys))
                #self._attrib(node, 'keyHintLabel', more_keys[0])

        self.add_special_buttons(n, style, values, out, False)
