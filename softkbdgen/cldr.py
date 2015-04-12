import lxml.etree
import itertools
import re

from lxml.etree import Element, SubElement
from io import StringIO
from collections import OrderedDict

CP_REGEX = re.compile(r"\\u{(.+?)}")

ENTITY_REGEX = re.compile(r"&#(\d+);")

def decode_u(v, newlines=True):
    def chk(x):
        vv = chr(int(x.group(1), 16))
        if newlines == False and vv in ('\n', '\r'):
            return x.group(0)
        return vv

    return CP_REGEX.sub(chk, v)

def encode_u(v): #
    return re.sub(r"([\x80-\xa0\xad\u2000-\u200f\u2011\u2028-\u202f\u205f-\u206f]|" +
                  r"[^\u0020-\u02af\u0370-\u1fff])",
        lambda x: r"\u{%X}" % ord(x.group(0)), v)

def key_cmp(x):
    ch, n = parse_cell(x[0])
    return -int(ch, 16) * 16 + n

def process_value(*args):
    def pv(v):
        return encode_u(decode_u(v))
#    def pv(v):
#        def p(x):
#            gv = int(x.group(1), 16)
#            if gv <= 0x20 or gv == 0xA0:
#                return x.group(0)
#            return chr(gv)
#        return CP_REGEX.sub(p, v)

    return tuple(pv(i) for i in args) if len(args) > 1 else pv(args[0])

def cell_range(ch, from_, to_):
    for i in range(from_, to_+1):
        yield "%s%02d" % (ch, i)

# E00 -> E12
# D01 -> D13
# C01 -> C11
# B00 -> B10

def parse_cell(x):
    a = x[0]
    b = int(x[1:])
    return a, b

def is_relevant_cell(x):
    ch, n = parse_cell(x)
    if ch == 'E':
        return 0 <= n <= 12
    if ch == 'D':
        return 1 <= n <= 13
    if ch == 'C':
        return 1 <= n <= 11
    if ch == 'B':
        return 0 <= n <= 10
    return False

def is_full_layout(o):
    """Strictly not accurate, as D13 is considered C12 for convenience."""

    chain = itertools.chain(
        cell_range('E', 0, 12),
        cell_range('D', 1, 12),
        cell_range('C', 1, 12),
        cell_range('B', 0, 10))

    for n, v in enumerate(chain):
        if v not in o:
            return False

    #if len(o) != n:
    #    return False

    return True

def filtered(v):
    if v == '"':
        return r'"\""'
    if v in " -?:,[]{}#&*!>'%@`~=":
        return '"%s"' % v
    return encode_u(v)

def to_xml(yaml_tree):
    tree = lxml.etree.fromstring("""<keyboard locale="%s"/>""" % \
            yaml_tree['internalName'])

    # TODO generate both these validly
    SubElement(tree, 'version')
    SubElement(tree, 'generation')

    names = SubElement(tree, 'names')
    SubElement(names, 'name',
            value=yaml_tree['displayNames'][yaml_tree['locale']])

    for mode, key_map in yaml_tree['modes'].items():
        if not mode.startswith('iso-'):
            continue

        mod = mode[4:]

        if mod == "default":
            node = SubElement(tree, 'keyMap')
        else:
            node = SubElement(tree, 'keyMap', modifiers=mod)

        if isinstance(key_map, dict):
            for k, v in sorted(key_map.items(), key=key_cmp):
                key_node = SubElement(node, 'map', iso=k, to=v)

                # TODO make this more optimal, chaining all lists and only
                # assigning when it makes sense to do so
                if v not in yaml_tree['deadKeys'].get(mode, {}):
                    key_node.attrib['transform'] = 'no'
        else:
            chain = itertools.chain(
                    cell_range('E', 0, 12),
                    cell_range('D', 1, 12),
                    cell_range('C', 1, 12),
                    cell_range('B', 0, 10))
            for iso, to in zip(chain, re.split(r"[\s\n]+", key_map)):
                key_node = SubElement(node, 'map', iso=iso, to=to)

                if to not in yaml_tree['deadKeys'].get(mode, {}):
                    key_node.attrib['transform'] = 'no'

        # Space special case!
        space = yaml_tree['special']['space'].get(mode, " ")
        SubElement(node, 'map', iso='A03', to=space)

    transforms = SubElement(tree, 'transforms', type="simple")

    for base, o in yaml_tree['transforms'].items():
        for tr_from, tr_to in o.items():
            n = SubElement(transforms, 'transform')
            n.attrib['from'] = "%s%s" % (base, tr_from)
            n.attrib['to'] = tr_to

    out = lxml.etree.tostring(tree, encoding='utf-8', pretty_print=True).decode()
    return ENTITY_REGEX.sub(lambda x: "\\u{%s}" % hex(int(x.group(1)))[2:].upper(), out)


class CLDRKeyboard:
    modes = {
        "default": "iso-default",
        "shift": "iso-shift",
        "opt": "iso-alt",
        "caps": "iso-caps",
        "caps+shift": "iso-shift+caps",
        "opt+shift+cmd?": "iso-alt+shift",
        "opt+caps": "iso-alt+caps",
        "opt+caps+shift": "iso-alt+shift+caps"
    }

    def __init__(self, data):
        self._modes = OrderedDict()

        # Actual transforms themselves
        self._transforms = OrderedDict()

        # Known deadkey glyphs
        self._deadkey_set = set()

        # Deadkey layouts
        self._deadkeys = OrderedDict()

        self._space = OrderedDict()

        tree = lxml.etree.fromstring(data)

        self._internal_name = tree.attrib['locale']
        self._locale = self._internal_name.split('-')[0]
        self._name = tree.xpath('names/name')[0].attrib['value']

        self._parse_transforms(tree)
        self._parse_keymaps(tree)

    def _parse_keymaps(self, tree):
        is_osx = self._internal_name.endswith('osx')

        for keymap in tree.xpath("keyMap"):
            mode = keymap.attrib.get('modifiers', 'default')
            new_mode = self.modes.get(mode, '??? %s' % mode)
            o = {}
            for key in keymap.xpath('map'):
                iso_key = key.attrib['iso']
                if not is_relevant_cell(iso_key):
                    if iso_key == "A03" and key.attrib['to'] != " ":
                        self._space[new_mode] = process_value(key.attrib['to'])
                    continue

                o[iso_key] = process_value(key.attrib['to'])
                if o[iso_key] in self._deadkey_set and \
                        key.attrib.get('transform', None) != "no":
                    self._deadkeys.setdefault(new_mode, set()).add(o[iso_key])

            # OS X definitions are in a pseudo-ANSI format that inverts
            # the E00 and B00 keys. No idea why.
            if is_osx:
                tmp = o['E00']
                o['E00'] = o['B00']
                o['B00'] = tmp

            # Force ANSI-style keys into the ISO world.
            if o.get('D13', None) is not None:
                o['C12'] = o['D13']
                del o['D13']

            self._modes[new_mode] = OrderedDict(sorted(o.items(), key=key_cmp))

    def _parse_transforms(self, tree):
        for transform in tree.xpath("transforms[@type='simple']/transform"):
            from_ = decode_u(transform.attrib['from'])
            self._deadkey_set.add(from_[0])
            self._transforms.setdefault(
                    from_[0], OrderedDict())[from_[1:]] = process_value(transform.attrib['to'])

    def keys(self, mode):
        return self._modes[mode]

    def as_yaml(self):
        x = StringIO()

        x.write("internalName: %s\n\n" % self._internal_name)
        x.write("displayNames:\n  %s: %s\n\n" % (self._locale, self._name))
        x.write("locale: %s\n\n" % self._locale)

        x.write("modes:\n")
        for mode, o in self._modes.items():
            if is_full_layout(o):
                x.write('  %s: |' % mode)
                cur = None
                for iso_key, value in o.items():
                    if cur != iso_key[0]:
                        x.write('\n   ')
                        cur = iso_key[0]
                    x.write(' ')
                    x.write(value)
                x.write('\n')
            else:
                x.write('  %s:\n' % mode)
                for iso_key, value in o.items():
                    x.write('    %s: %s\n' % (iso_key, filtered(value)))

        x.write("\ndeadKeys:\n")
        for mode, keys in self._deadkeys.items():
            x.write(('  %s: ["%s"]\n' % (mode, '", "'.join(keys))).replace(
                "\\", r"\\"))

        x.write("\ntransforms:\n")
        for base_ch, o in self._transforms.items():
            x.write('  %s:\n' % filtered(base_ch))
            for ch, v in o.items():
                x.write('    %s: %s\n' % (filtered(ch), filtered(v)))

        x.write("\nspecial:\n  space:\n")
        for mode, v in self._space.items():
            x.write('    %s: %s\n' % (mode, filtered(v)))

        return x.getvalue()


def kbd2yaml_main():
    import argparse, sys

    p = argparse.ArgumentParser(prog="cldr-kbd2yaml")
    p.add_argument('--osx', action='store_true',
                   help="Force detection of XML file as an OS X keyboard.")
    p.add_argument('cldr_xml', type=argparse.FileType('rb'),
                   default=sys.stdin)
    p.add_argument('yaml', type=argparse.FileType('w'),
                   default=sys.stdout)
    args = p.parse_args()

    args.yaml.write(CLDRKeyboard(args.cldr_xml.read()).as_yaml())

if __name__ == "__main__":
    kbd2yaml_main()

#if __name__ == "__main__":
#    import sys
#    v = CLDRKeyboard(open(sys.argv[1], 'rb').read()).as_yaml()
#    print(v)
#    import yaml
#
#    print(to_xml(yaml.load(StringIO(v))))
