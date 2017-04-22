import io
import os
import os.path

from .. import get_logger
from .base import *
from ..cldr import decode_u

logger = get_logger(__file__)

# SC 53 is decimal, 39 is space
WIN_VK_MAP = bind_iso_keys((
    "OEM_5", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "OEM_PLUS", "OEM_4",
    "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "OEM_6", "OEM_1",
    "A", "S", "D", "F", "G", "H", "J", "K", "L", "OEM_3", "OEM_7", "OEM_2",
    "OEM_102", "Z", "X", "C", "V", "B", "N", "M", "OEM_COMMA", "OEM_PERIOD", "OEM_MINUS"
))

WIN_KEYMAP = bind_iso_keys((
    "29", "02", "03", "04", "05", "06", "07", "08", "09", "0a",
    "0b", "0c", "0d", "10", "11", "12", "13", "14", "15", "16",
    "17", "18", "19", "1a", "1b", "1e", "1f", "20", "21", "22",
    "23", "24", "25", "26", "27", "28", "2b", "56", "2c", "2d",
    "2e", "2f", "30", "31", "32", "33", "34", "35"))

class WindowsGenerator(Generator):
    def generate(self, base='.'):
        outputs = OrderedDict()

        for layout in self._project.layouts.values():
            outputs[self._klc_get_name(layout)] = self.generate_klc(layout)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        build_dir = os.path.abspath(base)
        os.makedirs(build_dir, exist_ok=True)

        for name, data in outputs.items():
            with open(os.path.join(build_dir, "%s.klc" % name), 'w') as f:
                f.write(data.replace('\n', '\r\n'))

    def _klc_get_name(self, layout):
        return "kbd" + re.sub(r'[^A-Za-z0-9]', "", layout.internal_name)[:5]

    def _klc_write_headers(self, layout, buf):
        buf.write('KBD\t%s\t"%s"\n\n' % (
            self._klc_get_name(layout),
            layout.display_names[layout.locale]))

        copyright = self._project.copyright
        organisation = self._project.organisation

        buf.write('COPYRIGHT\t"%s"\n\n' % copyright)
        buf.write('COMPANY\t"%s"\n\n' % organisation)
        buf.write('LOCALENAME\t"%s"\n\n' % layout.locale)
        # Use fallback ID in every case (MS-LCID)
        buf.write('LOCALEID\t"00001000"\n\n')
        buf.write('VERSION\t1.0\n\n')
        # 0: default, 1: shift, 2: ctrl, 6: altGr/ctrl+alt, 7: shift+6
        buf.write('SHIFTSTATE\n\n0\n1\n2\n6\n7\n\n')

        buf.write('LAYOUT       ;\n\n')
        buf.write('//SC\tVK_ \t\tCaps\tNormal\tShift\tCtrl\tAltGr\tAltShft\t-> Output\n')
        buf.write('//--\t----\t\t----\t------\t-----\t----\t-----\t-------\t   ------\n\n')

    def _klc_write_keys(self, layout, buf):
        col0 = mode_iter(layout, 'iso-default', required=True)
        col1 = mode_iter(layout, 'iso-shift')
        col2 = mode_iter(layout, 'iso-ctrl')
        col6 = mode_iter(layout, 'iso-alt')
        col7 = mode_iter(layout, 'iso-alt+shift')

        alt_caps = mode_iter(layout, 'iso-alt+caps')

        caps = mode_iter(layout, 'iso-caps')
        caps_shift = mode_iter(layout, 'iso-shift+caps')

        # Cannot be supported. :(
        #alt_caps_shift = mode_iter(layout, 'iso-alt+shift+caps')

        def win_filter(*args, force=False):
            def wf(v):
                """actual filter function"""
                if v is None:
                    return '-1'

                v = str(v)
                if re.match(r"^\d{4}$", v):
                    return v

                v = decode_u(v)

                if v == '\0':
                    return '-1'

                # check for anything outsize A-Za-z range
                if not force and re.match("^[A-Za-z]$", v):
                    return v

                return "%04x" % ord(v)

            return tuple(wf(i) for i in args)

        def win_ligature(v):
            o = tuple('%04x' % ord(c) for c in decode_u(v))
            if len(o) > 4:
                raise Exception('Ligatures cannot be longer than 4 codepoints.')
            return o

        # Hold all the ligatures
        ligatures = []

        for (sc, vk, c0, c1, c2, c6, c7, cap, scap, acap) in zip(
                WIN_KEYMAP.values(), WIN_VK_MAP.values(), col0, col1, col2,
                col6, col7, caps, caps_shift, alt_caps):

            cap_mode = 0
            if cap is not None and c0 != cap and c1 != cap:
                cap_mode = "SGCap"
            elif cap is None:
                cap_mode += 1 if c0 != c1 else 0
                cap_mode += 4 if c6 != c7 else 0
            else:
                cap_mode += 1 if cap == c1 else 0
                cap_mode += 4 if acap == c7 else 0
            cap_mode = str(cap_mode)

            if len(vk) < 8:
                vk += "\t"
            buf.write("%s\t%s\t%s" % (sc, vk, cap_mode))

            # n is the col number for ligatures.
            for n, mode, key in ((0, 'iso-default', c0),
                                 (1, 'iso-shift', c1),
                                 (2, 'iso-ctrl', c2),
                                 (3, 'iso-alt', c6),
                                 (4, 'iso-alt+shift', c7)):

                filtered = decode_u(key or '')
                if key is not None and len(filtered) > 1:
                    buf.write("\t%%")
                    ligatures.append((filtered, (vk, str(n)) + win_ligature(key)))
                else:
                    buf.write("\t%s" % win_filter(key))
                    if key in layout.dead_keys.get(mode, []):
                        buf.write("@")

            buf.write("\t// %s %s %s %s %s\n" % (c0, c1, c2, c6, c7))

            if cap_mode == "SGCap":
                if cap is not None and len(win_ligature(cap)) > 1:
                    cap = None
                    logger.warning("Caps key '%s' too long for Caps Mode.")

                if scap is not None and len(win_ligature(scap)) > 1:
                    scap = None
                    logger.warning("Caps+Shift key '%s' too long for Caps Mode.")

                buf.write("-1\t-1\t\t0\t%s\t%s\t\t\t\t// %s %s\n" % (
                    win_filter(cap, scap) + (cap, scap)))

        # Space, such special case oh my.
        buf.write("39\tSPACE\t\t0\t")
        if 'space' not in layout.special:
            buf.write("0020\t0020\t0020\t-1\t-1\n")
        else:
            o = layout.special['space']
            buf.write("%s\t%s\t%s\t%s\t%s\n" % win_filter(
                    o.get('iso-default', '0020'),
                    o.get('iso-shift', '0020'),
                    o.get('iso-ctrl', '0020'),
                    o.get('iso-alt', None),
                    o.get('iso-alt+shift', None)
                ))

        # Decimal key on keypad.
        decimal = layout.decimal or "."
        buf.write("53\tDECIMAL\t\t0\t%s\t%s\t-1\t-1\t-1\n\n" % win_filter(
            decimal, decimal))

        # Ligatures!
        if len(ligatures) > 0:
            buf.write("LIGATURE\n\n")
            buf.write("//VK_\tMod#\tChr0\tChr1\tChr2\tChr3\n")
            buf.write("//----\t----\t----\t----\t----\t----\n\n")
            for original, col in ligatures:
                more_tabs = len(col)-7
                buf.write("%s\t\t%s%s\t// %s\n" % (col[0],
                    "\t".join(col[1:]),
                    '\t' * more_tabs,
                    original))
            buf.write('\n')

        # Deadkeys!
        for basekey, o in layout.transforms.items():
            if len(basekey) != 1:
                logger.warning(("Base key '%s' invalid for Windows " +
                       "deadkeys; skipping.") % basekey)
                continue

            buf.write("DEADKEY\t%s\n\n" % win_filter(basekey))
            for key, output in o.items():
                if key == ' ':
                    continue

                key = str(key)
                output = str(output)

                if len(key) != 1 or len(output) != 1:
                    logger.warning(("%s%s -> %s is invalid for Windows " +
                           "deadkeys; skipping.") % (basekey, key, output))
                    continue
                buf.write("%s\t%s\t// %s -> %s\n" % (
                    win_filter(key, output, force=True) + (key, output)))

            # Create fallback key from space, or the basekey.
            output = o.get(' ', basekey)
            buf.write("0020\t%s\t//   -> %s\n\n" % (
                win_filter(output)[0], output))


    def generate_klc(self, layout):
        buf = io.StringIO()

        self._klc_write_headers(layout, buf)
        self._klc_write_keys(layout, buf)

        buf.write("ENDKBD\n")

        return buf.getvalue()

