import copy
import json
import uuid
import pathlib
import itertools
import subprocess
import re
from collections import OrderedDict

from lxml import etree
from lxml.etree import Element, SubElement

from ..bundle import parse_desktop_layout
from ..base import get_logger
from ..cldr import CP_REGEX

logger = get_logger(__file__)

OSX_KEYMAP = OrderedDict(
    (
        ("C01", "0"),
        ("C02", "1"),
        ("C03", "2"),
        ("C04", "3"),
        ("C06", "4"),
        ("C05", "5"),
        ("B01", "6"),
        ("B02", "7"),
        ("B03", "8"),
        ("B04", "9"),
        ("B00", "50"),  # E00 flipped!
        ("B05", "11"),
        ("D01", "12"),
        ("D02", "13"),
        ("D03", "14"),
        ("D04", "15"),
        ("D06", "16"),
        ("D05", "17"),
        ("E01", "18"),
        ("E02", "19"),
        ("E03", "20"),
        ("E04", "21"),
        ("E06", "22"),
        ("E05", "23"),
        ("E12", "24"),
        ("E09", "25"),
        ("E07", "26"),
        ("E11", "27"),
        ("E08", "28"),
        ("E10", "29"),
        ("D12", "30"),
        ("D09", "31"),
        ("D07", "32"),
        ("D11", "33"),
        ("D08", "34"),
        ("D10", "35"),
        # U WOT 36 - space yeah yeah
        ("C09", "37"),
        ("C07", "38"),
        ("C11", "39"),
        ("C08", "40"),
        ("C10", "41"),
        ("D13", "42"),
        ("B08", "43"),
        ("B10", "44"),
        ("B06", "45"),
        ("B07", "46"),
        ("B09", "47"),
        # U WOT 48 - backspace yeah yeah
        ("A03", "49"),
        ("E00", "10"),  # B00 flipped!
        ("E13", "93"),
        ("B11", "94"),
    )
)

OSX_HARDCODED = OrderedDict(
    (
        ("36", r"\u{D}"),
        ("48", r"\u{9}"),
        ("51", r"\u{8}"),
        ("53", r"\u{1B}"),
        ("64", r"\u{10}"),
        ("66", r"\u{1D}"),
        ("70", r"\u{1C}"),
        ("71", r"\u{1B}"),
        ("72", r"\u{1F}"),
        ("76", r"\u{3}"),
        ("77", r"\u{1E}"),
        ("79", r"\u{10}"),
        ("80", r"\u{10}"),
        ("96", r"\u{10}"),
        ("97", r"\u{10}"),
        ("98", r"\u{10}"),
        ("99", r"\u{10}"),
        ("100", r"\u{10}"),
        ("101", r"\u{10}"),
        ("103", r"\u{10}"),
        ("105", r"\u{10}"),
        ("106", r"\u{10}"),
        ("107", r"\u{10}"),
        ("109", r"\u{10}"),
        ("111", r"\u{10}"),
        ("113", r"\u{10}"),
        ("114", r"\u{5}"),
        ("115", r"\u{1}"),
        ("116", r"\u{B}"),
        ("117", r"\u{7F}"),
        ("118", r"\u{10}"),
        ("119", r"\u{4}"),
        ("120", r"\u{10}"),
        ("121", r"\u{C}"),
        ("122", r"\u{10}"),
        ("123", r"\u{1C}"),
        ("124", r"\u{1D}"),
        ("125", r"\u{1F}"),
        ("126", r"\u{1E}"),
    )
)


def plutil_get_json(path):
    cmd = "plutil -convert json -o -".split(" ")
    cmd.append(path)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    json_str = process.communicate()[0].decode()
    return json.loads(json_str, object_pairs_hook=OrderedDict)


def plutil_to_xml_str(json_obj):
    cmd = "plutil -convert xml1 -o - -".split(" ")

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    return process.communicate(json.dumps(json_obj).encode())[0].decode()


class Pbxproj:
    @staticmethod
    def gen_key():
        return uuid.uuid4().hex[8:].upper()

    def __init__(self, path):
        self._proj = plutil_get_json(path)

    def __str__(self):
        return plutil_to_xml_str(self._proj)

    @property
    def objects(self):
        return self._proj["objects"]

    @property
    def root(self):
        return self.objects[self._proj["rootObject"]]

    @property
    def main_group(self):
        return self.objects[self.root["mainGroup"]]

    def find_ref_for_name(self, name, isa=None):
        for ref, o in self.objects.items():
            if o.get("name", None) == name and (
                isa is None or o.get("isa", None) == isa
            ):
                return ref
        return None

    def find_resource_build_phase(self, target_name):
        targets = [self.objects[t] for t in self.root["targets"]]
        target = None

        for t in targets:
            if t["name"] == target_name:
                target = t
                break

        if target is None:
            return None

        for build_phase in target["buildPhases"]:
            phase = self.objects[build_phase]
            if phase["isa"] == "PBXResourcesBuildPhase":
                return phase

        return None

    def create_plist_string_variant(self, variants):
        o = {
            "isa": "PBXVariantGroup",
            "children": variants,
            "name": "InfoPlist.strings",
            "sourceTree": "<group>",
        }

        return o

    def add_plist_strings(self, locales):
        plist_strs = [self.create_plist_string_file(l) for l in locales]
        variant = self.create_plist_string_variant(plist_strs)

        var_key = Pbxproj.gen_key()
        self.objects[var_key] = variant

        key = Pbxproj.gen_key()
        self.objects[key] = {"isa": "PBXBuildFile", "fileRef": var_key}

        return (var_key, key)

    def add_plist_strings_to_build_phase(self, locales, target_name):
        phase = self.find_resource_build_phase(target_name)
        (var_ref, ref) = self.add_plist_strings(locales)
        phase["files"].append(ref)
        return var_ref

    def find_variant_group(self, target):
        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXVariantGroup"
                and o.get("name", None) == target
            ):
                break
        else:
            raise Exception("No src found.")
        return o

    def set_target_build_setting(self, target, key, value):
        o = self.find_target(target)
        build_cfg_list = self.objects[o["buildConfigurationList"]]
        build_cfgs = [self.objects[x] for x in build_cfg_list["buildConfigurations"]]

        for cfg in build_cfgs:
            cfg["buildSettings"][key] = value

    def set_target_package_id(self, target, new_id):
        o = self.find_target(target)
        build_cfg_list = self.objects[o["buildConfigurationList"]]
        build_cfgs = [self.objects[x] for x in build_cfg_list["buildConfigurations"]]

        for cfg in build_cfgs:
            cfg["buildSettings"]["PRODUCT_BUNDLE_IDENTIFIER"] = new_id

    def add_file_ref_to_variant_group(self, file_ref, variant_name):
        variant = self.find_variant_group(variant_name)
        variant["children"].append(file_ref)
        return variant

    def add_plist_strings_to_variant_group(self, locales, variant_name, target_name):
        variant = self.find_variant_group(variant_name)
        o = []
        for locale in locales:
            ref = self.create_plist_string_file(locale, target_name)
            variant["children"].append(ref)
            o.append(ref)
        return o

    def add_ref_to_group(self, ref, group_list):
        o = self.main_group
        n = False

        for g in group_list:
            for c in o["children"]:
                co = self.objects[c]
                if n:
                    break
                if co.get("path", co.get("name", None)) == g:
                    o = co
                    n = True
            if n:
                n = False
                continue
            else:
                # Create new group
                ref = Pbxproj.gen_key()
                self.objects[ref] = {
                    "isa": "PBXGroup",
                    "children": [],
                    "path": g,
                    "sourceTree": "<group>",
                }
                o["children"].append(ref)
                n = False
                o = self.objects[ref]
                continue

        o["children"].append(ref)
        return True

    def create_file_reference(self, file_type, locale, name, **kwargs):
        o = {
            "isa": "PBXFileReference",
            "lastKnownFileType": file_type,
            "name": locale,
            "path": "%s.lproj/%s" % (locale, name),
            "sourceTree": "<group>",
        }

        o.update(kwargs)

        k = Pbxproj.gen_key()
        self.objects[k] = o
        return k

    def create_plist_file(self, plist_path):
        o = {
            "isa": "PBXFileReference",
            "lastKnownFileType": "text.plist.xml",
            "name": pathlib.Path(plist_path).name,
            "path": plist_path,
            "sourceTree": "<group>",
        }

        k = Pbxproj.gen_key()
        self.objects[k] = o
        return k

    def create_plist_string_file(self, locale, name="InfoPlist.strings"):
        return self.create_file_reference("text.plist.strings", locale, name)

    def create_text_file(self, locale, name):
        return self.create_file_reference("text", locale, name)

    def add_path(self, path_list, target=None):
        if target is None:
            target = self.main_group

        for name in path_list:
            children = [self.objects[r] for r in target["children"]]
            for c in children:
                if c.get("path", None) == name:
                    target = c
                    break
            else:
                ref = Pbxproj.gen_key()

                o = {
                    "children": [],
                    "isa": "PBXGroup",
                    "path": name,
                    "sourceTree": "<group>",
                }

                self.objects[ref] = o
                target["children"].append(ref)
                target = self.objects[ref]

    def clear_target_dependencies(self, target):
        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == target
            ):
                break
        else:
            raise Exception("No src found.")

        # HACK: unclear; leaves dangling nodes
        o["dependencies"] = []

    def clear_target_embedded_binaries(self, target):
        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == target
            ):
                break
        else:
            raise Exception("No src found.")

        target_o = o
        for o in [self.objects[x] for x in target_o["buildPhases"]]:
            if (
                o.get("isa", None) == "PBXCopyFilesBuildPhase"
                and o.get("name", None) == "Embed App Extensions"
            ):
                break
        else:
            raise Exception("No src found.")

        o["files"] = []

    def create_container_item_proxy(self, container_portal, remote_ref, info):
        ref = Pbxproj.gen_key()

        self.objects[ref] = {
            "isa": "PBXContainerItemProxy",
            "containerPortal": container_portal,
            "proxyType": "1",
            "remoteGlobalIDString": remote_ref,
            "remoteInfo": info,
        }

        logger.debug(self.objects[ref])

        return ref

    def create_target_dependency(self, proxy_ref, dep_ref):
        ref = Pbxproj.gen_key()

        self.objects[ref] = {
            "isa": "PBXTargetDependency",
            "targetProxy": proxy_ref,
            "target": dep_ref,
        }
        logger.debug(self.objects[ref])

        return ref

    def add_dependency_to_target(self, target_ref, dep_ref):
        target = self.objects[target_ref]

        if target.get("dependencies", None) is None:
            target["dependencies"] = []

        target["dependencies"].append(dep_ref)
        logger.debug(target)

    def add_appex_to_target_dependencies(self, appex, target):
        logger.debug("%s %s" % (appex, target))
        # Find target
        appex_ref = self.find_ref_for_name(appex, isa="PBXNativeTarget")
        logger.debug("Appex ref: " + appex_ref)

        # Create container proxy
        proxy_ref = self.create_container_item_proxy(
            self._proj["rootObject"], appex_ref, appex
        )
        logger.debug("Proxy ref: " + proxy_ref)

        # Create target dependency
        dep_ref = self.create_target_dependency(proxy_ref, appex_ref)
        logger.debug("Target dep ref: " + dep_ref)

        # Add to deps
        target_ref = self.find_ref_for_name(target, isa="PBXNativeTarget")
        logger.debug(target_ref)
        self.add_dependency_to_target(target_ref, dep_ref)

    def add_appex_to_target_embedded_binaries(self, appex, target):
        for appex_ref, o in self.objects.items():
            if (
                o.get("isa", None) == "PBXFileReference"
                and o.get("path", None) == appex
            ):
                break
        else:
            raise Exception("No appex src found.")

        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == target
            ):
                break
        else:
            raise Exception("No target src found.")

        target_o = o
        for o in [self.objects[x] for x in target_o["buildPhases"]]:
            if (
                o.get("isa", None) == "PBXCopyFilesBuildPhase"
                and o.get("name", None) == "Embed App Extensions"
            ):
                break
        else:
            raise Exception("No src found.")

        ref = Pbxproj.gen_key()
        appex_o = {
            "isa": "PBXBuildFile",
            "fileRef": appex_ref,
            "settings": {"ATTRIBUTES": ["RemoveHeadersOnCopy"]},
        }
        self.objects[ref] = appex_o

        o["files"].append(ref)

    def find_target(self, target):
        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == target
            ):
                return o
        else:
            raise Exception("No src found.")

    def add_source_ref_to_build_phase(self, ref, target):
        target_o = self.find_target(target)

        for o in [self.objects[x] for x in target_o["buildPhases"]]:
            if o.get("isa", None) == "PBXSourcesBuildPhase":
                break
        else:
            raise Exception("No src found.")

        nref = Pbxproj.gen_key()
        self.objects[nref] = {"isa": "PBXBuildFile", "fileRef": ref}

        o["files"].append(nref)

    def remove_target(self, target):
        for ref, o in self.objects.items():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == target
            ):
                break
        else:
            raise Exception("No src found.")
        prod_ref = o["productReference"]
        del self.objects[o["productReference"]]

        for nref, o in self.objects.items():
            if (
                o.get("isa", None) == "PBXBuildFile"
                and o.get("fileRef", None) == prod_ref
            ):
                break
        else:
            raise Exception("No src found.")

        for o in self.objects.values():
            if o.get("isa", None) == "PBXGroup" and o.get("name", None) == "Products":
                break
        else:
            raise Exception("No src found.")

        o["children"].remove(prod_ref)
        self.root["targets"].remove(ref)

    def duplicate_target(self, src_name, dst_name, plist_path):
        for o in self.objects.values():
            if (
                o.get("isa", None) == "PBXNativeTarget"
                and o.get("name", None) == src_name
            ):
                break
        else:
            raise Exception("No src found.")

        base_clone = copy.deepcopy(o)
        base_ref = Pbxproj.gen_key()
        self.objects[base_ref] = base_clone

        new_phases = []
        for phase in base_clone["buildPhases"]:
            ref = Pbxproj.gen_key()
            new_phases.append(ref)
            self.objects[ref] = copy.deepcopy(self.objects[phase])
        base_clone["buildPhases"] = new_phases
        base_clone["name"] = dst_name

        conf_ref = Pbxproj.gen_key()
        conf_clone = copy.deepcopy(self.objects[base_clone["buildConfigurationList"]])
        self.objects[conf_ref] = conf_clone
        base_clone["buildConfigurationList"] = conf_ref

        new_confs = []
        for conf in conf_clone["buildConfigurations"]:
            ref = Pbxproj.gen_key()
            new_confs.append(ref)
            self.objects[ref] = copy.deepcopy(self.objects[conf])

            self.objects[ref]["buildSettings"]["INFOPLIST_FILE"] = plist_path
            self.objects[ref]["buildSettings"]["PRODUCT_NAME"] = dst_name
            self.objects[ref]["buildSettings"]["CODE_SIGN_STYLE"] = "Manual"
            self.objects[ref]["buildSettings"]["ENABLE_BITCODE"] = "NO"
        conf_clone["buildConfigurations"] = new_confs

        appex_ref = Pbxproj.gen_key()
        appex_clone = copy.deepcopy(self.objects[base_clone["productReference"]])
        self.objects[appex_ref] = appex_clone
        appex_clone["path"] = "%s.appex" % dst_name
        base_clone["productReference"] = appex_ref

        # PBXContainerItemProxy etc seem unaffected by leaving dependencies in
        # base_clone['dependencies'] = []

        self.add_ref_to_group(appex_ref, ["Products"])

        self.root["targets"].append(base_ref)
        return base_clone, appex_ref


def generate_osx_mods():
    conv = OrderedDict(
        (
            ("cmd", "command"),
            ("caps", "caps"),
            ("alt", "anyOption"),
            ("shift", "anyShift"),
        )
    )

    def gen_conv(tpl):
        tplo = []
        for t, v in conv.items():
            if t not in tpl:
                v += "?"
            tplo.append(v)
        return tuple(tplo)

    m = ("caps", "alt", "shift")
    mods = (x for i in range(len(m)) for x in itertools.combinations(m, i))

    o = OrderedDict()
    for mod in mods:
        mod = ("cmd",) + mod
        o["osx-%s" % "+".join(mod)] = (" ".join(gen_conv(mod)),)
    return o


class OSXKeyLayout:
    doctype = (
        '<!DOCTYPE keyboard PUBLIC "" '
        + '"file://localhost/System/Library/DTDs/KeyboardLayout.dtd">'
    )
    modes = OrderedDict(
        (
            ("iso-default", ("command?",)),
            ("iso-shift", ("anyShift caps? command?",)),
            ("iso-caps", ("caps",)),
            ("iso-caps+shift", ("caps anyShift",)),
            ("iso-alt", ("anyOption command?",)),
            ("iso-alt+shift", ("anyOption anyShift caps? command?",)),
            ("iso-caps+alt", ("caps anyOption command?",)),
            ("iso-caps+alt+shift", ("caps anyOption anyShift command?",)),
            ("iso-ctrl", ("anyShift? caps? anyOption? anyControl",)),
            ("osx-cmd", ("command",)),
            ("osx-cmd+shift", ("command anyShift",)),
        )
    )
    modes.update(generate_osx_mods())

    # TODO unused
    required = ("iso-default", "iso-shift", "iso-caps")

    DEFAULT_CMD = parse_desktop_layout(
        r"""
        § 1 2 3 4 5 6 7 8 9 0 - =
        q w e r t y u i o p [ ]
        a s d f g h j k l ; ' \
        ` z x c v b n m , . /
    """
    )

    DEFAULT_CMD_SHIFT = parse_desktop_layout(
        r"""
        ± ! @ # $ % ^ & * ( ) _ +
        Q W E R T Y U I O P { }
        A S D F G H J K L : " |
        ~ Z X C V B N M < > ?
    """
    )

    def __bytes__(self):
        """XML almost; still encode the control chars. Death to standards!"""

        # Convert
        v = CP_REGEX.sub(lambda x: "&#x%04X;" % int(x.group(1), 16), str(self))
        v = re.sub(
            r"&(quot|amp|apos|lt|gt);",
            lambda x: {
                "&quot;": "&#x0022;",
                "&amp;": "&#x0026;",
                "&apos;": "&#x0027;",
                "&lt;": "&#x003C;",
                "&gt;": "&#x003E;",
            }[x.group(0)],
            v,
        )
        return ('<?xml version="1.1" encoding="UTF-8"?>\n%s' % v).encode("utf-8")

    def __str__(self):
        root = copy.deepcopy(self.elements["root"])

        actions = root.xpath("actions")[0]
        terminators = root.xpath("terminators")[0]

        if len(actions) == 0:
            root.remove(actions)
        if len(terminators) == 0:
            root.remove(terminators)

        return etree.tostring(
            root, encoding="unicode", doctype=self.doctype, pretty_print=True
        )

    def __init__(self, name, id_):
        modifiers_ref = "modifiers"
        mapset_ref = "default"

        self.elements = {}

        root = Element("keyboard", group="126", id=id_, name=name)
        self.elements["root"] = root

        self.elements["layouts"] = SubElement(root, "layouts")

        SubElement(
            self.elements["layouts"],
            "layout",
            first="0",
            last="17",
            mapSet=mapset_ref,
            modifiers=modifiers_ref,
        )

        self.elements["modifierMap"] = SubElement(
            root, "modifierMap", id=modifiers_ref, defaultIndex="0"
        )

        self.elements["keyMapSet"] = SubElement(root, "keyMapSet", id=mapset_ref)

        self.elements["actions"] = SubElement(root, "actions")

        self.elements["terminators"] = SubElement(root, "terminators")

        self.key_cache = {}
        self.kmap_cache = {}
        self.action_cache = {}

        class KeyIncrementer:
            def __init__(self, prefix):
                self.prefix = prefix
                self.data = {}
                self.c = 0

            def has(self, key):
                return key in self.data

            def get(self, key):
                if self.data.get(key, None) is None:
                    self.data[key] = self.c
                    self.c += 1
                return "%s%03d" % (self.prefix, self.data[key])

        self.states = KeyIncrementer("s")
        self.actions = KeyIncrementer("a")

        self._n = 0

    def _add_modifier_map(self, mode):
        mm = self.elements["modifierMap"]
        kms = self.elements["keyMapSet"]

        node = SubElement(mm, "keyMapSelect", mapIndex=str(self._n))

        mods = self.modes.get(mode, None)
        for mod in mods:
            SubElement(node, "modifier", keys=mod)

        self.kmap_cache[mode] = SubElement(kms, "keyMap", index=str(self._n))
        self._n += 1
        return self.kmap_cache[mode]

    def _get_kmap(self, mode):
        kmap = self.kmap_cache.get(mode, None)
        if kmap is not None:
            return kmap
        return self._add_modifier_map(mode)

    def _set_key(self, mode, key, key_id, action=None, output=None):
        if action is not None and output is not None:
            raise Exception("Cannot specify contradictory action and output.")

        key_key = "%s %s" % (mode, key_id)

        node = self.key_cache.get(key_key, None)

        if node is None:
            kmap_node = self._get_kmap(mode)
            node = SubElement(kmap_node, "key", code=key_id)
            self.key_cache[key_key] = node

        if action is not None:
            node.attrib["action"] = str(action)
            if node.attrib.get("output", None) is not None:
                del node.attrib["output"]
        elif output is not None:
            node.attrib["output"] = str(output)
            if node.attrib.get("action", None) is not None:
                del node.attrib["action"]

    def _set_default_action(self, key):
        action_id = self.actions.get(key)  # "Key %s" % key
        action = self.action_cache.get(action_id, None)

        if action is None:
            action = SubElement(self.elements["actions"], "action", id=action_id)
            self.action_cache[action_id] = action

    def _set_terminator(self, action_id, output):
        termin = self.elements["terminators"].xpath(
            'when[@state="%s"]' % action_id.replace('"', r"&quot;")
        )

        if len(termin) == 0:
            el = SubElement(self.elements["terminators"], "when")
            el.set("state", action_id)
            el.set("output", output)

    def _set_default_transform(self, action_id, output):
        action = self.action_cache.get(action_id, None)

        # TODO create a generic create or get method for actions
        if action is None:
            logger.trace(
                "Create default action - action:%r output:%r" % (action_id, output)
            )
            action = SubElement(self.elements["actions"], "action", id=action_id)
            self.action_cache[action_id] = action

        if len(action.xpath('when[@state="none"]')) == 0:
            logger.trace(
                "Create 'none' when - action:%r output:%r" % (action_id, output)
            )
            el = SubElement(action, "when")
            el.set("state", "none")
            el.set("output", output)

    def set_key(self, mode, key, key_id):
        self._set_key(mode, key, key_id, output=key)

    def set_deadkey(self, mode, key, key_id, output):
        """output is the output when the deadkey is followed by an invalid"""
        logger.trace("%r %r %r %r" % (mode, key, key_id, output))
        action_id = self.actions.get(key)  # "Key %s" % key
        pressed_id = self.states.get(key)  # "State %s" % key

        self._set_key(mode, key, key_id, action=action_id)

        # Create default action (set to pressed state)
        self._set_default_action(key)
        self._set_terminator(pressed_id, output)

    def set_transform_key(self, mode, key, key_id):
        action_id = self.actions.get(key)  # "Key %s" % key

        self._set_key(mode, key, key_id, action=action_id)

        # Find action, add none state (move the output)
        self._set_default_transform(action_id, key)

    def add_transform(self, action_id, state, output=None, next=None):
        action = self.action_cache.get(action_id, None)

        if action is None:
            raise Exception("'%s' was not a found action_id." % action_id)

        if output is not None and next is not None:
            raise Exception("Output and next cannot be simultaneously defined.")

        if output is not None:
            el = SubElement(action, "when")
            el.set("state", state)
            el.set("output", output)
        elif next is not None:
            el = SubElement(action, "when")
            el.set("state", state)
            el.set("next", next)
        # logger.trace("%r" % el)
