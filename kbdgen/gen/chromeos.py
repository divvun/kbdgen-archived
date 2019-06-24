from collections import defaultdict, OrderedDict
import itertools
import json
import os
import os.path
import shutil
import requests
import tempfile

from ..base import get_logger
from .base import PhysicalGenerator, run_process, DesktopLayoutView, bind_iso_keys

logger = get_logger(__file__)

KEY_MAP = bind_iso_keys((
    # Row E
    "Backquote",
    "Digit1",
    "Digit2",
    "Digit3",
    "Digit4",
    "Digit5",
    "Digit6",
    "Digit7",
    "Digit8",
    "Digit9",
    "Digit0",
    "Minus",
    "Equal",

    # Row D
    "KeyQ",
    "KeyW",
    "KeyE",
    "KeyR",
    "KeyT",
    "KeyY",
    "KeyU",
    "KeyI",
    "KeyO",
    "KeyP",
    "BracketLeft",
    "BracketRight",

    # Row C
    "KeyA",
    "KeyS",
    "KeyD",
    "KeyF",
    "KeyG",
    "KeyH",
    "KeyJ",
    "KeyK",
    "KeyL",
    "Semicolon",
    "Quote",
    "Backslash",

    # Row B
    "IntlBackslash",
    "KeyZ",
    "KeyX",
    "KeyC",
    "KeyV",
    "KeyB",
    "KeyN",
    "KeyM",
    "Comma",
    "Period",
    "Slash"
))

LAYOUT_NAMES = {
    "nb": "{} testatur",
    "no": "{} testatur",
    "nn": "{} testatur",
    "sv": "{} tangentbord",
    "en": "{} keyboard"
}

def layout_name(locale, name):
    s = LAYOUT_NAMES.get(locale, LAYOUT_NAMES.get(locale.split("-")[0], None))
    if s is None:
        logger.warn("No layout format string found for locale '%s'; falling back to 'en'." % locale)
        s = LAYOUT_NAMES["en"]
    return s.format(name)

def replace_iso_keys(obj):
    o = {}
    for k in obj.keys():
        if obj[k] is None:
            continue
        o[KEY_MAP[k]] = obj[k]
    for k in o.keys():
        if len(o[k]) == 0:
            del o[k]
    return o

ICONS = {
    "16": "icon16.png",
    "48": "icon48.png",
    "128": "icon128.png"
}

class ChromeOSGenerator(PhysicalGenerator):
    @property
    def supported_layouts(self):
        o = OrderedDict()
        for k, v in self._bundle.layouts.items():
            if "chrome" in v.modes or "desktop" in v.modes:
                o[k] = v
        return o

    @property
    def chrome_target(self):
        return self._bundle.targets.get("chrome", {})
    
    def layout_target(self, layout):
        if layout.targets is not None:
            return layout.targets.get("chrome", {})
        return {}

    def xkb_base_layout(self, layout):
        fallback = self.layout_target(layout).get("locale", "us")
        if isinstance(fallback, list):
            fallback = fallback[0]
        return self.layout_target(layout).get("xkbLayout", fallback)

    def base_locale(self, layout):
        return self.layout_target(layout).get("locale", "en-US")

    def _msg(self, text):
        return {
            "message": text
        }

    def generate_manifest(self):
        messages = {}
        components = []

        for locale, desc in self._bundle.project.locales.items():
            if locale not in messages:
                messages[locale] = {}
            
            messages[locale]["name"] = self._msg(desc.name)
            messages[locale]["description"] = self._msg(desc.description)

        for locale, layout in self.supported_layouts.items():
            # messages[locale] = {}
            lookup_locale = locale.replace("-", "_")
            locale_msg = "__MSG_%s__" % lookup_locale

            component = {
                "name": locale_msg,
                "type": "ime",
                "id": locale,
                "description": locale_msg,
                "language": self.base_locale(layout),
                "layouts": [self.xkb_base_layout(layout)]
            }

            for display_locale, display_name in layout.display_names.items():
                if display_locale not in messages:
                    messages[display_locale] = {}
                messages[display_locale][lookup_locale] = self._msg(layout_name(display_locale, display_name))

            components.append(component)

        # Google isn't smart enough to fall back to English if a field is missing.
        for locale, obj in messages.items():
            if locale == "en":
                continue
            if obj.get("name", None) is None:
                obj["name"] = messages["en"]["name"]
            if obj.get("description", None) is None:
                obj["description"] = messages["en"]["description"]

        manifest = {
            "name": "__MSG_name__",
            "version": self.chrome_target.get("build", 1),
            "version_name": self.chrome_target.get("version", "0.0.0"),
            "manifest_version": 2,
            "description": "__MSG_description__",
            "background": {
                "scripts": ["background.js"]
            },
            "permissions": [
                "input"
            ],
            "input_components": components,
            "default_locale": "en",
            "icons": ICONS
        }

        return {
            "manifest": manifest,
            "messages": messages
        }

    def open_w(self, *args):
        return open(os.path.join(*args), 'w', encoding="utf-8")

    @property
    def chrome_resources(self):
        return self._bundle.resources("chrome")

    def generate_icons(self, build_dir):
        icon = os.path.join(self.chrome_resources, "icon.png")

        if not os.path.exists(icon):
            logger.warning("no icon supplied!")
            return

        cmd_tmpl = "convert -resize {h}x{w} -background white -alpha remove -gravity center -extent {h}x{w} {src} {out}"
        work_items = []

        for size, fn in ICONS.items():
            h = float(size)
            w = h
            cmd = cmd_tmpl.format(h=h, w=w, src=icon, out=os.path.join(build_dir, fn))

            msg = "Creating '%s' from '%s'…" % (fn, icon)
            work_items.append((msg, run_process(cmd.split(" "), return_process=True)))

        for (msg, process) in work_items:
            logger.info(msg)
            process.wait()

    @property
    def app_id(self):
        return self._app_id
        
    def sanity_check(self):
        if self.is_release:
            if self.chrome_target.get("build", None) is None:
                logger.error("No `build` property found in chrome target; cannot generator.")
                return False

            if self.chrome_target.get("version", None) is None:
                logger.error("No `version` property found in chrome target; cannot generator.")
                return False

            if os.environ.get("CHROME_CLIENT_ID", None) is None:
                logger.error("No `CHROME_CLIENT_ID` env var specified; cannot publish package to Chrome Web Store.")
                return False

            if os.environ.get("CHROME_CLIENT_SECRET", None) is None:
                logger.error("No `CHROME_CLIENT_SECRET` env var specified; cannot publish package to Chrome Web Store.")
                return False

            if os.environ.get("CHROME_REFRESH_TOKEN", None) is None:
                logger.error("No `CHROME_REFRESH_TOKEN` env var specified; cannot publish package to Chrome Web Store.")
                return False

            self._app_id = self.chrome_target.get("appId", None)
            if self._app_id is None:
                logger.error("No appId found in `chrome` target configuration; cannot publish.")
                return False

        return super().sanity_check()

    def upload_package(self, build_dir):
        data = {
            "grant_type": "refresh_token",
            "client_id": os.environ["CHROME_CLIENT_ID"],
            "client_secret": os.environ["CHROME_CLIENT_SECRET"],
            "refresh_token": os.environ["CHROME_REFRESH_TOKEN"]
        }

        oauth_response = requests.post("https://www.googleapis.com/oauth2/v4/token", data=data).json()

        logger.info("Generating .zip for upload…")
        with tempfile.TemporaryDirectory() as tmpdir:
            p = "%s/upload-%s.zip" % (tmpdir, self.app_id)
            logger.trace("p: %r, b: %r" % (p, build_dir))
            run_process(["zip", "-r9", p, "."], cwd=build_dir, show_output=True)

            url = "https://www.googleapis.com/upload/chromewebstore/v1.1/items/%s" % self.app_id
            headers = {
                "Authorization": "Bearer %s" % oauth_response["access_token"],
                "x-goog-api-version": "2"
            }
            logger.info("Uploading…")
            result = requests.put(url, headers=headers, data=open(p, 'rb').read())
            logger.debug("%r" % result)

            shutil.copyfile(p, os.path.join(build_dir, "..", "chrome-%s.zip" % self.app_id))

    def generate(self, base="."):
        if not self.sanity_check():
            return

        deps_dir = os.path.join(os.path.abspath(base), "chrome-build")
        os.makedirs(deps_dir, exist_ok=True)

        logger.info("Generating manifest and i18n files…")
        files = self.generate_manifest()
        manifest = json.dumps(files["manifest"], indent=2, ensure_ascii=False)

        logger.info("Writing manifest.json…")
        logger.trace(manifest)

        with self.open_w(deps_dir, "manifest.json") as f:
            f.write(manifest)

        for locale, contents in files["messages"].items():
            fn_locale = locale.replace("-", "_")
            logger.info("Writing _locales/%s/messages.json…" % fn_locale)
            locale_path = os.path.join(deps_dir, "_locales", fn_locale)
            os.makedirs(locale_path, exist_ok=True)
            messages = json.dumps(contents, indent=2, ensure_ascii=False)
            logger.trace(messages)
            with self.open_w(locale_path, "messages.json") as f:
                f.write(messages)

        layouts = {}
        for locale, layout in self.supported_layouts.items():
            logger.info("Generating layout for locale '%s'…" % locale)
            layout_view = DesktopLayoutView(layout, "chrome")

            modes = {}
            for (name, mode) in layout_view.modes().items():
                modes[name] = replace_iso_keys(mode)
                
            layout_descriptor = {
                "deadKeys": layout_view.dead_keys(),
                "transforms": layout.transforms,
                "layers": modes,
                "space": layout_view.space()
            }

            layouts[locale] = layout_descriptor

        logger.info("Writing keyboard layouts…")
        descriptor = "const descriptor = %s\n" % json.dumps(layouts, indent=2, ensure_ascii=False)
        start_line = "Keyboard.install(descriptor)"
        
        logger.info("Merging IME and keyboard descriptor…")
        with open(
            os.path.join(
                os.path.dirname(__file__), "bin", "keyboard.js"
            )) as f:
            background_js = "%s\n%s\n%s\n" % (f.read(), descriptor, start_line)
        
        logger.info("Writing background.js…")
        logger.trace(background_js)

        with self.open_w(deps_dir, "background.js") as f:
            f.write(background_js)

        logger.info("Generating icons…")
        self.generate_icons(deps_dir)

        if self.is_release:
            self.upload_package(deps_dir)
        logger.info("Done!")


