import json

from .. import get_logger

logger = get_logger(__file__)

from .. import Parser
from ..gen import generators


class BahkatPackage:
    @classmethod
    def from_kbdgen_project(cls, proj_yaml, target, category):
        if target != "win":
            raise Exception("Only Windows is supported.")

        project = Parser().parse(proj_yaml)
        langs = set()
        for layout in project.layouts.values():
            langs.add(layout.locale)

        tree = {
            "@type": "https://bahkat.org/Package",
            "id": project.internal_name,
            "name": project.names,
            "description": project.descriptions,
            "version": project.target(target).get("version", "0.0.0"),
            "category": category,
            "languages": list(langs),
            "os": {"windows": ">= 8.1"},
            "dependencies": {},
            "virtualDependencies": {},
            "installer": None,
        }

        return cls(tree)

    def __init__(self, tree):
        self.tree = tree

    def to_json(self):
        return json.dumps(self.tree, indent=2) + "\n"


def main():
    import argparse, sys

    p = argparse.ArgumentParser(prog="bahkatgen")
    p.add_argument(
        "-t",
        "--target",
        required=True,
        choices=generators.keys(),
        help="Target output.",
    )
    p.add_argument("-c", "--category", required=True, help="Category for package")
    p.add_argument(
        "kbdgen_project",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
    )
    p.add_argument("output_json", type=argparse.FileType("w"), default=sys.stdout)
    args = p.parse_args()

    package = BahkatPackage.from_kbdgen_project(
        args.kbdgen_project, args.target, args.category
    )
    args.output_json.write(package.to_json())


if __name__ == "__main__":
    main()
