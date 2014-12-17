import argparse

from . import *

def parse_args():
    p = argparse.ArgumentParser(prog="softkbdgen")
    p.add_argument('-D', '--dry-run', action="store_true",
                   help="Don't build, just do sanity checks.")
    p.add_argument('-K', '--key', nargs="*", dest='cfg_pairs',
                   help="Key-value overrides (eg -K target.thing.foo=42)")
    p.add_argument('-R', '--release', action='store_true',
                   help="Compile in 'release' mode.")
    p.add_argument('-G', '--global', type=argparse.FileType('r'),
                   help="Override the global.yaml file")
    p.add_argument('-b', '--branch', default='stable',
                   help='Git branch (default: stable)')
    p.add_argument('-r', '--repo', help='Git repo.')
    p.add_argument('-t', '--target', required=True,
                   help="Target output.")
    p.add_argument('project', type=argparse.FileType('r'),
                   default=sys.stdin)
    return p.parse_args()

def parse_cfg_pairs(str_list):
    try:
        return [x.split('=', 1) for x in str_list]
    except:
        raise Exception("Error: invalid key-value pair provided.")

def main():
    args = parse_args()

    try:
        project = Parser().parse(args.project,
                                 args.cfg_pairs)
    except Exception as e:
        raise e
        print(e)
        sys.exit(1)

    if args.target not in ["android", "ios"]:
        print("Error: only 'android' and 'ios' are supported currently.")
        sys.exit(1)

    if args.target == "android":
        x = gen.AndroidGenerator(project, dict(args._get_kwargs()))
    elif args.target == "ios":
        x = gen.AppleiOSGenerator(project, dict(args._get_kwargs()))

    try:
        x.generate()
    except gen.MissingApplicationException as e:
        print(e)

if __name__ == "__main__":
    main()
