import copy
import logging
import os
import os.path
import re
import sys
from collections import OrderedDict, namedtuple

from . import orderedyaml, log

log.monkey_patch_trace_logging()

def get_logger(path):
    return logging.getLogger(os.path.basename(os.path.splitext(path)[0]))

log.enable_pretty_logging(
        fmt="%(color)s[%(levelname)1.1s %(module)s:%(lineno)d]%(end_color)s" +
            " %(message)s")

logger = logging.getLogger()

VERSION = "0.2a1"

Action = namedtuple("Action", ['row', 'position', 'width'])

ISO_KEYS = ( "E00",
    "E01", "E02", "E03", "E04", "E05", "E06",
    "E07", "E08", "E09", "E10", "E11", "E12",
    "D01", "D02", "D03", "D04", "D05", "D06",
    "D07", "D08", "D09", "D10", "D11", "D12",
    "C01", "C02", "C03", "C04", "C05", "C06", # TODO fix the D13 special case.
    "C07", "C08", "C09", "C10", "C11", "D13", # C12 -> D13
    "B00", "B01", "B02", "B03", "B04", "B05",
    "B06", "B07", "B08", "B09", "B10" )

def parse_layout(data):
    if isinstance(data, dict):
        o = OrderedDict()
        for key in ISO_KEYS:
            o[key] = data.get(key, None)
        return o
    elif isinstance(data, str):
        data = re.sub(r"[\r\n\s]+", " ", data.strip()).split(" ")
        if len(data) != len(ISO_KEYS):
            raise Exception(len(data))
        return OrderedDict(zip(ISO_KEYS, data))


class Project:
    def __init__(self, tree):
        self._tree = tree

    # TODO properties should never throw.
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
        return self._tree['version']

    @property
    def build(self):
        return self._tree['build']

    @property
    def copyright(self):
        return self._tree.get('copyright', '')

    @property
    def organisation(self):
        return self._tree.get('organisation', '')

    def target(self, target):
        return self._tree['targets'].get(target, {}) or {}

    def icon(self, target, size=None):
        val = self.target(target).get('icon', None)
        if val is None:
            return None
        if isinstance(val, str):
            return val
        if size is None:
            # Find largest
            m = -1
            for k in val:
                if k > m:
                    m = k
            return val[m]
        else:
            lrg = -1
            m = sys.maxsize
            for k in val:
                if k > lrg:
                    lrg = k
                if k >= size and k < m:
                    m = k
            if m == sys.maxsize:
                return val[lrg]
            return val[m]

class Keyboard:
    def __init__(self, tree):
        self._tree = tree

    @property
    def internal_name(self):
        return self._tree['internalName']

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
                    node[chunk] = {}
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
                    os.path.join(os.path.dirname(__file__), "global.yaml"))
        return orderedyaml.load(cfg_file)

    def _parse_keyboard_descriptor(self, f):
        tree = orderedyaml.load(f)

        for key in ['locale', 'displayNames', 'internalName', 'modes']:
            if key not in tree:
                raise Exception("%s key missing from file." % key)

        # TODO move this to android and ios generators
        #if 'default' not in tree['modes']:
        #    raise Exception("No default mode supplied in file.")

        if 'modifiers' not in tree or tree.get('modifiers', None) is None:
            tree['modifiers'] = []

        if 'longpress' not in tree or tree.get('longpress', None) is None:
            tree['longpress'] = {}

        for mode in list(tree['modes'].keys()):
            if isinstance(tree['modes'][mode], list):
                raise Exception(("'%s' in '%s' must be defined as a string using" +
                                 " block string format, not a list.") % (mode, f.name))
            try:
                tree['modes'][mode] = parse_layout(tree['modes'][mode])
            except Exception as e:
                raise Exception(("'%s' in file '%s' is the wrong length. " +
                                 "Got %s, expected %s.") % (
                    mode, f.name, str(e), len(ISO_KEYS)))

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

        layouts = {}

        for layout in tree['layouts']:
            with open("%s.yaml" % layout) as f:
                l = self._parse_keyboard_descriptor(f)
                layouts[l.internal_name] = l

        tree['layouts'] = layouts

        return Project(tree)

    def parse(self, data, cfg_pairs=None, cfg_file=None):
        tree = self._parse_global(cfg_file)
        tree.update(orderedyaml.load(data))

        project = self._parse_project(tree)
        if cfg_pairs is not None:
            self._overrides(project._tree, self._parse_cfg_pairs(cfg_pairs))
        return project

