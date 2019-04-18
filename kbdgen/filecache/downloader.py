import humanize
import requests
import sys
import shutil

clr_line = "%c[2K\r" % 27
blocks = " ▏▎▍▌▋▊▉█"


def stream_download(url: str, fn: str, output_file: str):
    r = requests.get(url, stream=True)

    with open(output_file, "wb") as f:
        i = 0
        block_size = 1024
        content_len = None

        for block in r.iter_content(block_size, decode_unicode=False):
            if not block:
                continue
            f.write(block)

            if content_len is None:
                content_len = r.headers.get("content-length", None)

            if content_len is not None:
                max_size_raw = int(content_len)
                i = min(max_size_raw, i + block_size)
                write_download_progress(fn, i, max_size_raw)
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


def write_download_progress(fn: str, cur_sz: int, max_sz: int):
    if platform.system() == "Windows":
        return
    if cur_sz < 1000:
        c = "%s B" % cur_sz
    else:
        c = humanize.naturalsize(min(cur_sz, max_sz))

    m = humanize.naturalsize(max_sz)
    pc = "%.0f" % min(cur_sz / max_sz * 100.0, 100.0)
    w = min(shutil.get_terminal_size().columns, 80)

    max_fn_len = w // 3
    fn = truncate_middle(fn, max_fn_len)
    pc_len = 4
    space_punc_len = 7
    msg_len = len(fn) + max(len(c) + len(m), 18) + pc_len + space_punc_len
    prog = generate_prog_bar(w - msg_len, cur_sz, max_sz)

    msg = "{clr}{fn}: {pc:>3}% {prog}▏ {frac:<18}".format(
        clr=clr_line, fn=fn, prog=prog, frac="{cur}/{max}".format(cur=c, max=m), pc=pc
    )

    sys.stdout.write(msg)
    sys.stdout.flush()


def test_download_bar():
    import time
    import random

    fsize = 2717221829
    i = 0
    while i < fsize:
        write_download_progress("a-ridiculous-name-that-was-truncated.tgz", i, fsize)
        time.sleep(random.random() / 500)
        i += random.randint(0, 250000)
    i = fsize
    write_download_progress("a-ridiculous-name-that-was-truncated.tgz", i, fsize)
    print()


if __name__ == "__main__":
    test_download_bar()
