import yaml
import gen

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
    def target(self, target):
        return self._tree['targets'].get(target, {})


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
        tree = yaml.load(data)

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

        print (tree)
        return Project(tree)

    def parse(self, data):
        return self._parse_project(data)

def xml_encode_numeric_entity(ch):
    return "&#%s;" % hex(ord(ch))[1:]

if __name__ == "__main__":
    import sys, os, os.path
    kbdtree = Parser().parse(open(sys.argv[1]))
    out = gen.AndroidGenerator(kbdtree).generate()
