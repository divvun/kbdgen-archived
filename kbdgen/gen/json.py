import os.path
import shutil

from collections import OrderedDict

from .base import Generator, run_process, MobileLayoutView
from ..base import get_logger
from .ios import AppleiOSGenerator
import json

logger = get_logger(__name__)


class JSONGenerator(Generator):
    def generate(self, base="."):
        out_dir = os.path.abspath(base)
        os.makedirs(out_dir, exist_ok=True)
        fn = os.path.join(out_dir, "%s.json" % os.path.splitext(self._bundle.path)[0])

        layouts = OrderedDict()

        for name, layout in self._bundle.layouts.items():
            layouts[name] = layout

        with open(fn, "w") as f:
            json.dump({"layouts": layouts}, f, indent=2, ensure_ascii=False)


class QRGenerator(AppleiOSGenerator):
    def generate(self, base="."):
        import brotli

        if not shutil.which("qrencode"):
            logger.error("`qrencode` not found on PATH.")
            return

        command = self._args.get("command", None)
        logger.trace("Command: %s" % command)
        preferred_locale = None
        if command is not None:
            preferred_locale = command

        for name, layout in self.supported_layouts.items():
            if preferred_locale is not None:
                if name == preferred_locale:
                    logger.info("Using given locale: %s", preferred_locale)
                    break
            else:
                logger.info("Choosing first layout from project: %s" % name)
                break
        else:
            logger.error("No locale found.")
            return

        o = self.generate_json_layout(name, layout)
        data = json.dumps(o, ensure_ascii=False, separators=(",", ":"))
        compressed = brotli.compress(data.encode("utf-8"))
        logger.debug(["%02x" % x for x in compressed])
        logger.debug("%s %s" % (len(data), len(compressed)))
        fn_path = os.path.abspath(os.path.join(base, "%s.png" % name))

        run_process(["qrencode", "-8o", fn_path], shell=False, pipe=compressed)
        logger.info("QR code generated at: %s" % fn_path)
