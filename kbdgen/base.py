import copy
import logging
import os
import os.path
import re
import sys
import itertools
import unicodedata
from collections import OrderedDict, namedtuple

from . import orderedyaml, log

class KbdgenException(Exception): pass

log.monkey_patch_trace_logging()

def get_logger(path):
    return logging.getLogger(os.path.basename(os.path.splitext(path)[0]))

log.enable_pretty_logging(
        fmt="%(color)s[%(levelname)1.1s %(module)s:%(lineno)d]%(end_color)s" +
            " %(message)s")

logger = logging.getLogger()

Action = namedtuple("Action", ['row', 'position', 'width'])
ProjectLocaleData = namedtuple("ProjectLocaleData", ['name', 'description'])

ISO_KEYS = ( "E00",
    "E01", "E02", "E03", "E04", "E05", "E06",
    "E07", "E08", "E09", "E10", "E11", "E12",
    "D01", "D02", "D03", "D04", "D05", "D06",
    "D07", "D08", "D09", "D10", "D11", "D12",
    "C01", "C02", "C03", "C04", "C05", "C06", # TODO fix the D13 special case.
    "C07", "C08", "C09", "C10", "C11", "D13", # C12 -> D13
    "B00", "B01", "B02", "B03", "B04", "B05",
    "B06", "B07", "B08", "B09", "B10" )

MODE_LIST_ERROR = """\
'%s' must be defined as a string using block string format, not a list.

For example, if your keyboard.yaml looks like:

```
modes:
  default: [
    q w e r t y u i o p å,
    a s d f g h j k l ö æ,
      z x c v b n m ï
  ]
```

Convert that to:

```
modes:
  default: |
    q w e r t y u i o p å
    a s d f g h j k l ö æ
      z x c v b n m ï
```
"""

def parse_layout(data, length_check=True):
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
    return [re.split(r'\s+', x.strip()) for x in data.strip().split('\n')]

class Project:
    def __init__(self, tree):
        self._tree = tree

    def relpath(self, end):
        return os.path.abspath(os.path.join(self.path, end))

    @property
    def path(self):
        return self._tree['_path']

    @property
    def locales(self):
        return self._tree['locales']

    @property
    def author(self):
        return self._tree['author']

    @property
    def email(self):
        return self._tree['email']

    @property
    def layouts(self):
        return self._tree['layouts']

    @property
    def targets(self):
        return self._tree['targets']

    @property
    def internal_name(self):
        return self._tree['internalName']

    @property
    def app_strings(self):
        return self._tree['appStrings']

    @property
    def version(self):
        return str(self._tree['version'])

    @property
    def build(self):
        return str(self._tree['build'])

    @property
    def copyright(self):
        return self._tree.get('copyright', '')

    @property
    def organisation(self):
        return self._tree.get('organisation', '')

    def locale(self, tag):
        val = self.locales.get(tag, None)
        if val is None:
            return None
        return ProjectLocaleData(val["name"], val["description"])

    def first_locale(self):
        tag = next(iter(self.locales.keys()))
        return self.locale(tag)

    def target(self, target):
        return self._tree['targets'].get(target, {}) or {}

    def icon(self, target, size=None):
        val = self.target(target).get('icon', None)
        if val is None:
            return None
        if isinstance(val, str):
            return self.relpath(val)
        if size is None:
            # Find largest
            m = -1
            for k in val:
                if k > m:
                    m = k
            return self.relpath(val[m])
        else:
            lrg = -1
            m = sys.maxsize
            for k in val:
                if k > lrg:
                    lrg = k
                if k >= size and k < m:
                    m = k
            if m == sys.maxsize:
                return self.relpath(val[lrg])
            return self.relpath(val[m])

class Keyboard:
    def __init__(self, tree):
        self._tree = tree

    @property
    def internal_name(self):
        return self._tree['internalName']

    @property
    def native_display_name(self):
        return self.display_names[self.locale]

    @property
    def display_names(self):
        return self._tree['displayNames']

    @property
    def locale(self):
        return self._tree['locale']

    @property
    def special(self):
        return self._tree.get('special', {})

    @property
    def decimal(self):
        return self._tree.get('decimal', None)

    @property
    def dead_keys(self):
        return self._tree.get('deadKeys', {})

    @property
    def derive(self):
        return self._tree.get('derive', {})

    @property
    def transforms(self):
        return self._tree.get('transforms', {})

    @property
    def modifiers(self):
        return self._tree['modifiers']

    @property
    def modes(self):
        return self._tree['modes']

    @property
    def strings(self):
        return self._tree.get('strings', {})

    @property
    def styles(self):
        return self._tree['styles']

    def target(self, target):
        return self._tree.get('targets', {}).get(target, {}) or {}

    def get_actions(self, style):
        return self.styles[style]['actions']

    def get_action(self, style, key):
        return self.styles[style]['actions'].get(key, None)

    @property
    def longpress(self):
        return self._tree['longpress']

    def get_longpress(self, key):
        return self._tree['longpress'].get(key, None)

    @property
    def supported_targets(self):
        return self._tree.get('supportedTargets', None)

    def supported_target(self, target):
        targets = self.supported_targets
        if targets is None:
            return True
        return target in targets

class Parser:
    def __init__(self):
        pass

    def _overrides(self, project, cfg_pairs):
        def resolve_path(path, v):
            chunks = path.split('.')

            last = chunks.pop()
            node = project

            for chunk in chunks:
                if node.get(chunk, None) is None:
                    node[chunk] = OrderedDict()
                node = node[chunk]
            node[last] = v

        for path, v in cfg_pairs:
            resolve_path(path, v)

    def _parse_cfg_pairs(self, str_list):
        try:
            return [x.split('=', 1) for x in str_list]
        except:
            raise Exception("Error: invalid key-value pair provided.")

    def _parse_global(self, cfg_file=None):
        if cfg_file is None:
            cfg_file = open(
                    os.path.join(os.path.dirname(__file__), "global.yaml"),
                    encoding="utf-8")
        return orderedyaml.load(cfg_file)

    @classmethod
    def _parse_keyboard_descriptor(cls, tree):
        for key in ['locale', 'displayNames', 'internalName', 'modes']:
            if key not in tree:
                raise Exception("%s key missing from file." % key)

        # TODO move this to android and ios generators
        #if 'mobile-default' not in tree['modes']:
        #    raise Exception("No default mode supplied in file.")

        if 'modifiers' not in tree or tree.get('modifiers', None) is None:
            tree['modifiers'] = []

        if 'longpress' not in tree or tree.get('longpress', None) is None:
            tree['longpress'] = OrderedDict()

        for mode in list(tree['modes'].keys()):
            if isinstance(tree['modes'][mode], list):
                raise Exception(MODE_LIST_ERROR % mode)
            try:
                # Soft layouts are special cased.
                if mode in ['mobile-default', 'mobile-shift']:
                    tree['modes'][mode] = parse_touch_layout(tree['modes'][mode])
                else:
                    tree['modes'][mode] = parse_layout(tree['modes'][mode])
            except Exception as e:
                raise Exception(("'%s' is the wrong length. " +
                                 "Got %s, expected %s.") % (
                    mode, str(e), len(ISO_KEYS)))

        for longpress, strings in tree['longpress'].items():
            tree['longpress'][longpress] = re.split(r"\s+", strings.strip())

        for style, styles in tree.get('styles', {}).items():
            for action, info in styles['actions'].items():
                styles['actions'][action] = Action(info[0], info[1], info[2])

        return Keyboard(tree)

    def _parse_project(self, tree):
        for key in ['locales', 'author',
                    'email', 'layouts', 'targets']:
            if key not in tree:
                raise Exception("%s key missing from file." % key)

        tree_path = tree['_path']

        layouts = OrderedDict()

        for layout in tree['layouts']:
            try:
                with open(os.path.join(tree_path, "%s.yaml" % layout), encoding="utf-8") as f:
                    try:
                        data = unicodedata.normalize("NFC", f.read())
                        kbdtree = orderedyaml.loads(data)
                        l = self._parse_keyboard_descriptor(kbdtree)
                        dt = l.derive.get("transforms", False)
                        if dt is not False:
                            derive_transforms(l, True if dt == "all" else False)
                        layouts[l.internal_name] = l
                    except Exception as e:
                        logger.error("There was an error for file '%s.yaml':" % layout)
                        raise e
            except FileNotFoundError as e:
                logger.error("Layout '%s' listed in project, but not found." % layout)
                return None

        tree['layouts'] = layouts

        return Project(tree)

    def parse(self, f, cfg_pairs=None, cfg_file=None):
        tree = self._parse_global(cfg_file)
        # Compose all decomposed unicode codepoints
        data = unicodedata.normalize("NFC", f.read())
        tree.update(orderedyaml.loads(data))

        tree['_path'] = os.path.dirname(os.path.abspath(f.name))

        project = self._parse_project(tree)
        if project is None:
            return None
        if cfg_pairs is not None:
            self._overrides(project._tree, self._parse_cfg_pairs(cfg_pairs))
        return project

def decompose(ch):
    x = unicodedata.normalize("NFKD", ch).replace(" ", "")
    if x == ch:
        try:
            c = "COMBINING %s" % unicodedata.name(ch).replace("MODIFIER LETTER ", "")
            return unicodedata.lookup(c)
        except:
            pass
    return x

def derive_transforms(layout, allow_glyphbombs=False):
    if layout._tree.get("transforms", None) is None:
        layout._tree["transforms"] = {}

    dead_keys = sorted(set(itertools.chain.from_iterable(layout.dead_keys.values())))
    logger.trace("Dead keys: %r" % dead_keys)

    # Get all letter category input chars
    def char_filter(ch):
        if ch is None: return False
        if len(ch) != 1: return False
        return unicodedata.category(ch).startswith("L")
    input_chars = sorted(set(filter(char_filter,
        set(itertools.chain.from_iterable((x.values() for x in layout.modes.values()))))))
    logger.trace("Input chars: %r" % input_chars)

    # Generate inputtable transforms
    for d in dead_keys:
        if layout.transforms.get(d, None) is None:
            layout.transforms[d] = { " ": d }

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
    