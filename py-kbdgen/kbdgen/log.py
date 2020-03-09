import sys
import io
import traceback
import logging
import os
import os.path


class RustLogger:
    def __init__(self, target):
        import rust_logger

        self.rust_logger = rust_logger.Logger(target)

    def _log(self, level, msg):
        try:
            mod, lno = self._find_caller()
        except Exception as e:
            print(e)
            mod, lno = None, None

        if not isinstance(msg, str):
            try:
                msg = repr(msg)
            except:
                msg = str(msg)

        self.rust_logger.log(level, msg, lno, mod)

    def trace(self, msg):
        self._log(0, msg)

    def debug(self, msg):
        self._log(10, msg)

    def info(self, msg):
        self._log(20, msg)

    def warn(self, msg):
        self._log(30, msg)

    def warning(self, msg):
        self._log(30, msg)

    def error(self, msg):
        self._log(40, msg)

    def critical(self, msg):
        self._log(40, msg)

    def log(self, level, msg):
        self._log(level, msg)

    def _find_caller(self):
        stack = traceback.extract_stack()
        s = stack[-4]
        return (s[0], s[1])


def get_logger(target=None):
    if target is None:
        target = "<root>"
    return RustLogger(target)


def hijack_logging_getLogger():
    logging.getLogger = get_logger


# See logging mod for info on why this bad idea exists.
_srcfile = os.path.normcase(hijack_logging_getLogger.__code__.co_filename)
