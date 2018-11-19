import os.path

from io import StringIO
from collections import namedtuple
from math import sqrt
from .base import Generator
from ..base import get_logger

logger = get_logger(__file__)
Key = namedtuple("Key", ["x", "y", "dist"])


def generate_error_map(layout):
    pass


def find_key_distance(a, b):
    (a_x, a_y) = a
    (b_x, b_y) = b
    return sqrt((b_x - a_x) ** 2 + (b_y - a_y) ** 2)


def generate_distances(coords):
    o = {}
    for (a, a_xy) in coords.items():
        dists = {}
        for (b, b_xy) in coords.items():
            dists[b] = find_key_distance(a_xy, b_xy)
        o[a] = Key(a_xy[0], a_xy[1], dists)
    return o


def calculate_row_offsets(rows):
    longest = -1
    for row in rows:
        if len(row) > longest:
            longest = len(row)

    offsets = []
    for row in rows:
        offsets.append((longest - len(row)) / 2)

    return offsets


def generate_coordinates(rows, offsets):
    o = {}

    for (y, row) in enumerate(rows):
        x_offset = offsets[y]
        for (x, key) in enumerate(row):
            o[key] = (x_offset + x, y)

    return o


def convert_phy_mode(mode):
    if isinstance(mode, list):
        return mode

    rows = []
    cur = []
    logger.warn(mode)
    p = "E"

    # TODO: this is naive and must fill gaps
    for k, v in mode.items():
        if not k.startswith(p):
            p = k[0]
            rows.append(cur)
            cur = []
        cur.append(v)

    if len(cur) > 0:
        rows.append(cur)

    return rows


def generate_xfst_macro(coords):
    alphas = " | ".join(coords.keys())
    regexes = []
    for (a, coord) in coords.items():
        regexes.append("[%s::0] @> [%s::0]" % (a, a))
        for (b, dist) in coord.dist.items():
            regexes.append("[%s::0] @> [%s::%s]" % (a, b, dist))
    data = """\
set print-weight ON
set precision 6

define Alphabet [%% %s] ;
regex %s ||
    Alphabet [Alphabet*] __ [Alphabet*] Alphabet ;
""" % (
        alphas,
        " ,\n    ".join(regexes)
    )

    return data


def generate_att(coords):
    # find end point of all items
    c = 1
    pairs = []
    out = StringIO()

    for (a, coord) in coords.items():
        for (b, dist) in coord.dist.items():
            pairs.append([a, b, dist])
    pairs.sort()
    
    for (a, b, dist) in pairs:
        first = c
        c += 1
        out.write("0\t{0}\t{1}\t{1}\t0.0\n".format(first, a))
        out.write("{0}\t@TERMINUS@\t{1}\t{1}\t{2}\n".format(first, b, "%.6f" % dist))
    out.write("{0} 0.0\n".format(c))

    v = out.getvalue().replace("@TERMINUS@", str(c))
    return v


class ErrorModelGenerator(Generator):
    def generate(self, base="."):
        out_dir = os.path.abspath(base)
        os.makedirs(out_dir, exist_ok=True)

        for name, layout in self._project.layouts.items():
            logger.info(name)
            logger.info("---")
            for (mode_name, mode) in layout.modes.items():
                if not mode_name.startswith("mobile"):
                    continue

                mode = convert_phy_mode(mode)
                offsets = calculate_row_offsets(mode)
                coords = generate_coordinates(mode, offsets)
                map_ = generate_distances(coords)
                print(generate_att(map_))
                return
