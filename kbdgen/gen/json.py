import os.path
import shutil

from collections import OrderedDict

from .base import Generator, run_process, MobileLayoutView
from ..base import get_logger
import json

logger = get_logger(__file__)


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

class QRGenerator(Generator):
    def generate(self, base="."):
        if not shutil.which("qrencode"):
            logger.error("`qrencode` not found on PATH.")
            return

        command = self._args.get("command", None)
        logger.trace("Command: %s" % command)
        preferred_locale = None
        if command is not None:
            preferred_locale = command

        tree = None
        for name, layout in self._bundle.layouts.items():
            if preferred_locale is not None:
                if name == preferred_locale:
                    logger.info("Using given locale: %s", preferred_locale)
                    tree = layout
                    break
            else:
                logger.info("Choosing first layout from project: %s" % name)
                tree = layout
                break
        
        if tree is None:
            logger.error("No locale found.")
            return

        layout_view = MobileLayoutView(tree, "ios")

        o = {
            "name": layout.display_names[name],
            "space": tree.strings.space,
            "enter": tree.strings._return,
            "normal": layout_view.mode("default"),
            "shifted": layout_view.mode("shift"),
            "longPress": tree.longpress
        }

        data = json.dumps(o, ensure_ascii=False, separators=(',', ':'))
        logger.debug(data)
        fn_path = os.path.abspath(os.path.join(base, "%s.png" % name))
        run_process(["qrencode", data, "-o", fn_path], shell=False)
        logger.info("QR code generated at: %s" % fn_path)