import datetime
import itertools
import os.path
import re
import unicodedata

import lxml.etree
from lxml.etree import SubElement
from io import StringIO
from collections import OrderedDict, namedtuple

from .base import get_logger

logger = get_logger(__file__)

CP_REGEX = re.compile(r"\\u{(.+?)}")
ENTITY_REGEX = re.compile(r"&#(\d+);")

BAD_UNICODE_CATS = ("C", "Z", "M")


def cldr_sub(value, repl, ignore_space=False):
    def r(x):
        c = unicodedata.category(x)[0]
        if (ignore_space and x == " ") or c not in BAD_UNICODE_CATS:
            return x
        else:
            return repl(x, c)

    return "".join([r(x) for x in value])


def decode_u(v, newlines=True):
    def chk(x):
        vv = chr(int(x.group(1), 16))
        if not newlines and vv in ("\n", "\r"):
            return x.group(0)
        return vv

    if v is None:
        v = ""

    return CP_REGEX.sub(chk, str(v))


def encode_u(v):
    return cldr_sub(v, lambda x, c: r"\u{%X}" % ord(x))


def key_cmp(x):
    ch, n = parse_cell(x[0])
    return -int(ch, 16) * 16 + n


def process_value(*args):
    pv = lambda v: encode_u(decode_u(v))  # noqa: E731
    return tuple(pv(i) for i in args) if len(args) > 1 else pv(args[0])


def cell_range(ch, from_, to_):
    for i in range(from_, to_ + 1):
        yield "%s%02d" % (ch, i)


def parse_cell(x):
    a = x[0]
    b = int(x[1:])
    return a, b


def is_relevant_cell(x):
    ch, n = parse_cell(x)
    if ch == "E":
        return 0 <= n <= 12
    if ch == "D":
        return 1 <= n <= 12
    if ch == "C":
        return 1 <= n <= 12
    if ch == "B":
        return 0 <= n <= 10
    return False


class UnknownNgramException(Exception):
    pass


def split_for_set(s, string):
    o = []
    i = len(string)
    while len(string) > 0:
        in_set = string[:i] in s
        if in_set:
            o.append(string[:i])
            string = string[i:]
            i = len(string)
        elif i == 1:
            raise UnknownNgramException("'%s' not found in set." % string)
        else:
            i -= 1
    return tuple(o)


def keyboard_range():
    return itertools.chain(
        cell_range("E", 0, 12),
        cell_range("D", 1, 12),
        cell_range("C", 1, 12),
        cell_range("B", 0, 10),
    )


def is_full_layout(o):
    """Strictly not accurate, as D13 is considered C12 for convenience."""

    chain = keyboard_range()

    for v in chain:
        if v not in o:
            return False

    return True


def filtered(v):
    if v == '"':
        return "'\"'"
    if v == "\\":
        # TODO check if this is necessary in practice
        return r'"\\"'
    if v in r" |-?:,[]{}#&*!>'%@`~=":
        return '"%s"' % v
    return encode_u(v)


def to_xml(yaml_tree):
    tree = lxml.etree.fromstring(
        """<keyboard locale="%s"/>""" % yaml_tree["internalName"]
    )

    # TODO generate both these validly
    SubElement(tree, "version")
    SubElement(tree, "generation")

    names = SubElement(tree, "names")
    SubElement(names, "name", value=yaml_tree["displayNames"][yaml_tree["locale"]])

    for mode, key_map in yaml_tree["modes"].items():
        if not mode.startswith("iso-"):
            continue

        mod = mode[4:]

        if mod == "default":
            node = SubElement(tree, "keyMap")
        else:
            node = SubElement(tree, "keyMap", modifiers=mod)

        deadkey_set = {
            x for x in itertools.chain.from_iterable(yaml_tree["deadKeys"].values())
        }

        if isinstance(key_map, dict):
            for k, v in sorted(key_map.items(), key=key_cmp):
                key_node = SubElement(node, "map", iso=str(k), to=str(v))

                # TODO make this more optimal, chaining all lists and only
                # assigning when it makes sense to do so
                if v in deadkey_set and v not in yaml_tree["deadKeys"].get(mode, {}):
                    key_node.attrib["transform"] = "no"
        else:
            chain = keyboard_range()
            for iso, to in zip(chain, re.split(r"[\s\n]+", key_map)):
                # Ignore nulls
                if to == r"\u{0}":
                    continue

                key_node = SubElement(node, "map", iso=iso, to=to)

                if to in deadkey_set and to not in yaml_tree["deadKeys"].get(mode, {}):
                    key_node.attrib["transform"] = "no"

        # Space special case!
        space = yaml_tree.get("special", {}).get("space", {}).get(mode, " ")
        SubElement(node, "map", iso="A03", to=space)

    transforms = SubElement(tree, "transforms", type="simple")

    for base, o in yaml_tree["transforms"].items():
        for tr_from, tr_to in o.items():
            n = SubElement(transforms, "transform")
            n.attrib["from"] = "%s%s" % (base, tr_from)
            n.attrib["to"] = tr_to

    out = lxml.etree.tostring(
        tree, xml_declaration=True, encoding="utf-8", pretty_print=True
    ).decode()
    return ENTITY_REGEX.sub(lambda x: "\\u{%s}" % hex(int(x.group(1)))[2:].upper(), out)


class CLDRKeyboard:
    @classmethod
    def from_file(cls, f):
        return cls(f.read(), filename=os.path.basename(f.name))

    def __init__(self, data, filename=None):
        self._filename = filename

        self._modes = OrderedDict()

        # Actual transforms themselves
        self._transforms = OrderedDict()

        # Key set
        self._key_set = set()

        # Known deadkey glyphs
        self._deadkey_set = set()

        # Deadkey layouts
        self._deadkeys = OrderedDict()

        self._comments = {}

        self._space = OrderedDict()

        tree = lxml.etree.fromstring(data)

        self._internal_name = tree.attrib["locale"]
        self._locale = self._internal_name.split("-")[0]
        self._name = tree.xpath("names/name")[0].attrib["value"]

        self._generate_keyset(tree)
        self._parse_transforms(tree)
        self._parse_keymaps(tree)

    def _generate_keyset(self, tree):
        self._key_set = {decode_u(n.attrib["to"]) for n in tree.xpath("keyMap/map")}
        self._key_set.add(" ")

    def _parse_keymaps(self, tree):
        is_osx = self._internal_name.endswith("osx")

        for keymap in tree.xpath("keyMap"):
            mode = CLDRMode(keymap.attrib.get("modifiers", "default"))
            new_mode = mode.kbdgen[0]
            self._comments[new_mode] = mode.cldr
            o = {}
            for key in keymap.xpath("map"):
                iso_key = key.attrib["iso"]
                # Special case for layout differences.
                if iso_key == "D13":
                    iso_key = "C12"
                elif not is_relevant_cell(iso_key):
                    if iso_key == "A03" and key.attrib["to"] != " ":
                        self._space[new_mode] = process_value(key.attrib["to"])
                    continue

                o[iso_key] = process_value(key.attrib["to"])

                if (
                    o[iso_key] in self._deadkey_set
                    and key.attrib.get("transform", None) != "no"
                ):
                    self._deadkeys.setdefault(new_mode, set()).add(o[iso_key])

            # OS X definitions are in a pseudo-ANSI format that inverts
            # the E00 and B00 keys to prioritise B00 to the E00 position if
            # an ISO language keyboard layout is used on an ANSI keyboard.
            if is_osx and "B00" in o and "E00" in o:
                tmp = o["E00"]
                o["E00"] = o["B00"]
                o["B00"] = tmp

            if "B00" not in o and "E00" in o:
                o["B00"] = o["E00"]

                logger.warning(
                    (
                        "B00 has been duplicated from E00 in '%s'; "
                        + "ANSI keyboard definition?"
                    )
                    % new_mode
                )

            # Force ANSI-style keys into the ISO world.
            if "D13" in o:
                o["C12"] = o["D13"]
                del o["D13"]

            self._modes[new_mode] = OrderedDict(sorted(o.items(), key=key_cmp))

    def _parse_transforms(self, tree):
        o = OrderedDict()

        def o_add(ng, v):
            last = o
            for k in ng[:-1]:
                last.setdefault(k, OrderedDict())
                last = last[k]
            last[ng[-1]] = v

        for transform in tree.xpath("transforms[@type='simple']/transform"):
            ngrams = split_for_set(self._key_set, decode_u(transform.attrib["from"]))
            self._deadkey_set.add(ngrams[0])
            o_add(ngrams, decode_u(transform.attrib["to"]))

        self._transforms = o

    def keys(self, mode):
        return self._modes[mode]

    def _as_yaml_transforms(self, x):
        x.write("\ntransforms:\n")

        def mm(n, it):
            for k, v in it.items():
                if isinstance(v, str):
                    x.write("%s%s: %s\n" % (" " * n, filtered(k), filtered(v)))
                elif isinstance(v, dict):
                    x.write("%s%s:\n" % (" " * n, filtered(k)))
                    mm(n + 2, v)

        mm(2, self._transforms)

    def as_yaml(self):
        x = StringIO()

        x.write(
            "### Generated from %s on %s.\n\n"
            % (
                self._filename or "string data",
                datetime.datetime.utcnow().strftime("%Y-%m-%d at %H:%M"),
            )
        )

        x.write("internalName: %s\n\n" % self._internal_name)
        x.write("displayNames:\n  %s: %s\n\n" % (self._locale, self._name))
        x.write("locale: %s\n\n" % self._locale)

        x.write("modes:\n")
        for mode, o in self._modes.items():
            if mode in self._comments:
                x.write("  # %s\n" % self._comments[mode])
                x.write("  %s: |" % mode)
                cur = None
                for iso_key in keyboard_range():
                    if cur != iso_key[0]:
                        x.write("\n   ")
                        cur = iso_key[0]
                    x.write(" ")
                    x.write(o.get(iso_key, r"\u{0}"))
                x.write("\n")

        if len(self._deadkeys) > 0:
            x.write("\ndeadKeys:\n")
            for mode, keys in self._deadkeys.items():
                output = list(sorted(keys))
                x.write(("  %s: %r\n" % (mode, output)).replace("\\", r"\\"))

        if len(self._transforms) > 0:
            self._as_yaml_transforms(x)

        if len(self._space) > 0:
            x.write("\nspecial:\n  space:\n")
            for mode, v in self._space.items():
                x.write("    %s: %s\n" % (mode, filtered(v)))

        return x.getvalue()


Left = "left"
Right = "right"
Both = "both"

Shift = "shift"
Alt = "alt"
Caps = "caps"
Ctrl = "ctrl"
OSXCommand = "cmd"

TOKENS = {
    "shift": Shift,
    "alt": Alt,
    "opt": Alt,
    "caps": Caps,
    "ctrl": Ctrl,
    "cmd": OSXCommand,
}

ModeToken = namedtuple("CLDRMode", ["name", "direction", "required"])


class CLDRMode:
    def __init__(self, data):
        self._raw = data
        self._kbdgen = None

    def _parse_tokens(self, tokens):
        def pt(tok):
            is_required = not tok.endswith("?")
            if not is_required:
                tok = tok[:-1]

            is_l = tok.endswith("L")
            is_r = tok.endswith("R")

            if is_l or is_r:
                tok = tok[:-1]

            known_token = TOKENS.get(tok, None)
            if known_token is None:
                return ModeToken(known_token, None, None)

            direction = Both
            if is_l:
                direction = Left
            if is_r:
                direction = Right

            return ModeToken(known_token, direction, is_required)

        return tuple(pt(x) for x in tokens)

    def _init_kbdgen(self):
        out = []
        phrases = self._raw.split(" ")

        for ph in phrases:
            # Special case: "default"
            if ph == "default":
                if "iso-default" not in out:
                    out.append("iso-default")
                continue

            tokens = self._parse_tokens(ph.split("+"))
            clean = tuple(tok[0] for tok in tokens if tok.required is True)

            prefix = "iso"
            if OSXCommand in clean:
                prefix = "osx"

            def mm(x):
                if x == "cmd":
                    return 0
                if x == "caps":
                    return 5
                if x == "ctrl":
                    return 10
                if x == "alt":
                    return 20
                if x == "shift":
                    return 40
                return 99

            v = "%s-%s" % (prefix, "+".join(sorted(clean, key=mm)))
            if v not in out:
                out.append(v)

        # Sorted to bring shortest priority to the front
        # eg ('iso-caps+alt', 'iso-alt', 'osx-cmd+alt') from cs is wrong.
        return tuple(sorted(out, key=lambda x: x.count("+")))

    @property
    def kbdgen(self):
        if self._kbdgen is None:
            self._kbdgen = self._init_kbdgen()
        return self._kbdgen

    @property
    def cldr(self):
        return self._raw


def cldr2kbdgen_main():
    import argparse
    import sys

    p = argparse.ArgumentParser(prog="cldr2kbdgen")
    p.add_argument(
        "--osx",
        action="store_true",
        help="Force detection of XML file as an OS X keyboard.",
    )
    p.add_argument("cldr_xml", type=argparse.FileType("rb"), default=sys.stdin)
    p.add_argument("kbdgen_yaml", type=argparse.FileType("w"), default=sys.stdout)
    args = p.parse_args()

    args.kbdgen_yaml.write(CLDRKeyboard.from_file(args.cldr_xml).as_yaml())


def kbdgen2cldr_main():
    import argparse
    import sys
    from . import orderedyaml

    p = argparse.ArgumentParser(prog="kbdgen2cldr")
    # p.add_argument('--osx', action='store_true',
    #               help="Force detection of XML file as an OS X keyboard.")
    p.add_argument("kbdgen_yaml", type=argparse.FileType("r"), default=sys.stdout)
    p.add_argument("cldr_xml", type=argparse.FileType("w"), default=sys.stdin)
    args = p.parse_args()

    parsed = orderedyaml.load(args.kbdgen_yaml)
    args.cldr_xml.write(to_xml(parsed))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("cldr2kbdgen or kbdgen2cldr required as first param.")
        sys.exit(1)
    app = sys.argv.pop(1)

    if app == "cldr2kbdgen":
        cldr2kbdgen_main()
    elif app == "kbdgen2cldr":
        kbdgen2cldr_main()
    else:
        print("cldr2kbdgen or kbdgen2cldr required as first param.")
        sys.exit(1)
