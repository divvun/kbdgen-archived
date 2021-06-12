from .log import hijack_logging_getLogger

try:
    hijack_logging_getLogger()
except Exception as e:
    print(e)

__version__ = "2.0.0-alpha.16"
