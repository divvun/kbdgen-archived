import os
import os.path
import shutil
import yaml
import re
import itertools
import unicodedata
import logging

from collections import OrderedDict
from kbdgen import orderedyaml
from kbdgen.models import *

logger = logging.getLogger()

ISO_KEYS = (
    "E00",
    "E01",
    "E02",
    "E03",
    "E04",
    "E05",
    "E06",
    "E07",
    "E08",
    "E09",
    "E10",
    "E11",
    "E12",
    "D01",
    "D02",
    "D03",
    "D04",
    "D05",
    "D06",
    "D07",
    "D08",
    "D09",
    "D10",
    "D11",
    "D12",
    "C01",
    "C02",
    "C03",
    "C04",
    "C05",
    "C06",  # TODO fix the D13 special case.
    "C07",
    "C08",
    "C09",
    "C10",
    "C11",
    "D13",  # C12 -> D13
    "B00",
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B09",
    "B10",
)

MOBILE_MODES = frozenset((
    "default",
    "shift"
))

DESKTOP_MODES = frozenset((
    "default",
    "shift",
    "caps",
    "caps+shift",
    "alt",
    "alt+shift",
    "caps+alt",
    "ctrl"
))

MAC_MODES = frozenset((
    "cmd",
    "cmd+shift",
    "cmd+alt",
    "cmd+alt+shift"
))

def parse_desktop_layout(data, length_check=True):
    if isinstance(data, dict):
        o = OrderedDict()
        for key in ISO_KEYS:
            v = data.get(key, None)
            o[key] = str(v) if v is not None else None
        return o
    elif isinstance(data, str):
        data = re.sub(r"[\r\n\s]+", " ", data.strip()).split(" ")
        if length_check and len(data) != len(ISO_KEYS):
            raise Exception(len(data))
        o = OrderedDict(zip(ISO_KEYS, data))
        # Remove nulls
        for k in ISO_KEYS:
            if o[k] == r"\u{0}":
                o[k] = None
        return o


def parse_touch_layout(data):
    return [re.split(r"\s+", x.strip()) for x in data.strip().split("\n")]

class MobileLayoutMode(dict):
    @staticmethod
    def decode(obj):
        o = {}
        for k in MOBILE_MODES:
            if k in obj:
                o[k] = parse_touch_layout(obj[k])
        return MobileLayoutMode(**o)

class DesktopLayoutMode(dict):
    @staticmethod
    def decode(obj, modes=DESKTOP_MODES):
        o = {}
        for k in modes:
            if k in obj:
                o[k] = parse_desktop_layout(obj[k])
        return DesktopLayoutMode(**o)
        

def assert_valid_keysets(cand_keys, parent_keys, base_keys, cand, parent):
    overlap = cand_keys & parent_keys
    diff = base_keys - parent_keys - cand_keys
    if len(overlap) > 0:
        raise Exception("Conflicting modes found for `%s` and `%s`: %r" % (cand, parent, overlap))
    # if len(diff) > 0:
    #     raise Exception("Missing modes in `%s` relative to `%s`: %s" % (cand, parent, ", ".join(diff)))


def parse_modes(tree):
    # We support these top levels:
    # mobile, ios, android, desktop, win, mac
    #
    # If ios and/or android exist, if any of their children exist, the same must not exist in mobile
    # If win and/or mac exist, if any of their children exist, the same must not exist in desktop
    modes = OrderedDict()

    if "mobile" in tree:
        mobile_layers = MobileLayoutMode.decode(tree["mobile"])
        mobile_keyset = frozenset(mobile_layers.keys())
        modes["mobile"] = mobile_layers
    else:
        mobile_keyset = frozenset()

    if "desktop" in tree:
        desktop_layers = DesktopLayoutMode.decode(tree["desktop"])
        desktop_keyset = frozenset(desktop_layers.keys())
        modes["desktop"] = desktop_layers
    else:
        desktop_keyset = frozenset()
    
    if "android" in tree:
        android_layers = MobileLayoutMode.decode(tree["android"])
        android_keyset = frozenset(android_layers.keys())
        assert_valid_keysets(android_keyset, mobile_keyset, MOBILE_MODES, "android", "mobile")
        modes["android"] = android_layers

    if "ios" in tree:
        ios_layers = MobileLayoutMode.decode(tree["ios"])
        ios_keyset = frozenset(ios_layers.keys())
        assert_valid_keysets(ios_keyset, mobile_keyset, MOBILE_MODES, "ios", "mobile")
        modes["ios"] = ios_layers

    if "win" in tree:
        win_layers = DesktopLayoutMode.decode(tree["win"])
        win_keyset = frozenset(win_layers.keys())
        assert_valid_keysets(win_keyset, desktop_keyset, DESKTOP_MODES, "win", "desktop")
        modes["win"] = win_layers

    # TODO: deduplicate this mess
    if "chrome" in tree:
        chrome_layers = DesktopLayoutMode.decode(tree["chrome"])
        chrome_keyset = frozenset(chrome_layers.keys())
        assert_valid_keysets(chrome_keyset, desktop_keyset, DESKTOP_MODES, "chrome", "desktop")
        modes["chrome"] = chrome_layers

    if "mac" in tree:
        mac_layers = DesktopLayoutMode.decode(tree["mac"], DESKTOP_MODES | MAC_MODES)
        mac_keyset = frozenset(mac_layers.keys())
        assert_valid_keysets(mac_keyset, desktop_keyset, DESKTOP_MODES | MAC_MODES, "mac", "desktop")
        modes["mac"] = mac_layers

    return modes


def try_decode_target(cls, target, obj):
    try:
        return cls.decode(obj)
    except KeyError as e:
        raise Exception("Error decoding target '%s', missing key: %s" % (
            target, str(e)))


def decode_target(name, obj):
    if name.startswith("win"):
        return try_decode_target(TargetWindows, "win", obj)
    if name.startswith("mac"):
        return try_decode_target(TargetMacOS, "mac", obj)
    if name.startswith("ios"):
        return try_decode_target(TargetIOS, "ios", obj)
    if name.startswith("android"):
        return try_decode_target(TargetAndroid, "android", obj)
    return obj


def decompose(ch):
    x = unicodedata.normalize("NFKD", ch).replace(" ", "")
    if x == ch:
        try:
            c = "COMBINING %s" % unicodedata.name(ch).replace("MODIFIER LETTER ", "")
            return unicodedata.lookup(c)
        except Exception:
            pass
    return x


def derive_transforms(layout, allow_glyphbombs=False):
    if layout.transforms is None:
        layout.transforms = {}

    dead_keys = sorted(set(itertools.chain.from_iterable(layout.dead_keys.values())))
    logger.trace("Dead keys: %r" % dead_keys)

    # Get all letter category input chars
    def char_filter(ch):
        if ch is None:
            return False
        if len(ch) != 1:
            return False
        return unicodedata.category(ch).startswith("L")

    input_chars = sorted(
        set(
            filter(
                char_filter,
                set(
                    itertools.chain.from_iterable(
                        (x.values() for x in layout.modes.values())
                    )
                ),
            )
        )
    )
    logger.trace("Input chars: %r" % input_chars)

    # Generate inputtable transforms
    for d in dead_keys:
        if layout.transforms.get(d, None) is None:
            layout.transforms[d] = {" ": d}

        dc = decompose(d)

        for ch in input_chars:
            composed = "%s%s" % (ch, dc)
            normalised = unicodedata.normalize("NFKC", composed)

            # Check if when composed the codepoint is not the same as decomposed
            if not allow_glyphbombs and composed == normalised:
                logger.trace("Skipping %s%s" % (d, ch))
                continue

            logger.trace("Adding transform: %s%s -> %s" % (d, ch, normalised))
            layout.transforms[d][ch] = normalised

def decode_layout(tree):
    layout = Layout.decode(tree)
    layout.modes = parse_modes(layout.modes)

    if layout.longpress is None:
        layout.longpress = OrderedDict()

    lp = OrderedDict()
    for longpress, strings in layout.longpress.items():
        lp[longpress] = re.split(r"\s+", strings.strip())
    layout.longpress = lp

    transforms_derive = layout.derive is not None and layout.derive.get("transforms", False)
    if transforms_derive is True:
        derive_transforms(layout, False) # TODO: allow strange, non-standard interactions

    return layout

def normalized_yaml_load(f):
    data = unicodedata.normalize("NFC", f.read())
    return orderedyaml.loads(data)

class ProjectBundle:
    """A project bundle consists of a project.yaml file, a targets/ directory and a layouts/ directory."""
    
    @staticmethod
    def load(bundle_path):
        logger.trace("Loading %r" % bundle_path)
        project_yaml_path = os.path.join(bundle_path, "project.yaml")
        layouts_path = os.path.join(bundle_path, "layouts")
        targets_path = os.path.join(bundle_path, "targets")

        with open(project_yaml_path, encoding="utf-8") as f:
            logger.trace("Loading project: %r" % project_yaml_path)
            project = Project.decode(normalized_yaml_load(f))

        logger.trace("Loading layouts")
        layouts = dict([(
            os.path.splitext(x)[0],
            decode_layout(normalized_yaml_load(open(os.path.join(layouts_path, x), encoding="utf-8")))
        ) for x in os.listdir(layouts_path)])
        
        logger.trace("Loading targets")
        targets = dict([(
            os.path.splitext(x)[0],
            decode_target(x, normalized_yaml_load(open(os.path.join(targets_path, x),  encoding="utf-8")))
        ) for x in os.listdir(targets_path)])

        return ProjectBundle(bundle_path, project, layouts, targets)

    def __init__(self, path, project, layouts, targets):
        self._path = os.path.abspath(path)
        self._project = project
        self._layouts = layouts
        self._targets = targets

    def relpath(self, end):
        return os.path.abspath(os.path.join(self.path, end))

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self._path[:-1]))[0]

    @property
    def path(self):
        return self._path

    @property
    def project(self):
        return self._project
    
    @property
    def layouts(self):
        return self._layouts
    
    @property
    def targets(self):
        return self._targets

    def resources(self, target):
        return os.path.join(self.relpath("resources"), target)