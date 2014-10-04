import yaml
import gen

from collections import namedtuple

Action = namedtuple("Action", ['row', 'position', 'width'])

class Keyboard:
    def __init__(self, tree):
        self._tree = tree

    @property
    def name(self):
        return self._tree['name']

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

    def parse(self, data):
        tree = yaml.load(data)

        for key in ['name', 'modes']:
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

def xml_encode_numeric_entity(ch):
    return "&#%s;" % hex(ord(ch))[1:]

if __name__ == "__main__":
    import sys, os, os.path
    kbdtree = Parser().parse(open(sys.argv[1]))
    out = gen.AndroidGenerator(kbdtree).generate()
    for k, v in out:
        print("Saving %s..." % k)

        os.makedirs(os.path.dirname(k), exist_ok=True)
        with open(k, 'w') as f:
            f.write(v)
