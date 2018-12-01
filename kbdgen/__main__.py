import sys

if __name__ == "__main__":
    if sys.version_info.major < 3:
        print("kbdgen only supports Python 3.")
        sys.exit(1)
    try:
        from .cli import run_cli
        sys.exit(run_cli())
    except KeyboardInterrupt:
        sys.exit(255)
