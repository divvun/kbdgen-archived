import copy
import os.path
import itertools

from collections import OrderedDict
from textwrap import dedent

from .. import get_logger
from .base import *
from ..cldr import decode_u
import json

logger = get_logger(__file__)

class JSONGenerator(Generator):
    def generate(self, base='.'):
        out_dir = os.path.abspath(base)
        os.makedirs(out_dir, exist_ok=True)
        fn = os.path.join(out_dir, "%s.json" % self._project.internal_name)

        layouts = OrderedDict()

        for name, layout in self.supported_layouts.items():
            layouts[layout.internal_name] = layout._tree

        with open(fn, 'w') as f:
            json.dump({"layouts": layouts}, f, indent=2)

