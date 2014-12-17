import sys
import os
import re
from collections import namedtuple

import yaml

from . import gen

Action = namedtuple("Action", ['row', 'position', 'width'])

class Project:
    def __init__(self, tree):
        self._tree = tree

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
        return yaml.load(cfg_file)

    def _parse_layout(self, data):
        tree = yaml.load(data)

        for key in ['locale', 'displayNames', 'internalName', 'modes']:
            if key not in tree:
                raise Exception("%s key missing from file." % key)

        if 'default' not in tree['modes']:
            raise Exception("No default mode supplied in file.")

        if 'modifiers' not in tree or tree.get('modifiers', None) is None:
            tree['modifiers'] = []

        if 'longpress' not in tree or tree.get('longpress', None) is None:
            tree['longpress'] = {}

        for mode, strings in tree['modes'].items():
            tree['modes'][mode] = [re.split(r"\s+", x.strip()) for x in strings]

        for longpress, strings in tree['longpress'].items():
            tree['longpress'][longpress] = re.split(r"\s+", strings.strip())

        for style, styles in tree['styles'].items():
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
        tree.update(yaml.load(data))

        project = self._parse_project(tree)
        if cfg_pairs is not None:
            self._overrides(project._tree, self._parse_cfg_pairs(cfg_pairs))
        return project


