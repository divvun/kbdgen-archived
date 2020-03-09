import copy
import os.path
import itertools

import xml.etree.ElementTree as etree
from xml.etree.ElementTree import Element, SubElement
from textwrap import dedent
from collections import OrderedDict

from ..base import get_logger
from .base import Generator, mode_dict, ISO_KEYS, get_bin_resource
from ..cldr import decode_u

logger = get_logger(__name__)

NS = "{http://www.w3.org/2000/svg}"

class SVGGenerator(Generator):
    @property
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "desktop" in v.modes or "mac" in v.modes or "win" in v.modes or "chrome" in v.modes:
                o[k] = v
        return o

    def generate(self, base="."):
        with get_bin_resource("keyboard-iso.svg", text=True) as f:
            tree = etree.parse(f)
        root = tree.getroot()

        files = []
        
        for name, layout in self.supported_layouts.items():
            files.append(
                (
                    "%s.svg" % name,
                    layout.display_names.get(name, name),
                    self.generate_svg(name, layout, copy.deepcopy(root)),
                )
            )

        out_dir = os.path.abspath(base)
        os.makedirs(out_dir, exist_ok=True)

        for fn, _, data in files:
            with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
                f.write(data)

        # Get English name, or fallback to internal name
        kbd_name = self._bundle.name

        with open(os.path.join(out_dir, "layout.html"), "w", encoding="utf-8") as f:
            f.write(
                dedent(
                    """\
            <!doctype html>
            <html>
            <head>
                <meta charset='utf-8'>
                <title>Layout(s) for the %s</title>
            </head>
            <body>
                <p><strong>Legend:</strong></p>
                <table>
                  <thead>
                    <tr>
                      <th>Mode</th>
                      <th>Standard</th>
                      <th>Dead</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                        <th>Default</th>
                        <td>black</td>
                        <td>green</td>
                    </tr>
                    <tr>
                        <th>AltGr/Option</th>
                        <td>red</td>
                        <td>orange</td>
                    </tr>
                    <tr>
                        <th>Caps Lock (Mode Switch)</th>
                        <td>blue</td>
                        <td>pink</td>
                    </tr>
                    <tr>
                        <th>Caps Lock + AltGr/Option:</th>
                        <td>purple</td>
                        <td>green</td>
                    </tr>
                  </tbody>
                </table>
            """
                )
                % kbd_name
            )

            for fn, name, _ in sorted(files):
                f.write("    <h2>%s</h2>\n" % name)
                f.write('    <object type="image/svg+xml"')
                f.write('data="%s" width="960" height="320"></object><br>\n' % fn)
                # f.write('    <iframe style="border:none" ')
                # f.write('src="%s" width="960" height="320"></iframe><br>\n' % fn)

            f.write(
                dedent(
                    """\
                <script>
                    "use strict";

                    var i, ii, nodes, node;

                    nodes = document.querySelectorAll(".key-dead");
                    for (i = 0, ii = nodes.length; i < ii; ++i) {
                        nodes[i].addEventListener('click', function(e) {
                            console.log(this);
                        }, false);
                    }
                </script>
            </body>
            </html>
            """
                )
            )

    def _make_key_group(self, primary, secondary, cls=None):
        if cls is None:
            cls = ""

        trans = {
            "\u00A0": "NBSP",
            "\u200B": "ZWSP",
            "\u200C": "ZWNJ",
            "\u200D": "ZWJ",
            "\u2060": "WJ",
        }

        primary = trans.get(primary, primary)
        secondary = trans.get(secondary, secondary)

        g = Element(NS + "g", **{"class": ("key-group %s" % cls).strip()})
        p = SubElement(
            g,
            NS + "text",
            **{"dy": "1em", "y": "32", "x": "32", "class": "key-text-primary"}
        )
        try:
            p.text = primary
        except Exception as e:
            logger.warning("For char 0x%04x: %s" % (ord(primary), e))
        s = SubElement(
            g,
            NS + "text",
            **{"dy": "-.4em", "y": "32", "x": "32", "class": "key-text-secondary"}
        )
        try:
            s.text = secondary
        except Exception as e:
            logger.warning("For char 0x%04x: %s" % (ord(secondary), e))
        return (g, p, s)

    def generate_svg(self, locale, layout, root):
        logger.info("Generating SVG for '%s'..." % locale)
        default = mode_dict(locale, layout, "default", "win", required=True)
        shift = mode_dict(locale, layout, "shift", "win")

        caps = mode_dict(locale, layout, "caps", "win")
        caps_shift = mode_dict(locale, layout, "caps+shift", "win")

        alts = mode_dict(locale, layout, "alt", "win")
        alts_shift = mode_dict(locale, layout, "alt+shift", "win")

        alt_caps = mode_dict(locale, layout, "caps+alt", "win")
        alt_caps_shift = mode_dict(locale, layout, "caps+alt+shift", "win")

        for k in itertools.chain(ISO_KEYS, ("A03",)):
            logger.trace("%s" % k)
            groups = []

            dk = decode_u(default.get(k, "")) or None
            dk_dead = dk is not None and default[k] in layout.dead_keys.get(
                "default", {}
            )

            sk = decode_u(shift.get(k, "")) or None
            sk_dead = sk is not None and shift[k] in layout.dead_keys.get("shift", {})

            ack = decode_u(alt_caps.get(k, "")) or None
            ack_dead = ack is not None and alt_caps[k] in layout.dead_keys.get(
                "caps+alt", {}
            )

            acsk = decode_u(alt_caps_shift.get(k, "")) or None
            acsk_dead = acsk is not None and alt_caps_shift[k] in layout.dead_keys.get(
                "caps+alt+shift", {}
            )

            ak = decode_u(alts.get(k, "")) or None
            ak_dead = ak is not None and alts[k] in layout.dead_keys.get("alt", {})

            ask = decode_u(alts_shift.get(k, "")) or None
            ask_dead = ask is not None and alts_shift[k] in layout.dead_keys.get(
                "alt+shift", {}
            )

            ck = decode_u(caps.get(k, "")) or None
            ck_dead = ck is not None and caps[k] in layout.dead_keys.get("caps", {})

            csk = decode_u(caps_shift.get(k, "")) or None
            csk_dead = csk is not None and caps_shift[k] in layout.dead_keys.get(
                "caps+shift", {}
            )

            for g in root.iter():
                if not g.tag.endswith("g"):
                    continue
                if k.lower() in g.attrib.get("class", ""):
                    break
            else:
                raise Exception("No <g> found for %s" % k)
            logger.trace("Element: %r %r %r" % (g, g.tag, g.attrib))

            if True:  # has_group1:
                group1, p1, s1 = self._make_key_group(dk, sk, "key-group-1")
                if dk_dead:
                    p1.attrib["class"] += " key-dead"
                if sk_dead:
                    s1.attrib["class"] += " key-dead"
                g.append(group1)

                groups.append(group1)

            if True:  # has_group2:
                group2, p2, s2 = self._make_key_group(ak, ask, "key-group-2")
                if ak_dead:
                    p2.attrib["class"] += " key-dead"
                if ask_dead:
                    s2.attrib["class"] += " key-dead"
                g.append(group2)

                groups.append(group2)

            if True:  # has_group3:
                group3, p3, s3 = self._make_key_group(ck, csk, "key-group-3")
                if ck_dead:
                    p3.attrib["class"] += " key-dead"
                if csk_dead:
                    s3.attrib["class"] += " key-dead"
                g.append(group3)

                groups.append(group3)

            if True:  # has_group4:
                group4, p4, s4 = self._make_key_group(ack, acsk, "key-group-4")
                if ack_dead:
                    p4.attrib["class"] += " key-dead"
                if acsk_dead:
                    s4.attrib["class"] += " key-dead"
                g.append(group4)

                groups.append(group4)

            if len(groups) == 2:
                groups[0].attrib["transform"] = "translate(-14, 0)"
                groups[1].attrib["transform"] = "translate(14, 0)"
            if len(groups) == 3:
                groups[0].attrib["transform"] = "translate(-20, 0)"
                groups[2].attrib["transform"] = "translate(20, 0)"
            if len(groups) == 4:
                groups[0].attrib["transform"] = "translate(-24, 0)"
                groups[1].attrib["transform"] = "translate(-8, 0)"
                groups[2].attrib["transform"] = "translate(8, 0)"
                groups[3].attrib["transform"] = "translate(24, 0)"

        return "<?xml version='1.0' encoding='utf8'?>\n%s" % etree.tostring(
            root, encoding="utf-8"
        ).decode("utf-8")
