import urllib.request


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
