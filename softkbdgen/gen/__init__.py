#import os
#import os.path
#import sys
#import shutil
#import subprocess
#import copy
#import re
#import io
#import json
#import uuid
#import plistlib
#import random
#import itertools
#
#from textwrap import dedent, indent
#from collections import OrderedDict, defaultdict
#from itertools import zip_longest
#
#import pycountry
#from lxml import etree
#from lxml.etree import Element, SubElement
#
#from . import cldr
#
#from .cldr import CP_REGEX, decode_u

# TODO use logger for output

from .base import *

from .ios import AppleiOSGenerator
from .android import AndroidGenerator
from .win import WindowsGenerator
from .osx import OSXGenerator
from .x11 import XKBGenerator
from .svgkbd import SVGGenerator






