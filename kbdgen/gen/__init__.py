from collections import OrderedDict

from .ios import AppleiOSGenerator
from .android import AndroidGenerator
from .win import WindowsGenerator
from .mac import MacGenerator
from .x11 import XKBGenerator
from .svgkbd import SVGGenerator
from .json import QRGenerator, JSONGenerator
from .errormodel import ErrorModelGenerator
from .chromeos import ChromeOSGenerator

generators = OrderedDict(
    (
        ("win", WindowsGenerator),
        ("mac", MacGenerator),
        ("x11", XKBGenerator),
        ("svg", SVGGenerator),
        ("android", AndroidGenerator),
        ("ios", AppleiOSGenerator),
        ("json", JSONGenerator),
        ("qr", QRGenerator),
        ("errormodel", ErrorModelGenerator),
        ("chrome", ChromeOSGenerator),
    )
)
