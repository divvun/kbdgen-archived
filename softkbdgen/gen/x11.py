import io

from .. import get_logger
from .base import *
from ..cldr import CP_REGEX

logger = get_logger(__file__)

class XKBGenerator(Generator):
    def generate(self, base='.'):
        logger.critical("This target is not fully implemented yet!")

        for name, layout in self._project.layouts.items():
            print(self.generate_nonsense(name, layout))

        if self.dry_run:
            logger.info("Dry run completed.")
            return

    def generate_nonsense(self, name, layout):
        buf = io.StringIO()

        buf.write("default partial alphanumeric_keys\n")
        buf.write('xkb_symbols "basic" {\n')
        buf.write('    name[Group1]= "%s";\n' % layout.display_names[layout.locale])
        buf.write('    include "us(basic)"\n\n')

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
                if re.match("^[A-Za-z]$", v):
                    return v

                if len(v) > 1:
                    return "{ %s }" % ", ".join(["U%04X" % ord(x) for x in v])
                return "U%04X" % ord(v)

            o = [xf(i) for i in args]
            while len(o) > 0 and o[-1] == '':
                o.pop()
            return tuple(o)

        for (iso, c0, c1, c2, c3) in zip(ISO_KEYS, col0, col1, col2, col3):
            cols = ", ".join("%10s" % x for x in xkb_filter(c0, c1, c2, c3))
            buf.write("    key <A%s> { [ %s ] };\n" % (iso, cols))

        buf.write('\n    include "level3(ralt_switch)"\n};')
        return buf.getvalue()

