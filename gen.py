from lxml import etree
from lxml.etree import Element, SubElement
from textwrap import dedent, indent

import os
import os.path
import shutil
import subprocess
import copy
import re
import io
import json
import uuid
import plistlib
import collections

import pycountry

class CulturalImperialismException(Exception): pass

class MissingApplicationException(Exception): pass

def git_clone(src, dst, branch, cwd='.'):
    print("Cloning repository '%s' to '%s'..." % (src, dst))

    cmd = ['git', 'clone', src, dst]

    process = subprocess.Popen(cmd, cwd=cwd)
    process.wait()

    git_update(dst, branch, cwd)


def git_update(dst, branch, cwd='.'):
    print("Updating repository '%s'..." % dst)

    cmd = """git checkout %s;
             git reset --hard;
             git clean -fdx;
             git pull;""" % branch

    cwd = os.path.join(cwd, dst)

    process = subprocess.Popen(cmd, cwd=cwd, shell=True)
    process.wait()


def plutil_get_json(path):
    cmd = "plutil -convert json -o -".split(" ")
    cmd.append(path)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    json_str = process.communicate()[0].decode()
    return json.loads(json_str, object_pairs_hook=collections.OrderedDict)


def plutil_to_xml_str(json_obj):
    cmd = "plutil -convert xml1 -o - -".split(" ")

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
    return process.communicate(json.dumps(json_obj).encode())[0].decode()


class Pbxproj:
    @staticmethod
    def gen_key():
        return uuid.uuid4().hex[8:].upper()

    def __init__(self, path):
        self._proj = plutil_get_json(path)

    def __str__(self):
        return plutil_to_xml_str(self._proj)

    @property
    def objects(self):
        return self._proj['objects']

    @property
    def root(self):
        return self.objects[self._proj['rootObject']]

    @property
    def main_group(self):
        return self.objects[self.root['mainGroup']]

    def find_resource_build_phase(self, target_name):
        targets = [self.objects[t] for t in self.root['targets']]
        target = None

        for t in targets:
            if t['name'] == target_name:
                target = t
                break

        if target is None:
            return None

        for build_phase in target['buildPhases']:
            phase = self.objects[build_phase]
            if phase['isa'] == "PBXResourcesBuildPhase":
                return phase

        return None

    def create_plist_string_file(self, locale):
        o = {
            "isa": "PBXFileReference",
            "lastKnownFileType": "text.plist.strings",
            "name": locale,
            "path": "%s.lproj/InfoPlist.strings" % locale,
            "sourceTree": "<group>"
        }

        k = Pbxproj.gen_key()
        self.objects[k] = o
        return k

    def create_plist_string_variant(self, variants):
        o = {
            "isa": "PBXVariantGroup",
            "children": variants,
            "name": "InfoPlist.strings",
            "sourceTree": "<group>"
        }

        return o

    def add_plist_strings(self, locales):
        plist_strs = [self.create_plist_string_file(l) for l in locales]
        variant = self.create_plist_string_variant(plist_strs)

        var_key = Pbxproj.gen_key()
        self.objects[var_key] = variant

        key = Pbxproj.gen_key()
        self.objects[key] = {
            "isa": "PBXBuildFile",
            "fileRef": var_key
        }

        return (var_key, key)

    def add_plist_strings_to_build_phase(self, locales, target_name):
        phase = self.find_resource_build_phase(target_name)
        (var_ref, ref) = self.add_plist_strings(locales)
        phase['files'].append(ref)
        return var_ref

    def add_ref_to_group(self, ref, group_list):
        o = self.main_group
        n = False

        for g in group_list:
            for c in o['children']:
                co = self.objects[c]
                if n:
                    break
                if co.get('path', co.get('name', None)) == g:
                    o = co
                    n = True
            if n:
                n = False
                continue
            else:
                return False

        o['children'].append(ref)
        return True


class Generator:
    def __init__(self, project, args=None):
        self._project = project
        self._args = args or {}

    @property
    def repo(self):
        return self._args.get('repo', None)

    @property
    def branch(self):
        return self._args.get('branch', 'stable')

    @property
    def is_release(self):
        return self._args.get('release', False)

    @property
    def dry_run(self):
        return self._args.get('dry_run', False)


class AppleiOSGenerator(Generator):
    def generate(self, base='.'):
        build_dir = os.path.join(base, 'build')

        os.makedirs(build_dir, exist_ok=True)

        for name, layout in self._project.layouts.items():
            gen_dir = os.path.join(build_dir, 'ios_%s' % name)

            if os.path.isdir(gen_dir):
                git_update(gen_dir, self.branch, base)
            else:
                git_clone(self.repo, gen_dir, self.branch, base)

            # Generated swift file
            with open(os.path.join(gen_dir, 'Keyboard',
                        'GeneratedKeyboard.swift'), 'w') as f:
                f.write(self.generate_file(layout))

            # Hosting app plist
            with open(os.path.join(gen_dir, 'HostingApp',
                        'Info.plist'), 'rb') as f:
                plist = plistlib.load(f, dict_type=collections.OrderedDict)

            with open(os.path.join(gen_dir, 'HostingApp',
                        'Info.plist'), 'wb') as f:
                self.update_plist(plist, f)

            # Keyboard plist
            with open(os.path.join(gen_dir, 'Keyboard',
                        'Info.plist'), 'rb') as f:
                plist = plistlib.load(f, dict_type=collections.OrderedDict)

            with open(os.path.join(gen_dir, 'Keyboard',
                        'Info.plist'), 'wb') as f:
                self.update_kbd_plist(plist, layout, f)

            # Update pbxproj with locales
            path = os.path.join(gen_dir,
                'TastyImitationKeyboard.xcodeproj', 'project.pbxproj')
            pbxproj = Pbxproj(path)
            with open(path, 'w') as f:
                self.update_pbxproj(pbxproj, layout, f)

            # Create locale strings
            self.create_locales(gen_dir, layout)

            print("You may now open TastyImitationKeyboard.xcodeproj in '%s'." %\
                    gen_dir)

    def write_l18n_str(self, f, key, value):
        f.write('"%s" = "%s";\n' % (key, value))

    def create_locales(self, gen_dir, layout):
        for locale, attrs in self._project.locales.items():
            lproj_dir = locale if locale != "en" else "Base"
            lproj = os.path.join(gen_dir, 'HostingApp', '%s.lproj' % lproj_dir)
            os.makedirs(lproj, exist_ok=True)

            with open(os.path.join(lproj, 'InfoPlist.strings'), 'a') as f:
                self.write_l18n_str(f, 'CFBundleName', attrs['name'])
                self.write_l18n_str(f, 'CFBundleDisplayName', attrs['name'])

        for locale, name in layout.display_names.items():
            lproj_dir = locale if locale != "en" else "Base"
            lproj = os.path.join(gen_dir, 'Keyboard', '%s.lproj' % lproj_dir)
            os.makedirs(lproj, exist_ok=True)

            with open(os.path.join(lproj, 'InfoPlist.strings'), 'a') as f:
                self.write_l18n_str(f, 'CFBundleName', name)
                self.write_l18n_str(f, 'CFBundleDisplayName', name)

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

    def get_locales(self, layout):
        return list(self.get_layout_locales(layout) |
                    self.get_project_locales())

    def update_pbxproj(self, pbxproj, layout, f):
        pbxproj.root['knownRegions'] = self.get_locales(layout)

        ref = pbxproj.add_plist_strings_to_build_phase(
                self.get_project_locales(), "HostingApp")
        pbxproj.add_ref_to_group(ref, ["HostingApp", "Supporting Files"])

        ref = pbxproj.add_plist_strings_to_build_phase(
                self.get_layout_locales(layout), "Keyboard")
        pbxproj.add_ref_to_group(ref, ["Keyboard", "Supporting Files"])

        f.write(str(pbxproj))

    def update_kbd_plist(self, plist, layout, f):
        bundle_id = "%s.%s" % (
                self._project.target('ios')['packageId'],
                layout.locale)

        plist['CFBundleName'] = layout.display_names['en']
        plist['CFBundleDisplayName'] = layout.display_names['en']
        plist['NSExtension']['NSExtensionAttributes']['PrimaryLanguage'] =\
                layout.locale
        plist['CFBundleIdentifier'] = bundle_id

        plistlib.dump(plist, f)

    def update_plist(self, plist, f):
        plist['CFBundleName'] = self._project.target('ios')['bundleName']
        plist['CFBundleDisplayName'] = self._project.target('ios')['bundleName']
        plist['CFBundleIdentifier'] = self._project.target('ios')['packageId']

        plistlib.dump(plist, f)

    def generate_file(self, layout):
        buf = io.StringIO()

        buf.write(dedent("""\
        // GENERATED FILE: DO NOT EDIT.

        func generatedKeyboard() -> Keyboard {
            var kbd = Keyboard()

        """))

        row_count = 0

        shift_key = indent(dedent("""\
        kbd.addKey(Key(.Shift), row: 2, page: 0)

        """), '    ')

        key_loop = indent(dedent("""\
        for key in ["%s"] {
            var model = Key(.Character)
            model.setLetter(key)
            kbd.addKey(model, row: %s, page: 0)
        }

        """), '    ')

        for row in layout.modes['shift']:
            if (row_count == 2):
                buf.write(shift_key)
            buf.write(key_loop % ('", "'.join(row), row_count))
            row_count += 1

        retStr = layout.strings.get('return', 'return')
        spaceStr = layout.strings.get('space', 'space')

        buf.write(dedent("""\
            return kbd
        }

        func generatedConfig() -> [String: String] {
            return ["return": "%s", "space": "%s"]
        }
        """ % (retStr, spaceStr)))

        return buf.getvalue()


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
            print("Dry run completed.")
            return

        self.native_locale_workaround()

        self.get_source_tree(base, sdk_base)

        styles = [
            ('phone', 'xml'),
            ('tablet', 'xml-sw600dp')
        ]

        files = []

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

            self.update_method_xml(kbd, base)
            self.update_strings_xml(kbd, base)

        files.append(self.create_ant_properties())

        self.save_files(files, base)

        self.update_localisation(base)

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
            print("Error: no package ID provided for Android target.")

        for name, kbd in self._project.layouts.items():
            for dn_locale in kbd.display_names:
                if dn_locale in ['zz', kbd.locale]:
                    continue
                try:
                    pycountry.languages.get(alpha2=dn_locale)
                except KeyError:
                    sane = False
                    print(("Error: (%s) '%s' is not a supported locale. " +\
                          "You should provide the code in ISO 639-1 " +\
                          "format, if possible.") % (
                        name, dn_locale))

            for mode, rows in kbd.modes.items():
                for n, row in enumerate(rows):
                    if len(row) > 11:
                        print(("Warning: (%s) row %s has %s keys. It is " +\
                               "recommended to have less than 12 keys per " +\
                               "row.") % (name, n+1, len(row)))
        return sane

    def _upd_locale(self, d, values):
        print("Updating localisation for %s..." % d)

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

    def build(self, base, release_mode=True):
        # TODO normal build
        print("Building...")
        process = subprocess.Popen(['ant', 'release' if release_mode else 'debug'],
                    cwd=os.path.join(base, 'deps', self.REPO))
        process.wait()

        if not release_mode:
            fn = self._project.internal_name + "-debug.apk"
        else:
            fn = self._project.internal_name + "-release.apk"
            # TODO other release shi
        path = os.path.join(base, 'deps', self.REPO, 'bin')

        print("Copying '%s' to build/ directory..." % fn)
        os.makedirs(os.path.join(base, 'build'), exist_ok=True)
        shutil.copy(os.path.join(path, fn), os.path.join(base, 'build'))

        print("Done!")

    def _str_xml(self, val_dir, name, subtype):
        os.makedirs(val_dir, exist_ok=True)
        fn = os.path.join(val_dir, 'strings.xml')
        print("Updating %s..." % fn)

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

    def update_method_xml(self, kbd, base):
        # TODO run this only once preferably
        print("Updating res/xml/method.xml...")
        fn = os.path.join(base, 'deps', self.REPO, 'res', 'xml', 'method.xml')

        with open(fn) as f:
            tree = etree.parse(f)

        self._android_subelement(tree.getroot(), 'subtype',
            icon="@drawable/ic_ime_switcher_dark",
            label="@string/subtype_%s" % kbd.internal_name,
            imeSubtypeLocale=kbd.locale,
            imeSubtypeMode="keyboard",
            imeSubtypeExtraValue="KeyboardLayoutSet=%s,AsciiCapable,EmojiCapable" % kbd.internal_name)
        with open(fn, 'w') as f:
            f.write(self._tostring(tree))
        #return ('res/xml/method.xml', self._tostring(tree))

    def save_files(self, files, base):
        fn = os.path.join(base, 'deps', self.REPO)
        for k, v in files:
            with open(os.path.join(fn, k), 'w') as f:
                print("Saving file '%s'..." % k)
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

        print("Preparing dependencies...")

        repo_dir = os.path.join(deps_dir, self.REPO)

        if os.path.isdir(repo_dir):
            git_update(repo_dir, self.branch, base)
        else:
            git_clone(self.repo, repo_dir, self.branch, base)

        print("Create Android project...")

        cmd = "%s update project -n %s -t android-19 -p ." % (
            os.path.join(os.path.abspath(sdk_base), 'tools/android'),
            self._project.internal_name)
        process = subprocess.Popen(cmd, cwd=os.path.join(deps_dir, self.REPO),
                shell=True)
        process.wait()
        if process.returncode != 0:
            raise Exception("Application ended with error code %s." % process.returncode)

    def create_ant_properties(self):
        data = dedent("""\
        package.name=%s
        key.store=%s
        key.alias=%s
        """ % (
            self._project.target('android')['packageId'],
            self._project.target('android')['keyStore'],
            self._project.target('android')['keyAlias']
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

