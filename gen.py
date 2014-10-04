from lxml import etree
from lxml.etree import Element, SubElement

class Generator:
    def __init__(self, tree):
        self._tree = tree

class AndroidGenerator(Generator):
    NS = "http://schemas.android.com/apk/res/com.android.inputmethod.latin"

    def _element(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            o["{%s}%s" % (self.NS, k)] = v
        return Element(*args, **o)

    def _subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            o["{%s}%s" % (self.NS, k)] = v
        return SubElement(*args, **o)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def generate(self):
        name = self._tree.name

        styles = [
            ('phone', 'xml'),
            ('tablet', 'xml-sw600dp')
        ]

        files = [
            ('xml/keyboard_layout_set_%s.xml' % name, self.kbd_layout_set()),
            ('xml/kbd_%s.xml' % name, self.keyboard())
        ]

        for style, prefix in styles:
            self.gen_key_width(style)

            files.append(("%s/rows_%s.xml" % (prefix, name), self.rows(style)))

            for row in self.rowkeys(style):
                row = ("%s/%s" % (prefix, row[0]), row[1])
                files.append(row)

        return files

    def kbd_layout_set(self):
        out = Element("KeyboardLayoutSet", nsmap={"latin": self.NS})

        self._subelement(out, "Element", elementName="alphabet",
            elementKeyboard="@xml/kbd_%s" % self._tree.name,
            enableProximityCharsCorrection="true")

        for name, kbd in (
            ("symbols", "@xml/kbd_symbols"),
            ("symbolsShifted", "@xml/kbd_symbols_shift"),
            ("phone", "@xml/kbd_phone"),
            ("phoneSymbols", "@xml/kbd_phone_symbols"),
            ("number", "@xml/kbd_number")
        ):
            self._subelement(out, "Element", elementName=name, elementKeyboard=kbd)

        return self._tostring(out)

    def row_has_special_keys(self, n, style):
        for key, action in self._tree.get_actions(style).items():
            if action.row == n:
                return True
        return False

    def rows(self, style):
        out = Element("merge", nsmap={"latin": self.NS})

        self._subelement(out, "include", keyboardLayout="@xml/key_styles_common")

        for n, values in enumerate(self._tree.modes['default']):
            n += 1

            row = self._subelement(out, "Row")
            include = self._subelement(row, "include", keyboardLayout="@xml/rowkeys_%s%s" % (
                self._tree.name, n))

            if not self.row_has_special_keys(n, style):
                self._attrib(include, keyWidth='%.2f%%p' % (100 / len(values)))
            else:
                self._attrib(include, keyWidth='%.2f%%p' % self.key_width)

        # All the fun buttons!
        self._subelement(out, "include", keyboardLayout="@xml/row_qwerty4")

        return self._tostring(out)

    def gen_key_width(self, style):
        m = 0
        for row in self._tree.modes['default']:
            r = len(row)
            if r > m:
               m = r

        vals = {
            "phone": 95,
            "tablet": 90
        }

        self.key_width = (vals[style] / m)

    def keyboard(self, **kwargs):
        out = Element("Keyboard", nsmap={"latin": self.NS})

        self._attrib(out, **kwargs)

        self._subelement(out, "include", keyboardLayout="@xml/rows_%s" % self._tree.name)

        return self._tostring(out)

    def rowkeys(self, style):
        for n, values in enumerate(self._tree.modes['default']):
            n += 1
            rows = self.add_rows(n, values, style)
            yield ('rowkeys_%s%s.xml' % (self._tree.name, n), self._tostring(rows))

    def _attrib(self, node, **kwargs):
        for k, v in kwargs.items():
            node.attrib["{%s}%s" % (self.NS, k)] = v

    def add_button_type(self, key, action, row, tree, is_start):
        node = self._element("Key")
        width = action.width

        if width == "fill":
            if is_start:
                width = "%.2f%%" % ((100 - (self.key_width * len(row))) / 2)
            else:
                width = "fillRight"
        elif width.endswith("%"):
            width += 'p'

        if key == "backspace":
            self._attrib(node, keyStyle="deleteKeyStyle")
        if key == "enter":
            self._attrib(node, keyStyle="enterKeyStyle")
        if key == "shift":
            self._attrib(node, keyStyle="shiftKeyStyle")
        self._attrib(node, keyWidth=width)

        tree.append(node)

    def add_special_buttons(self, n, style, row, tree, is_start):
        side = "left" if is_start else "right"

        for key, action in self._tree.get_actions(style).items():
            if action.row == n and action.position in [side, 'both']:
                self.add_button_type(key, action, row, tree, is_start)

    def add_rows(self, n, values, style):
        out = Element("merge", nsmap={"latin": self.NS})
        i = 1

        self.add_special_buttons(n, style, values, out, True)

        for key in values:
            more_keys = self._tree.get_longpress(key)

            node = self._subelement(out, "Key", keyLabel=key)
            if n == 1:
                if i > 0 and i <= 10:
                    if i == 10:
                        i = 0
                    self._attrib(node, keyHintLabel=str(i), additionalMoreKeys=str(i))
                    if i > 0:
                        i += 1
                elif more_keys is not None:
                    self._attrib(node, keyHintLabel=more_keys[0])

            elif more_keys is not None:
                self._attrib(node, moreKeys=','.join(more_keys))
                #self._attrib(node, 'keyHintLabel', more_keys[0])

        self.add_special_buttons(n, style, values, out, False)

        return out
