import io

from .. import get_logger
from .base import *
from ..cldr import CP_REGEX

logger = get_logger(__file__)

keysym_to_str = {}
#str_to_keysym = {}

with open(filepath(__file__, 'bin', 'keysym.tsv')) as f:
    line = f.readline()
    while line:
        if line.startswith("*"):
            break
        line = f.readline()

    line = f.readline()
    while line:
        string, keysymstr = line.strip().split('\t')
        keysym = int(keysymstr, 16)

        #str_to_keysym[string] = keysym
        keysym_to_str[keysym] = string
        line = f.readline()

class XKBGenerator(Generator):
    def generate(self, base='.'):
        self.build_dir = os.path.abspath(os.path.join(base, 'build',
            'x11'))
        os.makedirs(self.build_dir, exist_ok=True)

        if self.dry_run:
            logger.info("Dry run completed.")
            return

        with open(os.path.join(self.build_dir, "%s.xkb" % (
            self._project.internal_name)), 'w') as f:
            for name, layout in self._project.layouts.items():
                f.write(self.generate_nonsense(name, layout))

    def generate_nonsense(self, name, layout):
        buf = io.StringIO()

        buf.write("default partial alphanumeric_keys\n")
        buf.write('xkb_symbols "basic" {\n\n')
        buf.write('    include "latin"\n')
        buf.write('    name[Group1] = "%s";\n\n' % layout.display_names[layout.locale])

        col0 = mode_iter(layout, 'iso-default', required=True)
        col1 = mode_iter(layout, 'iso-shift')
        col2 = mode_iter(layout, 'iso-alt')
        col3 = mode_iter(layout, 'iso-alt+shift')

        def xkb_filter(*args):
            def xf(v):
                """actual filter function"""
                if v is None:
                    return ''

                v = CP_REGEX.sub(lambda x: chr(int(x.group(1), 16)), v)
                # check for anything outsize A-Za-z range
                #if re.match("^[A-Za-z]$", v):
                #    return v

                if len(v) > 1:
                    # X11 still doesn't seem to support ligatures on a single key!!
                    #return "{ %s }" % ", ".join(["U%04X" % ord(x) for x in v])
                    raise Exception("Unicode ligatures not supported in X11. "
                        "Triggered by: '%s'" % v)

                o = ord(v)
                return keysym_to_str.get(o, "U%04X" % ord(v))

            o = [xf(i) for i in args]
            while len(o) > 0 and o[-1] == '':
                o.pop()
            return tuple(o)

        for (iso, c0, c1, c2, c3) in zip(ISO_KEYS, col0, col1, col2, col3):
            cols = ", ".join("%10s" % x for x in xkb_filter(c0, c1, c2, c3))
            buf.write("    key <A%s> { [ %s ] };\n" % (iso, cols))

        buf.write('\n    include "level3(ralt_switch)"\n};\n\n')
        return buf.getvalue()
