def keys():
    return sorted(["win", "mac", "svg", "android", "ios", "json", "qr", "errormodel", "chrome"])

def get(key):
    if key == 'win':
        from .win import WindowsGenerator
        return WindowsGenerator
    if key == 'ios':
        from .ios import AppleiOSGenerator
        return AppleiOSGenerator
    if key == 'android':
        from .android import AndroidGenerator
        return AndroidGenerator
    if key == 'mac':
        from .mac import MacGenerator
        return MacGenerator
    if key == 'svg':
        from .svgkbd import SVGGenerator
        return SVGGenerator
    if key == 'json':
        from .json import JSONGenerator
        return JSONGenerator
    if key == 'errormodel':
        from .errormodel import ErrorModelGenerator
        return ErrorModelGenerator
    if key == 'chrome':
        from .chromeos import ChromeOSGenerator
        return ChromeOSGenerator
    if key == 'qr':
        from .json import QRGenerator
        return QRGenerator
