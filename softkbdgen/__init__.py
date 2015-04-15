import sys
import os
import re
import copy
from collections import namedtuple

from . import orderedyaml

Action = namedtuple("Action", ['row', 'position', 'width'])

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

    def _parse_layout(self, data):
        tree = orderedyaml.load(data)

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

        strdicts = []
        keycache = {}
        layermap = {
            'iso-layer3': 'iso-default'
        }

        for mode, strings in tree['modes'].items():
            if isinstance(strings, list):
                print("DEPRECATED: %s is a list. Please use a string block (eg default: |)" % mode)
            elif isinstance(strings, str):
                strings = strings.strip().split('\n')
            if isinstance(strings, dict):
                # TODO abuse the strdicts loop, for now just add to modes.
                #strdicts.append((mode, strings))
                pass
            else:
                # TODO wtf can this even be reached??
                tree['modes'][mode] = [re.split(r"\s+", x.strip()) for x in strings]
                keycache[mode] = {}
                for y, row in enumerate(tree['modes'][mode]):
                    for x, key in enumerate(row):
                        keycache[mode][key] = (y, x)

        for mode, keys in strdicts:
            if mode not in layermap:
                print("ERROR mode not in layermap TODO FINISH")
                continue

            basemode = layermap[mode]
            tree['modes'][mode] = copy.deepcopy(tree['modes'][basemode])
            for k, v in keys.items():
                k = str(k)
                y, x = keycache[basemode][k]
                tree['modes'][mode][y][x] = v

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
                l = self._parse_layout(f)
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


