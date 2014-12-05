import yaml
import gen

import argparse
import sys
import os

from collections import namedtuple

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

    def target(self, target):
        return self._tree['targets'].get(target, {}) or {}


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

    def _parse_global(self):
        with open(os.path.join(os.path.dirname(__file__), "global.yaml")) as f:
            return yaml.load(f)

    def _parse_layout(self, data):
        tree = yaml.load(data)

        for key in ['locale', 'displayNames', 'internalName', 'modes']:
            if key not in tree:
                raise Exception("%s key missing from file." % key)

        if 'default' not in tree['modes']:
            raise Exception("No default mode supplied in file.")

        if 'modifiers' not in tree:
            tree['modifiers'] = []

        if 'longpress' not in tree:
            tree['longpress'] = []

        for mode, strings in tree['modes'].items():
            tree['modes'][mode] = [x.strip().split(' ') for x in strings]

        for longpress, strings in tree['longpress'].items():
            tree['longpress'][longpress] = strings.strip().split(' ')

        for style, styles in tree['styles'].items():
            for action, info in styles['actions'].items():
                styles['actions'][action] = Action(info[0], info[1], info[2])

        return Keyboard(tree)

    def _parse_project(self, data):
        tree = self._parse_global()
        tree.update(yaml.load(data))

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

    def parse(self, data, cfg_pairs=None):
        project = self._parse_project(data)
        if cfg_pairs is not None:
            self._overrides(project._tree, parse_cfg_pairs(cfg_pairs))
        return project

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-D', '--dry-run', action="store_true",
                   help="Don't build, just do sanity checks.")
    p.add_argument('-K', '--key', nargs="*", dest='cfg_pairs',
                   help="Key-value overrides (eg -K target.thing.foo=42)")
    p.add_argument('-R', '--release', action='store_true',
                   help="Compile in 'release' mode.")
    p.add_argument('-b', '--branch', default='stable',
                   help='Git branch (default: stable)')
    p.add_argument('-r', '--repo', help='Git repo.')
    p.add_argument('-t', '--target', required=True,
                   help="Target output.")
    p.add_argument('project', type=argparse.FileType('r'),
                   default=sys.stdin)
    return p.parse_args()

def parse_cfg_pairs(str_list):
    try:
        return [x.split('=', 1) for x in str_list]
    except:
        raise Exception("Error: invalid key-value pair provided.")

if __name__ == "__main__":
    args = parse_args()

    try:
        project = Parser().parse(args.project,
                                 args.cfg_pairs)
    except Exception as e:
        print(e)
        sys.exit(1)

    if args.target not in ["android", "ios"]:
        print("Error: only 'android' and 'ios' are supported currently.")
        sys.exit(1)

    if args.target == "android":
        x = gen.AndroidGenerator(project, dict(args._get_kwargs()))
    elif args.target == "ios":
        x = gen.AppleiOSGenerator(project, dict(args._get_kwargs()))

    try:
        x.generate()
    except gen.MissingApplicationException as e:
        print(e)
