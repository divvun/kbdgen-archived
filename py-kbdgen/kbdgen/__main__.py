import sys


def main():
    if sys.version_info.major < 3:
        print("kbdgen only supports Python 3.")
        sys.exit(1)
    try:
        from .cli import run_cli

        sys.exit(run_cli(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(255)


if __name__ == "__main__":
    main()
