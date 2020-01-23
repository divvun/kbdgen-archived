import logging
import os
import os.path
import re
import sys
import itertools
import unicodedata
from collections import OrderedDict, namedtuple

from . import orderedyaml, log, models
from .bundle import ProjectBundle


class KbdgenException(Exception):
    pass


class UserException(Exception):
    pass


def get_logger(name):
    return log.get_logger(name)

logger = get_logger(__name__)

ProjectLocaleData = namedtuple("ProjectLocaleData", ["name", "description"])

VALID_ID_RE = re.compile(r"^[a-z][0-9a-z-_]+$")

ISO_KEYS = (
    "E00",
    "E01",
    "E02",
    "E03",
    "E04",
    "E05",
    "E06",
    "E07",
    "E08",
    "E09",
    "E10",
    "E11",
    "E12",
    "D01",
    "D02",
    "D03",
    "D04",
    "D05",
    "D06",
    "D07",
    "D08",
    "D09",
    "D10",
    "D11",
    "D12",
    "C01",
    "C02",
    "C03",
    "C04",
    "C05",
    "C06",  # TODO fix the D13 special case.
    "C07",
    "C08",
    "C09",
    "C10",
    "C11",
    "D13",  # C12 -> D13
    "B00",
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B09",
    "B10",
)

MODE_LIST_ERROR = """\
'%s' must be defined as a string using block string format, not a list.

For example, if your keyboard.yaml looks like:

```
modes:
  mobile:
    default: [
        q w e r t y u i o p å,
        a s d f g h j k l ö æ,
        z x c v b n m ï
    ]
```

Convert that to:

```
modes:
  mobile:
    default: |
        q w e r t y u i o p å
        a s d f g h j k l ö æ
        z x c v b n m ï
```
"""


# class Project:
#     def __init__(self, tree):
#         self._tree = tree

#     def relpath(self, end):
#         return os.path.abspath(os.path.join(self.path, end))

#     @property
#     def path(self):
#         return self._tree["_path"]

#     @property
#     def locales(self):
#         return self._tree["locales"]

#     @property
#     def author(self):
#         return self._tree["author"]

#     @property
#     def email(self):
#         return self._tree["email"]

#     @property
#     def layouts(self):
#         return self._tree["layouts"]

#     @property
#     def targets(self):
#         return self._tree["targets"]

#     @property
#     def internal_name(self):
#         return self._tree["internalName"]

#     @property
#     def app_strings(self):
#         return self._tree["appStrings"]

#     @property
#     def version(self):
#         return str(self._tree["version"])

#     @property
#     def build(self):
#         return str(self._tree["build"])

#     @property
#     def copyright(self):
#         return self._tree.get("copyright", "")

#     @property
#     def organisation(self):
#         return self._tree.get("organisation", "")

#     def locale(self, tag):
#         val = self.locales.get(tag, None)
#         if val is None:
#             return None
#         return ProjectLocaleData(val["name"], val["description"])

#     @property
#     def names(self):
#         x = {}
#         for tag, o in self.locales.items():
#             x[tag] = o["name"]
#         return x

#     @property
#     def descriptions(self):
#         x = {}
#         for tag, o in self.locales.items():
#             x[tag] = o["description"]
#         return x

#     def first_locale(self):
#         tag = next(iter(self.locales.keys()))
#         return self.locale(tag)

#     def target(self, target):
#         return self._tree["targets"].get(target, {}) or {}

#     def icon(self, target, size=None):
#         val = self.target(target).get("icon", None)
#         if val is None:
#             return None
#         if isinstance(val, str):
#             return self.relpath(val)
#         if size is None:
#             # Find largest
#             m = -1
#             for k in val:
#                 if k > m:
#                     m = k
#             return self.relpath(val[m])
#         else:
#             lrg = -1
#             m = sys.maxsize
#             for k in val:
#                 if k > lrg:
#                     lrg = k
#                 if k >= size and k < m:
#                     m = k
#             if m == sys.maxsize:
#                 return self.relpath(val[lrg])
#             return self.relpath(val[m])


# class Keyboard:
#     def __init__(self, tree):
#         self._tree = tree

#     @property
#     def internal_name(self):
#         return self._tree["internalName"]

#     @property
#     def native_display_name(self):
#         return self.display_names[self.locale]

#     @property
#     def display_names(self):
#         return self._tree["displayNames"]

#     @property
#     def locale(self):
#         return self._tree["locale"]

#     @property
#     def special(self):
#         return self._tree.get("special", {})

#     @property
#     def decimal(self):
#         return self._tree.get("decimal", None)

#     @property
#     def dead_keys(self):
#         return self._tree.get("deadKeys", {})

#     @property
#     def derive(self):
#         return self._tree.get("derive", {})

#     @property
#     def transforms(self):
#         return self._tree.get("transforms", {})

#     @property
#     def modifiers(self):
#         return self._tree["modifiers"]

#     @property
#     def modes(self):
#         return self._tree["modes"]

#     @property
#     def strings(self):
#         return self._tree.get("strings", {})

#     @property
#     def styles(self):
#         return self._tree["styles"]

#     def target(self, target):
#         return self._tree.get("targets", {}).get(target, {}) or {}

#     def get_actions(self, style):
#         return self.styles[style]["actions"]

#     def get_action(self, style, key):
#         return self.styles[style]["actions"].get(key, None)

#     @property
#     def longpress(self):
#         return self._tree["longpress"]

#     def get_longpress(self, key):
#         return self._tree["longpress"].get(key, None)

#     @property
#     def supported_targets(self):
#         return self._tree.get("supportedTargets", None)

#     def supported_target(self, target):
#         targets = self.supported_targets
#         if targets is None:
#             return True
#         return target in targets


class Parser:
    def __init__(self):
        pass

    def _overrides(self, project, cfg_pairs):
        def resolve_path(path, v):
            chunks = path.split(".")

            last = chunks.pop()
            node = project

            for chunk in chunks:
                if getattr(node, chunk, None) is None:
                    setattr(node, chunk, OrderedDict())
                node = getattr(node, chunk, None)
            setattr(node, last, v)

        for path, v in cfg_pairs:
            resolve_path(path, v)

    def _parse_cfg_pairs(self, str_list):
        try:
            return [x.split("=", 1) for x in str_list]
        except Exception:
            raise Exception("Error: invalid key-value pair provided.")

    def parse(self, proj_path, cfg_pairs=None, cfg_file=None):
        if not proj_path.endswith(".kbdgen"):
            items = list(filter(lambda x: x.endswith(".kbdgen"), os.listdir(proj_path)))
            if len(items) > 1:
                raise UserException(
                    "Could not guess which .kbdgen bundle to load. Specify a full path to a .kbdgen bundle."
                )
            if len(items) > 0:
                proj_path = os.path.join(proj_path, items.pop())
        try:
            project = ProjectBundle.load(proj_path)
        except Exception as e:
            raise UserException("Could not load project bundle. Invalid YAML?", e)
        if cfg_pairs is not None:
            logger.trace("cfg_pairs: %r", cfg_pairs)
            self._overrides(project, self._parse_cfg_pairs(cfg_pairs))
        return project
