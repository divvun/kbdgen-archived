# LogFormatter taken straight from
# https://github.com/tornadoweb/tornado/blob/dcd1ef81df68ba928e6bbeb1cf194f1ff694ec49/tornado/log.py
# Other bits mangled to support Python 3 only and remove deps.
#
# Copyright 2012 Facebook
# Copyright 2016 Brendan Molloy <brendan@bbqsrc.net>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# Modified by Brendan Molloy (c) 2015
#

"""Logging support for kbdgen.

kbdgen uses three logger streams:

* ``tornado.access``: Per-request logging for kbdgen's HTTP servers (and
  potentially other servers in the future)
* ``tornado.application``: Logging of errors from application code (i.e.
  uncaught exceptions from callbacks)
* ``tornado.general``: General-purpose logging, including any errors
  or warnings from kbdgen itself.

These streams may be configured independently using the standard library's
`logging` module.  For example, you may wish to send ``tornado.access`` logs
to a separate file for analysis.
"""
from __future__ import absolute_import, division, print_function, with_statement

import logging
import logging.handlers
import sys

def to_unicode(value):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, (str, type(None))):
        return value
    if not isinstance(value, bytes):
        raise TypeError("Expected bytes, unicode, or None; got %r" % type(value))
    return value.decode("utf-8")


try:
    import curses
except ImportError:
    curses = None

# Logger objects for internal tornado use
access_log = logging.getLogger("kbdgen.access")
app_log = logging.getLogger("kbdgen.application")
gen_log = logging.getLogger("kbdgen.general")


def _stderr_supports_color():
    color = False
    if curses and hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except Exception:
            pass
    return color


def _safe_unicode(s):
    try:
        return to_unicode(s)
    except UnicodeDecodeError:
        return repr(s)


class LogFormatter(logging.Formatter):
    """Log formatter used in kbdgen.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.
    """

    DEFAULT_FORMAT = "%(color)s[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s"  # noqa
    DEFAULT_DATE_FORMAT = "%y%m%d %H:%M:%S"
    DEFAULT_COLORS = {
        logging.DEBUG: 4,  # Blue
        logging.INFO: 2,  # Green
        logging.WARNING: 3,  # Yellow
        logging.ERROR: 1,  # Red
        logging.CRITICAL: 1,  # Red
    }

    def __init__(
        self,
        color=True,
        fmt=DEFAULT_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        colors=DEFAULT_COLORS,
    ):
        r"""
        :arg bool color: Enables color support.
        :arg string fmt: Log message format.
          It will be applied to the attributes dict of log records. The
          text between ``%(color)s`` and ``%(end_color)s`` will be colored
          depending on the level if color support is on.
        :arg dict colors: color mappings from logging level to terminal color
          code
        :arg string datefmt: Datetime format.
          Used for formatting ``(asctime)`` placeholder in ``prefix_fmt``.

        .. versionchanged:: 3.2

           Added ``fmt`` and ``datefmt`` arguments.
        """
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._fmt = fmt

        self._colors = {}
        if color and _stderr_supports_color():
            # The curses module has some str/bytes confusion in
            # python3.  Until version 3.2.3, most methods return
            # bytes, but only accept strings.  In addition, we want to
            # output these strings with the logging module, which
            # works with unicode strings.  The explicit calls to
            # unicode() below are harmless in python2 but will do the
            # right conversion in python 3.
            fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or ""
            if (3, 0) < sys.version_info < (3, 2, 3):
                fg_color = str(fg_color, "ascii")

            for levelno, code in colors.items():
                self._colors[levelno] = str(curses.tparm(fg_color, code), "ascii")
            self._normal = str(curses.tigetstr("sgr0"), "ascii")
        else:
            self._normal = ""

    def format(self, record):
        try:
            message = record.getMessage()
            assert isinstance(message, str)  # guaranteed by logging
            # Encoding notes:  The logging module prefers to work with character
            # strings, but only enforces that log messages are instances of
            # basestring.  In python 2, non-ascii bytestrings will make
            # their way through the logging framework until they blow up with
            # an unhelpful decoding error (with this formatter it happens
            # when we attach the prefix, but there are other opportunities for
            # exceptions further along in the framework).
            #
            # If a byte string makes it this far, convert it to unicode to
            # ensure it will make it out to the logs.  Use repr() as a fallback
            # to ensure that all byte strings can be converted successfully,
            # but don't do it by default so we don't add extra quotes to ascii
            # bytestrings.  This is a bit of a hacky place to do this, but
            # it's worth it since the encoding errors that would otherwise
            # result are so useless (and tornado is fond of using utf8-encoded
            # byte strings whereever possible).
            record.message = _safe_unicode(message)
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = self.formatTime(record, self.datefmt)

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ""

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to _safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(_safe_unicode(ln) for ln in record.exc_text.split("\n"))
            formatted = "\n".join(lines)
        return formatted.replace("\n", "\n    ")


def enable_pretty_logging(options=None, logger=None, fmt=None):
    """Turns on formatted logging output as configured."""
    if logger is None:
        logger = logging.getLogger()

    # Set up color if we are in a tty and curses is installed
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter(fmt=fmt))
    logger.addHandler(channel)


def monkey_patch_trace_logging():
    setattr(logging, "TRACE", 5)
    logging._levelToName[logging.TRACE] = "TRACE"
    logging._nameToLevel["TRACE"] = logging.TRACE

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.TRACE):
            self._log(logging.TRACE, msg, args, **kwargs)

    logging.Logger.trace = trace

    LogFormatter.DEFAULT_COLORS[logging.TRACE] = 5
