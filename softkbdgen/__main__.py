import argparse
import yaml
import sys

from . import VERSION, Parser, gen, logger

generators = {
    "android": gen.AndroidGenerator,
    "ios": gen.AppleiOSGenerator,
    "osx": gen.OSXGenerator,
    "svg": gen.SVGGenerator,
    "win": gen.WindowsGenerator,
    "x11": gen.XKBGenerator
}

def parse_args():
    def logging_type(string):
        n = {
            "critical": 50,
            "error": 40,
            "warning": 30,
            "info": 20,
            "debug": 10,
            "trace": 5
        }.get(string, None)

        if n is None:
            raise argparse.ArgumentTypeError("Invalid logging level.")
        return n

    epilog = "Available targets: %s" % ", ".join(sorted(generators))
    p = argparse.ArgumentParser(prog="softkbdgen", epilog=epilog)
    p.add_argument('--version', action='version',
            version="%(prog)s " + VERSION)
    p.add_argument('--logging', type=logging_type, default=20,
                   help="Logging level")
    p.add_argument('-D', '--dry-run', action="store_true",
                   help="Don't build, just do sanity checks.")
    p.add_argument('-K', '--key', nargs="*", dest='cfg_pairs',
                   help="Key-value overrides (eg -K target.thing.foo=42)")
    p.add_argument('-R', '--release', action='store_true',
                   help="Compile in 'release' mode (where necessary).")
    p.add_argument('-G', '--global', type=argparse.FileType('r'),
                   help="Override the global.yaml file")
    p.add_argument('-b', '--branch', default='stable',
                   help='Git branch (default: stable)')
    p.add_argument('-r', '--repo', help='Git repo.')
    p.add_argument('-t', '--target', required=True,
                   help="Target output.")
    p.add_argument('project', help="Keyboard generation project (yaml)",
                   type=argparse.FileType('r'),
                   default=sys.stdin)
    return p.parse_args()

def main():
    args = parse_args()

    logger.setLevel(args.logging)

    try:
        project = Parser().parse(args.project,
                                 args.cfg_pairs)

    except yaml.scanner.ScannerError as e:
        print("Error parsing project:\n%s\n%s" % (
                e.problem,
                e.problem_mark
            ), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if logger.getEffectiveLevel() <= 10:
            raise e
        print("Error:", e, file=sys.stderr)
        sys.exit(1)

    generator = generators.get(args.target, None)

    if generator is None:
        print("Error: '%s' is not a valid target." % args.target,
                file=sys.stderr)
        print("Valid targets: %s" % ", ".join(generators),
                file=sys.stderr)
        sys.exit(1)

    x = generator(project, dict(args._get_kwargs()))

    try:
        x.generate()
    except gen.MissingApplicationException as e:
        print(e, file=sys.stderr)

if __name__ == "__main__":
    main()
