import urllib.request
import sys
import shutil
import platform

clr_line = "%c[2K\r" % 27
blocks = " ▏▎▍▌▋▊▉█"


def stream_download(url: str, fn: str, output_file: str):
    r = urllib.request.urlopen(url)

    with open(output_file, "wb") as f:
        i = 0
        block_size = 1024
        content_len = None

        while True:
            block = r.read(block_size)
            if not block:
                break
            f.write(block)

            if content_len is None:
                content_len = r.headers.get("content-length", None)

            if content_len is not None:
                max_size_raw = int(content_len)
                i = min(max_size_raw, i + block_size)
                # write_download_progress(fn, i, max_size_raw)
        print()


def generate_prog_bar(width: int, cur_sz: int, max_sz: int):
    if width < 1:
        return ""
    units = width
    t = cur_sz / max_sz * units
    if t == 0:
        bars = "▏"
    else:
        bars = "█" * int(t)
    et = t - int(t)
    if et > 0:
        extra = int(len(blocks) * et)
        bars += blocks[extra]
    return ("{:<%d}" % units).format(bars)


def truncate_middle(text: str, sz: int) -> str:
    if len(text) <= sz:
        return text
    split = sz // 2
    left = split
    right = split
    if sz % 2 == 0:
        left -= 1
    return "%s…%s" % (text[:left], text[-right:])


if __name__ == "__main__":
    test_download_bar()
