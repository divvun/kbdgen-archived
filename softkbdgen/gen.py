import os
import os.path
import sys
import shutil
import subprocess
import copy
import re
import io
import json
import uuid
import plistlib
import random
import itertools

from textwrap import dedent, indent
from collections import OrderedDict, defaultdict
from itertools import zip_longest

import pycountry
from lxml import etree
from lxml.etree import Element, SubElement

from . import boolmap
from . import cldr

from .cldr import CP_REGEX, decode_u

ANDROID_GLYPHS = {}

for api in range(16, 21+1):
    if api in (17, 18, 20):
        continue
    with open(os.path.join(os.path.dirname(__file__), "android-glyphs-api%s.bin" % api), 'rb') as f:
        ANDROID_GLYPHS[api] = boolmap.BoolMap(f.read())

class CulturalImperialismException(Exception): pass

class MissingApplicationException(Exception): pass

# TODO use logger for output
# TODO move into util module...
def mode_iter(layout, key, required=False, fallback=None):
    mode = layout.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("'%s' has a required mode." % key)
        return itertools.repeat(fallback)

    if isinstance(mode, dict):
        def wrapper():
            for iso in WIN_KEYMAP:
                yield mode.get(iso, fallback)
        return wrapper()
    else:
        return itertools.chain.from_iterable(mode)


def git_clone(src, dst, branch, cwd='.'):
    print("Cloning repository '%s' to '%s'..." % (src, dst))

    cmd = ['git', 'clone', src, dst]

    process = subprocess.Popen(cmd, cwd=cwd)
    process.wait()

    git_update(dst, branch, cwd)


def git_update(dst, branch, cwd='.'):
    print("Updating repository '%s'..." % dst)

    cmd = """git reset --hard;
             git checkout %s;
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
    return json.loads(json_str, object_pairs_hook=OrderedDict)


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

    def create_plist_string_file(self, locale, name="InfoPlist.strings"):
        o = {
            "isa": "PBXFileReference",
            "lastKnownFileType": "text.plist.strings",
            "name": locale,
            "path": "%s.lproj/%s" % (locale, name),
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

    def find_variant_group(self, target):
        for o in self.objects.values():
            if o.get('isa', None) == 'PBXVariantGroup' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")
        return o

    def add_plist_strings_to_variant_group(self, locales, variant_name, target_name):
        variant = self.find_variant_group(variant_name)
        o = []
        for locale in locales:
            ref = self.create_plist_string_file(locale, target_name)
            variant['children'].append(ref)
            o.append(ref)
        return o

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

    def add_file(self, fmt, path, **kwargs):
        ref = Pbxproj.gen_key()

        o = {
            'isa': "PBXFileReference",
            "lastKnownFileType": fmt,
            "path": path,
            "sourceTree": "<group>"
        }

        o.update(kwargs)

        self.objects[ref] = o

        return ref

    def add_plist_file(self, path):
        return self.add_file("text.plist.xml", path)

    def add_swift_file(self, path):
        return self.add_file("sourcecode.swift", path, fileEncoding=4)

    def add_path(self, path_list, target=None):
        if target is None:
            target = self.main_group

        for name in path_list:
            children = [self.objects[r] for r in target['children']]
            for c in children:
                if c.get('path', None) == name:
                    target = c
                    break
            else:
                ref = Pbxproj.gen_key()

                o = {
                    "children": [],
                    "isa": "PBXGroup",
                    "path": name,
                    "sourceTree": "<group>"
                }

                self.objects[ref] = o
                target['children'].append(ref)
                target = self.objects[ref]

    def clear_target_dependencies(self, target):
        for o in self.objects.values():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")

        # HACK: unclear; leaves dangling nodes
        o['dependencies'] = []

    def clear_target_embedded_binaries(self, target):
        for o in self.objects.values():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")

        target_o = o
        for o in [self.objects[x] for x in target_o['buildPhases']]:
            if o.get('isa', None) == 'PBXCopyFilesBuildPhase' and\
                    o.get('name', None) == "Embed App Extensions":
                break
        else:
            raise Exception("No src found.")

        o['files'] = []

    def add_appex_to_target_embedded_binaries(self, appex, target):
        for appex_ref, o in self.objects.items():
            if o.get('isa', None) == 'PBXFileReference' and\
                    o.get('path', None) == appex:
                break
        else:
            raise Exception("No src found.")

        for o in self.objects.values():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")

        target_o = o
        for o in [self.objects[x] for x in target_o['buildPhases']]:
            if o.get('isa', None) == 'PBXCopyFilesBuildPhase' and\
                    o.get('name', None) == "Embed App Extensions":
                break
        else:
            raise Exception("No src found.")

        ref = Pbxproj.gen_key()
        appex_o = {
            "isa": "PBXBuildFile",
            "fileRef": appex_ref,
            "settings": {"ATTRIBUTES": ["RemoveHeadersOnCopy"]}
        }
        self.objects[ref] = appex_o

        o['files'].append(ref)

    def add_source_ref_to_build_phase(self, ref, target):
        for o in self.objects.values():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")

        target_o = o
        for o in [self.objects[x] for x in target_o['buildPhases']]:
            if o.get('isa', None) == 'PBXSourcesBuildPhase':
                break
        else:
            raise Exception("No src found.")

        nref = Pbxproj.gen_key()
        self.objects[nref] = {
            "isa": "PBXBuildFile",
            "fileRef": ref
        }

        o['files'].append(nref)

    def remove_target(self, target):
        for ref, o in self.objects.items():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == target:
                break
        else:
            raise Exception("No src found.")
        prod_ref = o['productReference']
        #del self.objects[o['productReference']]

        for nref, o in self.objects.items():
            if o.get('isa', None) == 'PBXBuildFile' and\
                    o.get('fileRef', None) == prod_ref:
                break
        else:
            raise Exception("No src found.")

        for o in self.objects.values():
            if o.get('isa', None) == 'PBXGroup' and\
                    o.get('name', None) == "Products":
                break
        else:
            raise Exception("No src found.")

        o['children'].remove(prod_ref)
        self.root['targets'].remove(ref)

    def duplicate_target(self, src_name, dst_name, plist_path):
        for o in self.objects.values():
            if o.get('isa', None) == 'PBXNativeTarget' and\
                    o.get('name', None) == src_name:
                break
        else:
            raise Exception("No src found.")

        base_clone = copy.deepcopy(o)
        base_ref = Pbxproj.gen_key()
        self.objects[base_ref] = base_clone

        new_phases = []
        for phase in base_clone['buildPhases']:
            ref = Pbxproj.gen_key()
            new_phases.append(ref)
            self.objects[ref] = copy.deepcopy(self.objects[phase])
        base_clone['buildPhases'] = new_phases
        base_clone['name'] = dst_name

        conf_ref = Pbxproj.gen_key()
        conf_clone = copy.deepcopy(self.objects[base_clone['buildConfigurationList']])
        self.objects[conf_ref] = conf_clone
        base_clone['buildConfigurationList'] = conf_ref

        new_confs = []
        for conf in conf_clone['buildConfigurations']:
            ref = Pbxproj.gen_key()
            new_confs.append(ref)
            self.objects[ref] = copy.deepcopy(self.objects[conf])

            self.objects[ref]['buildSettings']['INFOPLIST_FILE'] = plist_path
            self.objects[ref]['buildSettings']['PRODUCT_NAME'] = dst_name
        conf_clone['buildConfigurations'] = new_confs

        appex_ref = Pbxproj.gen_key()
        appex_clone = copy.deepcopy(self.objects[base_clone['productReference']])
        self.objects[appex_ref] = appex_clone
        appex_clone['path'] = "%s.appex" % dst_name
        base_clone['productReference'] = appex_ref

        # HACK: have to generate PBXContainerItemProxy etc for this to work
        base_clone['dependencies'] = []

        self.add_ref_to_group(appex_ref, ['Products'])

        self.root['targets'].append(base_ref)

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

WIN_KEYMAP = OrderedDict((
    ("E00", "29"),
    ("E01", "02"),
    ("E02", "03"),
    ("E03", "04"),
    ("E04", "05"),
    ("E05", "06"),
    ("E06", "07"),
    ("E07", "08"),
    ("E08", "09"),
    ("E09", "0a"),
    ("E10", "0b"),
    ("E11", "0c"),
    ("E12", "0d"),
    ("D01", "10"),
    ("D02", "11"),
    ("D03", "12"),
    ("D04", "13"),
    ("D05", "14"),
    ("D06", "15"),
    ("D07", "16"),
    ("D08", "17"),
    ("D09", "18"),
    ("D10", "19"),
    ("D11", "1a"),
    ("D12", "1b"),
    ("C01", "1e"),
    ("C02", "1f"),
    ("C03", "20"),
    ("C04", "21"),
    ("C05", "22"),
    ("C06", "23"),
    ("C07", "24"),
    ("C08", "25"),
    ("C09", "26"),
    ("C10", "27"),
    ("C11", "28"),
    ("D13", "2b"), #C12
    ("B00", "56"),
    ("B01", "2c"),
    ("B02", "2d"),
    ("B03", "2e"),
    ("B04", "2f"),
    ("B05", "30"),
    ("B06", "31"),
    ("B07", "32"),
    ("B08", "33"),
    ("B09", "34"),
    ("B10", "35")
))

# SC 53 is decimal, 39 is space
WIN_VK_MAP = OrderedDict(((k, v) for k, v in zip(WIN_KEYMAP.keys(), (
    "OEM_5", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "OEM_PLUS", "OEM_4",
    "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "OEM_6", "OEM_1",
    "A", "S", "D", "F", "G", "H", "J", "K", "L", "OEM_3", "OEM_7", "OEM_2",
    "OEM_102", "Z", "X", "C", "V", "B", "N", "M", "OEM_COMMA", "OEM_PERIOD", "OEM_MINUS"
))))

#TODO move to cldr.py
class WindowsGenerator(Generator):
    def generate(self, base='.'):
        outputs = OrderedDict()

        for name, layout in self._project.layouts.items():
            outputs[name] = self.generate_klc(layout)

        if self.dry_run:
            print("Dry run completed.")
            return

        build_dir = os.path.join(base, 'build', 'win',
                self._project.internal_name)
        os.makedirs(build_dir, exist_ok=True)

        for name, data in outputs.items():
            with open(os.path.join(build_dir, "%s.klc" % name), 'w') as f:
                f.write(data.replace('\n', '\r\n'))

    def _klc_write_headers(self, layout, buf):
        buf.write('KBD\tkbd%s\t"%s"\n\n' % (
            re.sub(r'[^A-Za-z0-9]', "", layout.internal_name)[:5],
            layout.display_names[layout.locale]))

        copyright = self._project.copyright
        organisation = self._project.organisation

        buf.write('COPYRIGHT\t"%s"\n\n' % copyright)
        buf.write('COMPANY\t"%s"\n\n' % organisation)
        buf.write('LOCALENAME\t"%s"\n\n' % layout.locale)
        # Use fallback ID in every case (MS-LCID)
        buf.write('LOCALEID\t"00001000"\n\n')
        buf.write('VERSION\t1.0\n\n')
        # 0: default, 1: shift, 2: ctrl, 6: altGr/ctrl+alt, 7: shift+6
        buf.write('SHIFTSTATE\n\n0\n1\n2\n6\n7\n\n')

        buf.write('LAYOUT       ;\n\n')
        buf.write('//SC\tVK_ \t\tCaps\tNormal\tShift\tCtrl\tAltGr\tAltShft\t-> Output\n')
        buf.write('//--\t----\t\t----\t------\t-----\t----\t-----\t-------\t   ------\n\n')

    def _klc_write_keys(self, layout, buf):
        # TODO support the key-value mode with a wrapper

        col0 = mode_iter(layout, 'iso-default', required=True)
        col1 = mode_iter(layout, 'iso-shift')
        col2 = mode_iter(layout, 'iso-ctrl')
        col6 = mode_iter(layout, 'iso-alt')
        col7 = mode_iter(layout, 'iso-alt+shift')

        # TODO support SGCAP!

        caps = mode_iter(layout, 'iso-caps')
        altcaps = mode_iter(layout, 'iso-alt+caps')
        #capsshift = mode_iter(layout, 'iso-shift+caps')
        #altcapsshift = mode_iter(layout, 'iso-alt+shift+caps')

        def win_filter(*args, force=False):
            def wf(v):
                """actual filter function"""
                if v is None:
                    return '-1'

                if re.match(r"^\d{4}$", v):
                    return v

                v = decode_u(v)

                # check for anything outsize A-Za-z range
                if not force and re.match("^[A-Za-z]$", v):
                    return v

                return "%04x" % ord(v)

            return tuple(wf(i) for i in args)

        def win_ligature(v):
            o = tuple('%04x' % ord(c) for c in decode_u(v))
            if len(o) > 4:
                raise Exception('Ligatures cannot be longer than 4 codepoints.')
            return o

        # Hold all the ligatures
        ligatures = []

        for (sc, vk, c0, c1, c2, c6, c7, cap) in zip_longest(WIN_KEYMAP.values(),
                WIN_VK_MAP.values(), col0, col1, col2, col6, col7, caps,
                fillvalue="-1"):

            print((sc, vk, c0, c1, c2, c6, c7, cap))
            # TODO cap state (last one) 5 means caps applies in altgr state
            # TODO handle the altgr caps

            if cap is None:
                cap_mode = "1" if c0 != c1 else "0"
            else:
                cap_mode = "1" if cap == c1 else "0"

            if len(vk) < 8:
                vk += "\t"
            buf.write("%s\t%s\t%s" % (sc, vk, cap_mode))
            for n, mode, key in ((0, 'iso-default', c0),
                                 (1, 'iso-shift', c1),
                                 (2, 'iso-ctrl', c2),
                                 (6, 'iso-alt', c6),
                                 (7, 'iso-alt+shift', c7)):

                filtered = decode_u(key or '')
                if key is not None and len(filtered) > 1:
                    buf.write("\t%%")
                    ligatures.append((filtered, (vk, str(n)) + win_ligature(key)))
                else:
                    buf.write("\t%s" % win_filter(key))
                    if key in layout.dead_keys.get(mode, []):
                        buf.write("@")

            buf.write("\t  // %s %s %s %s %s\n" % (c0, c1, c2, c6, c7))

        # Space, such special case oh my.
        buf.write("39\tSPACE\t\t0\t")
        if layout.special.get('space', None) is None:
            buf.write("0020\t0020\t0020\t-1\t-1\n")
        else:
            o = layout.special['space']
            buf.write("%s\t%s\t%s\t%s\t%s\n" % win_filter(
                    o.get('iso-default', '0020'),
                    o.get('iso-shift', '0020'),
                    o.get('iso-ctrl', '0020'),
                    o.get('iso-alt', '-1'),
                    o.get('iso-alt+shift', '-1')
                ))

        # Decimal key on keypad.
        buf.write("53\tDECIMAL\t\t0\t%s\t%s\t-1\t-1\t-1\n\n" % win_filter(
            layout.decimal, layout.decimal))

        # Ligatures!
        if len(ligatures) > 0:
            buf.write("LIGATURE\n\n")
            buf.write("//VK_\tMod#\tChr0\tChr1\tChr2\tChr3\n")
            buf.write("//----\t----\t----\t----\t----\t----\n\n")
            for original, row in ligatures:
                more_tabs = len(row)-7
                buf.write("%s\t\t%s%s\t// %s\n" % (row[0],
                    "\t".join(row[1:]),
                    '\t' * more_tabs,
                    original))
            buf.write('\n')

        # Deadkeys!
        for basekey, o in layout.transforms.items():
            buf.write("DEADKEY\t%s\n\n" % win_filter(basekey))
            for key, output in o.items():
                if key == ' ':
                    continue

                key = str(key)
                output = str(output)

                if len(key) != 1 or len(output) != 1:
                    print(("WARNING: %s%s -> %s is invalid for Windows " +
                           "deadkeys; skipping.") % (basekey, key, output))
                    continue
                buf.write("%s\t%s\t// %s -> %s\n" % (
                    win_filter(key, output, force=True) + (key, output)))

            # Create fallback key from space, or the basekey.
            output = o.get(' ', basekey)
            buf.write("0020\t%s\t// fallback -> %s\n\n" % (
                win_filter(output)[0], output))


    def generate_klc(self, layout):
        buf = io.StringIO()

        self._klc_write_headers(layout, buf)
        self._klc_write_keys(layout, buf)

        buf.write("ENDKBD\n")

        return buf.getvalue()
        # TODO constrain caps to be inverse of default. Always.

OSX_KEYMAP = {
    'C01': '0',
    'C02': '1',
    'C03': '2',
    'C04': '3',
    'C06': '4',
    'C05': '5',
    'B01': '6',
    'B02': '7',
    'B03': '8',
    'B04': '9',
    'B00': '50', # E00 flipped!
    'B05': '11',
    'D01': '12',
    'D02': '13',
    'D03': '14',
    'D04': '15',
    'D06': '16',
    'D05': '17',
    'E01': '18',
    'E02': '19',
    'E03': '20',
    'E04': '21',
    'E06': '22',
    'E05': '23',
    'E12': '24',
    'E09': '25',
    'E07': '26',
    'E11': '27',
    'E08': '28',
    'E10': '29',
    'D12': '30',
    'D09': '31',
    'D07': '32',
    'D11': '33',
    'D08': '34',
    'D10': '35',
    # U WOT 36 - space yeah yeah
    'C09': '37',
    'C07': '38',
    'C11': '39',
    'C08': '40',
    'C10': '41',
    'D13': '42',
    'B08': '43',
    'B10': '44',
    'B06': '45',
    'B07': '46',
    'B09': '47',
    # U WOT 48 - backspace yeah yeah
    'A03': '49',
    'E00': '10', # B00 flipped!
    'E13': '93',
    'B11': '94'
}

OSX_HARDCODED = OrderedDict((
    ("36", r"\u{D}"),
    ("48", r"\u{9}"),
    ("51", r"\u{8}"),
    ("53", r"\u{1B}"),
    ("64", r"\u{10}"),
    ("66", r"\u{1D}"),
    ("70", r"\u{1C}"),
    ("71", r"\u{1B}"),
    ("72", r"\u{1F}"),
    ("76", r"\u{3}"),
    ("77", r"\u{1E}"),
    ("79", r"\u{10}"),
    ("80", r"\u{10}"),
    ("96", r"\u{10}"),
    ("97", r"\u{10}"),
    ("98", r"\u{10}"),
    ("99", r"\u{10}"),
    ("100", r"\u{10}"),
    ("101", r"\u{10}"),
    ("103", r"\u{10}"),
    ("105", r"\u{10}"),
    ("106", r"\u{10}"),
    ("107", r"\u{10}"),
    ("109", r"\u{10}"),
    ("111", r"\u{10}"),
    ("113", r"\u{10}"),
    ("114", r"\u{5}"),
    ("115", r"\u{1}"),
    ("116", r"\u{B}"),
    ("117", r"\u{7F}"),
    ("118", r"\u{10}"),
    ("119", r"\u{4}"),
    ("120", r"\u{10}"),
    ("121", r"\u{C}"),
    ("122", r"\u{10}"),
    ("123", r"\u{1C}"),
    ("124", r"\u{1D}"),
    ("125", r"\u{1F}"),
    ("126", r"\u{1E}")
))

def iterable_set(iterable):
    return {i for i in itertools.chain.from_iterable(iterable)}

def random_id():
    return str(-random.randrange(1, 32768))

class OSXKeyLayout:
    doctype = '<!DOCTYPE keyboard PUBLIC "" ' +\
              '"file://localhost/System/Library/DTDs/KeyboardLayout.dtd">'

    modes = OrderedDict((
        ('iso-default', ('command?', 'anyShift? caps? command')),
        ('iso-shift', ('anyShift caps?',)),
        ('iso-caps', ('caps',)),
        ('iso-shift+caps', ('anyShift caps',)),
        ('iso-alt', ('anyOption', 'caps? anyOption command')),
        ('iso-alt+shift', ('anyShift anyOption',
                           'anyShift caps? anyOption command')),
        ('iso-alt+caps', ('caps anyOption',)),
        ('iso-alt+shift+caps', ('anyShift anyOption caps',)),
        ('iso-ctrl', (
            "anyShift? caps? anyOption? anyControl",
            "anyShift? anyOption? command? anyControl",
            "anyShift caps anyOption command rightControl",
            "anyShift caps rightOption? command anyControl",
            "rightShift? caps anyOption command anyControl",
            "anyShift caps anyOption command control",
            "anyShift caps option? command anyControl",
            "shift? caps anyOption command anyControl",
            "caps? anyOption? command? anyControl"))
        ))

    def __bytes__(self):
        """XML almost; still encode the control chars. Death to standards!"""
        v = CP_REGEX.sub(lambda x: "&#x%04X;" % int(x.group(1), 16),
                str(self))
        # TODO compile not sub
        v = re.sub(r"[^\0-\u02af]",
                lambda x: "&#x%04X;" % ord(x.group(0)),
                v)

        return ('<?xml version="1.0" encoding="UTF-8"?>\n%s' % v).encode('utf-8')

    def __str__(self):
        return etree.tostring(self.elements['root'], encoding='unicode',
                           doctype=self.doctype, pretty_print=True)

    def __init__(self, name, id_):
        modifiers_ref = "modifiers"
        mapset_ref = "default"

        self.elements = {}

        root = Element('keyboard', group="126", id=id_, name=name)
        self.elements['root'] = root

        self.elements['layouts'] = SubElement(root, 'layouts')

        SubElement(self.elements['layouts'], 'layout', first="0", last="17",
                mapSet=mapset_ref, modifiers=modifiers_ref)

        self.elements['modifierMap'] = SubElement(root, 'modifierMap',
                id=modifiers_ref, defaultIndex="0")

        self.elements['keyMapSet'] = SubElement(root, 'keyMapSet',
                id=mapset_ref)

        self.elements['actions'] = SubElement(root, 'actions')

        self.elements['terminators'] = SubElement(root, 'terminators')

        self.key_cache = {}
        self.kmap_cache = {}
        self.action_cache = {}

        self._n = 0
        #self._init_modifier_maps()

    def _add_modifier_map(self, mode):
        mm = self.elements['modifierMap']
        kms = self.elements['keyMapSet']

        node = SubElement(mm, 'keyMapSelect', mapIndex=str(self._n))
        for mod in self.modes[mode]:
            SubElement(node, 'modifier', keys=mod)

        self.kmap_cache[mode] = SubElement(kms, 'keyMap', index=str(self._n))
        self._n += 1
        return self.kmap_cache[mode]

    def _init_modifier_maps(self):
        mm = self.elements['modifierMap']
        kms = self.elements['keyMapSet']

        for n, (mode, mods) in enumerate(self.modes.items()):
            node = SubElement(mm, 'keyMapSelect', mapIndex=str(n))
            for mod in mods:
                SubElement(node, 'modifier', keys=mod)

            self.kmap_cache[mode] = SubElement(kms, 'keyMap', index=str(n))

    def _get_kmap(self, mode):
        kmap = self.kmap_cache.get(mode, None)
        if kmap is not None:
            return kmap
        return self._add_modifier_map(mode)

    def _set_key(self, mode, key, key_id, action=None, output=None):
        if action is not None and output is not None:
            raise Exception("Cannot specify contradictory action and output.")

        key_key = "%s %s" % (mode, key_id)

        node = self.key_cache.get(key_key, None)

        if node is None:
            kmap_node = self._get_kmap(mode)
            node = SubElement(kmap_node, "key", code=key_id)
            self.key_cache[key_key] = node

        if action is not None:
            node.attrib['action'] = action
            if node.attrib.get('output', None):
                del node.attrib['output']
        elif output is not None:
            node.attrib['output'] = output
            if node.attrib.get('action', None):
                del node.attrib['action']

    def _set_default_action(self, action_id):
        pressed_id = "%s Pressed" % action_id
        action = self.action_cache.get(action_id, None)

        if action is None:
            action = SubElement(self.elements['actions'], 'action',
                     id=action_id)
            self.action_cache[action_id] = action

        if len(action.xpath('when[@state="none"]')) == 0:
            SubElement(action, 'when', state='none', next=pressed_id)

    def _set_terminator(self, action_id, output):
        termin = self.elements['terminators'].xpath(
                        'when[@state="%s"]' % action_id)

        if len(termin) == 0:
            SubElement(self.elements['terminators'], 'when', state=action_id,
                    output=output)

    def _set_default_transform(self, action_id, output):
        action = self.action_cache.get(action_id, None)

        # TODO create a generic create or get method for actions
        if action is None:
            action = SubElement(self.elements['actions'], 'action',
                     id=action_id)
            self.action_cache[action_id] = action

        if len(action.xpath('when[@state="none"]')) == 0:
            SubElement(action, 'when', state='none', output=output)

    def set_key(self, mode, key, key_id):
        self._set_key(mode, key, key_id, output=key)

    def set_deadkey(self, mode, key, key_id, output):
        """output is the output when the deadkey is followed by an invalid"""
        action_id = "Key %s" % key
        pressed_id = "%s Pressed" % action_id

        self._set_key(mode, key, key_id, action=action_id)

        # Create default action (set to pressed state)
        self._set_default_action(action_id)
        self._set_terminator(pressed_id, output)

    def set_transform_key(self, mode, key, key_id):
        action_id = "Key %s" % key
        pressed_id = "%s Pressed" % action_id

        self._set_key(mode, key, key_id, action=pressed_id)

        # Find action, add none state (move the output)
        self._set_default_transform(pressed_id, key)

    def add_transform(self, action_id, state, output=None, next=None):
        action = self.action_cache.get(action_id, None)

        if action is None:
            raise Exception("'%s' was not a found action_id." % action_id)

        if state is not None and next is not None:
            raise Exception("State and next cannot be simultaneously defined.")

        if output is not None:
            SubElement(action, 'when', state=state, output=output)
        elif next is not None:
            SubElement(action, 'when', state=state, next=next)


class OSXGenerator(Generator):
    def generate(self, base='.'):
        self.build_dir = os.path.abspath(os.path.join(base, 'build',
                'osx', self._project.internal_name))

        o = OrderedDict()

        for name, layout in self._project.layouts.items():
            o[name] = self.generate_xml(layout)

        if self.dry_run:
            print("Dry run completed.")
            return

        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        bundle = os.path.join(self.build_dir,
                 "%s.bundle" % self._project.internal_name)

        bundle_path = self.create_bundle(self.build_dir)
        res_path = os.path.join(bundle_path, "Contents", "Resources")

        for name, data in o.items():
            layout = self._project.layouts[name]
            fn = layout.display_names[layout.locale]
            with open(os.path.join(res_path, "%s.keylayout" % fn), 'w') as f:
                f.write(data)

        self.create_installer(bundle_path)

    def create_bundle(self, path):
        bundle_path = os.path.join(path, "%s.bundle" % self._project.internal_name)
        os.makedirs(os.path.join(bundle_path, 'Contents', 'Resources'),
            exist_ok=True)

        bundle_id = "%s.keyboardlayout.%s" % (
                self._project.target('osx')['packageId'],
                self._project.internal_name
            )

        target_tmpl = indent(dedent("""\
<key>KLInfo_%s</key>
<dict>
    <key>TISInputSourceID</key>
    <string>%s.%s</string>
    <key>TISIntendedLanguage</key>
    <string>%s</string>
</dict>"""), "        ")

        targets = []
        for name, layout in self._project.layouts.items():
            name = layout.display_names[layout.locale]
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
%s
    </dict>
</plist>
                """) % (
                    bundle_id,
                    self._project.target('osx')['bundleName'],
                    self._project.build,
                    '\n'.join(targets)
                )
            )

        return bundle_path

    def create_installer(self, bundle):
        cmd = ['productbuild', '--component',
                bundle, '/Library/Keyboard Layouts',
                "%s.pkg" % self._project.internal_name]

        process = subprocess.Popen(cmd, cwd=self.build_dir,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        out, err = process.communicate()

        if process.returncode != 0:
            print(err.decode())
            print("Application ended with error code %s." % process.returncode)
            sys.exit(process.returncode)

    def generate_xml(self, layout):
        name = layout.display_names[layout.locale]
        out = OSXKeyLayout(name, random_id())

        # Naively add all keys
        for mode_name in OSXKeyLayout.modes:
            # TODO throw on null
            mode = layout.modes.get(mode_name, None)
            if mode is None:
                print("WARNING: layout '%s' has no mode '%s'" % (
                    layout.internal_name, mode_name))
                continue

            if isinstance(mode, dict):
                keyiter = mode_iter(layout, mode_name)
            else:
                keyiter = itertools.chain.from_iterable(mode)
            action_keys = { str(i) for j in layout.transforms.keys()
                             for i in layout.transforms[j] }
            for (iso, key) in zip(WIN_KEYMAP, keyiter):
                if key is None:
                    continue

                key_id = OSX_KEYMAP[iso]

                if key in layout.dead_keys.get(mode_name, []):
                    out.set_deadkey(mode_name, key, key_id,
                            layout.transforms[key].get(' ', key))
                else:
                    out.set_key(mode_name, key, key_id)

                # Now cater for transforms too
                if key in action_keys:
                    out.set_transform_key(mode_name, key, key_id)

            # Space bar special case
            sp = layout.special.get('space', {}).get(mode_name, " ")
            out.set_key(mode_name, sp, "49")
            out.set_transform_key(mode_name, sp, "49")

            # Add hardcoded keyboard bits
            for key_id, key in OSX_HARDCODED.items():
                out.set_key(mode_name, key, key_id)

            # TODO Generate default cmd pages!

        # Generate remaining transforms
        for base, o in layout.transforms.items():
            base_id = "Key %s Pressed" % base
            for trans_key, output in o.items():
                if len(decode_u(str(trans_key))) > 1:
                    print("WARNING: '%s' has len longer than 1; not supported yet." % trans_key)
                    continue
                key_id = "Key %s Pressed" % trans_key
                out.add_transform(key_id, base_id, output=output)

        return bytes(out).decode('utf-8')


class XKBGenerator(Generator):
    def generate(self, base='.'):
        for name, layout in self._project.layouts.items():
            print(self.generate_nonsense(name, layout))

        if self.dry_run:
            print("Dry run completed.")
            return

    def generate_nonsense(self, name, layout):
        buf = io.StringIO()

        buf.write("default partial alphanumeric_keys\n")
        buf.write('xkb_symbols "basic" {\n')
        buf.write('    name[Group1]= "%s";\n' % layout.display_names[layout.locale])
        buf.write('    include "us(basic)"\n\n')

        col0 = mode_iter(layout, 'iso-default', required=True)
        col1 = mode_iter(layout, 'iso-shift')
        col2 = mode_iter(layout, 'iso-alt')
        col3 = mode_iter(layout, 'iso-alt+shift')

        def xkb_filter(*args):
            def xf(v):
                """actual filter function"""
                if v is None:
                    return ''

                v = CP_REGEX.sub(lambda x: chr(int(x.group(1), 16)), v)

                # check for anything outsize A-Za-z range
                if re.match("^[A-Za-z]$", v):
                    return v

                return "U%04X" % ord(v)

            o = [xf(i) for i in args]
            while len(o) > 0 and o[-1] == '':
                o.pop()
            return tuple(o)

        for (iso, c0, c1, c2, c3) in zip(WIN_KEYMAP.keys(), col0, col1, col2, col3):
            cols = ", ".join("%10s" % x for x in xkb_filter(c0, c1, c2, c3))
            buf.write("    key <A%s> { [ %s ] };\n" % (iso, cols))

        buf.write('\n    include "level3(ralt_switch)"\n};')
        return buf.getvalue()


class AppleiOSGenerator(Generator):
    def generate(self, base='.'):
        # TODO sanity checks

        if self.dry_run:
            print("Dry run completed.")
            return

        build_dir = os.path.join(base, 'build',
                'ios', self._project.target('ios')['packageId'])

        if os.path.isdir(build_dir):
            git_update(build_dir, self.branch, base)
        else:
            git_clone(self.repo, build_dir, self.branch, base)

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
            print("You may now open TastyImitationKeyboard.xcodeproj in '%s'." %\
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

            print(msg)
            process = subprocess.Popen(cmd, cwd=build_dir, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                print(err.decode())
                print("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)

        if os.path.exists(xcarchive):
            shutil.rmtree(xcarchive)
        print("Done! -> %s" % ipa)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def gen_hosting_app_icons(self, build_dir):
        if self._project.icon('ios') is None:
            print("Warning: no icon supplied!")
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

            print("Creating '%s' from '%s'..." % (fn, icon))
            process = subprocess.Popen(cmd, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                print(err.decode())
                print("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)

        with open(os.path.join(path, "Contents.json"), 'w') as f:
            json.dump(contents, f)


    def get_translatables_from_storyboard(self, xml_fn):
        with open(xml_fn) as f:
            tree = etree.parse(f)

        o = []
        for key, node, attr_node in [(n.attrib['value'], n.getparent().getparent(), n)
                for n in tree.xpath("//*[@keyPath='translate']")]:
            if node.attrib.get('placeholder', None) is not None:
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
            print("Error: no package ID provided for Android target.")

        for name, kbd in self._project.layouts.items():
            for dn_locale in kbd.display_names:
                if dn_locale in ['zz', kbd.locale]:
                    continue
                try:
                    pycountry.languages.get(alpha2=dn_locale)
                except KeyError:
                    sane = False
                    print(("[%s] Error: '%s' is not a supported locale. " +\
                          "You should provide the code in ISO 639-1 " +\
                          "format, if possible.") % (
                        name, dn_locale))

            for mode, rows in kbd.modes.items():
                for n, row in enumerate(rows):
                    if len(row) > 11:
                        print(("[%s] Warning: row %s has %s keys. It is " +\
                               "recommended to have less than 12 keys per " +\
                               "row.") % (name, n+1, len(row)))

            self.detect_unavailable_glyphs_long_press(kbd, 16)
            self.detect_unavailable_glyphs_long_press(kbd, 19)
            self.detect_unavailable_glyphs_long_press(kbd, 21)
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

    def generate_icons(self, base):
        icon = self._project.icon('android')
        if icon is None:
            print("Warning: no icon supplied!")
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

            print("Creating '%s' at size %dx%d" % (mipmap_dir, dimen, dimen))
            process = subprocess.Popen(cmd, shell=True,
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = process.communicate()
            if process.returncode != 0:
                print(err.decode())
                print("Application ended with error code %s." % process.returncode)
                sys.exit(process.returncode)


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
        print("Updating '%s'..." % fn)

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

        print("Updating 'res/xml/method.xml'...")
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
            print("Updating 'res/%s/method.xml'..." % xmlv)
            os.makedirs(path % xmlv, exist_ok=True)
            with open(fn % xmlv, 'w') as f:
                f.write(self.gen_method_xml(kbds, copy.deepcopy(tree)))

    def save_files(self, files, base):
        fn = os.path.join(base, 'deps', self.REPO)
        for k, v in files:
            with open(os.path.join(fn, k), 'w') as f:
                print("Creating '%s'..." % k)
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
            print("Warning: no glyphs file found for API %s! Can't detect " +
                  "missing characters from Android font!" % api_ver)
            return

        for vals in layout.longpress.values():
            for v in vals:
                for c in v:
                    if glyphs[ord(c)] is False:
                        print("[%s] Warning: '%s' (codepoint: U+%04X) is not supported by API %s!" % (
                            layout.internal_name,
                            c, ord(c), api_ver))

    def detect_unavailable_glyphs_keys(self, key, api_ver):
        glyphs = ANDROID_GLYPHS.get(api_ver, None)
        if glyphs is None:
            print("Warning: no glyphs file found for API %s! Can't detect " +
                  "missing characters from Android font!" % api_ver)
            return
