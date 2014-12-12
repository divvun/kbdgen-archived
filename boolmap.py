import array
import io

class BoolMap:
    def __init__(self, bytedata=None, default=False):
        self._default = bool(default)
        self._data = array.array('B')
        if bytedata is not None:
            self._data.frombytes(bytedata)

    def __getitem__(self, k):
        if not isinstance(k, int):
            raise KeyError(k)

        pos = k // 8
        off = k % 8

        if pos >= len(self._data):
            return self._default

        return bool(self._data[pos] & 1 << off)

    def __setitem__(self, k, v):
        if not isinstance(k, int):
            raise KeyError(k)
        if not isinstance(v, bool):
            raise ValueError(v)

        pos = k // 8
        off = k % 8

        if pos >= len(self._data):
            self._data.fromlist(
                    [0 if self._default is False else 0xFF] * (
                        pos - len(self._data) + 1))

        chunk = self._data[pos]
        if v:
            self._data[pos] = chunk | 1 << off
        else:
            self._data[pos] = ~(~chunk & 0xFF | (1 << off)) & 0xFF

        return v

    def __iter__(self):
        for v in self._data:
            for i in range(8):
                yield bool(v & (1 << i))

    def to_bytes(self):
        return self._data.tobytes()


def parse_range_data(data):
    range_data = [x.split('-', 1) for x in data.split(',')]
    new_ranges = []

    for chunk in range_data:
        l = len(chunk)
        if 0 > l > 2:
            raise Exception()
        if len(chunk) == 1:
            chunk.append(chunk[0])
        new_ranges.append(range(int(chunk[0], 16), int(chunk[1], 16) + 1))

    # pop the end, I hate it.
    new_ranges.pop()
    return new_ranges


def apply_ranges_to_boolmap(data):
    boolmap = BoolMap()
    for iterator in data:
        for i in iterator:
            boolmap[i] = True
    return boolmap

if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as f:
        data = f.read()
    ranges = parse_range_data(data)
    bm = apply_ranges_to_boolmap(ranges)
    with open(sys.argv[1] + '.bin', 'wb') as f:
        f.write(bm.to_bytes())
