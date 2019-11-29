import itertools
import logging
import os
import os.path
import subprocess
import sys
import re
import io

from functools import lru_cache
from collections import OrderedDict

from . import bin as resources
from ..base import ISO_KEYS, KbdgenException

logger = logging.getLogger()

# Parses "\s{foo:42.12}", "\s{foo}" and "\{foo:42}"
RE_SPECIAL_KEY = re.compile(r"^\\s{([^}:]+)(?::(\d+(?:\.\d+)?))?}$")


class MissingApplicationException(KbdgenException):
    pass


class GenerationError(KbdgenException):
    pass


def get_bin_resource(res, text=False):
    o = resources.__loader__.open_resource(res)
    if text:
        return io.TextIOWrapper(o)
    return o


def bind_iso_keys(other):
    return OrderedDict(((k, v) for k, v in zip(ISO_KEYS, other)))


def interpret_special_keys(rows):
    # Parse out all the \s keys
    for row in rows:
        for (n, key) in enumerate(row):
            match = RE_SPECIAL_KEY.match(key)
            if match is not None:
                (id_, width) = match.groups()
                if width is None:
                    width = 1.0
                else:
                    width = float(width)

                if id_.startswith('"') and id_.endswith('"'):
                    id_ = id_[1:-1]
                else:
                    id_ = "_%s" % id_
                row[n] = {"id": id_, "width": width}


class MobileLayoutView:
    def __init__(self, layout, target):
        self._layout = layout
        self._target = target

    def mode(self, mode):
        o = {}
        o.update(self._layout.modes.get("mobile", {}))
        o.update(self._layout.modes.get(self._target, {}))
        rows = o.get(mode, None)
        if rows is None:
            return None
        interpret_special_keys(rows)
        return rows

    def modes(self):
        o = {}
        o.update(self._layout.modes.get("mobile", {}))
        o.update(self._layout.modes.get(self._target, {}))
        return o

    def dead_keys(self):
        o = {}
        if self._layout.dead_keys is None:
            return o
        o.update(self._layout.dead_keys.get("mobile", {}))
        o.update(self._layout.dead_keys.get(self._target, {}))
        return o


class TabletLayoutView:
    def __init__(self, layout, target):
        self._layout = layout
        self._target = target

    def mode(self, mode):
        o = {}
        o.update(self._layout.modes.get(self._target, {}))
        rows = o.get(mode, None)
        if rows is None:
            return []
        interpret_special_keys(rows)
        return rows

    def modes(self):
        o = {}
        o.update(self._layout.modes.get(self._target, {}))
        return o


class DesktopLayoutView:
    def __init__(self, layout, target):
        self._layout = layout
        self._target = target

    def mode(self, mode):
        return self.modes().get(mode, None)

    def modes(self):
        o = {}
        o.update(self._layout.modes.get("desktop", {}))
        o.update(self._layout.modes.get(self._target, {}))
        return o

    def dead_keys(self):
        o = {}
        if self._layout.dead_keys is None:
            return o
        o.update(self._layout.dead_keys.get("desktop", {}))
        o.update(self._layout.dead_keys.get(self._target, {}))
        return o

    def space(self):
        o = {}
        if self._layout.space is None:
            return o
        o.update(self._layout.space.get("desktop", {}))
        o.update(self._layout.space.get(self._target, {}))
        return o


class Generator:
    def __init__(self, bundle, args=None):
        self._bundle = bundle
        self._args = args or {}

    @property
    def repo(self):
        return self._args.get("repo", None)

    @property
    def branch(self):
        return self._args.get("branch", "master")

    @property
    def is_release(self):
        return self._args.get("release", False)

    @property
    def dry_run(self):
        return self._args.get("dry_run", False)

    @property
    def output_dir(self):
        return self._args.get("output", ".")

    def satisfies_requirements(self) -> bool:
        # if len(self.supported_layouts) == 0:
        #     logger.error("This project defines no supported layouts for this target.")
        #     return False
        # else:
        #     logger.debug("Supported layouts: %s" % ", ".join(self.supported_layouts))

        return True


class PhysicalGenerator(Generator):
    def validate_layout(self, layout, target):
        view = DesktopLayoutView(layout, target)

        mode_keys = set(view.modes().keys())
        deadkey_keys = set(view.dead_keys().keys())

        print(mode_keys)

        undefined_modes = deadkey_keys - mode_keys

        if len(undefined_modes) > 0:
            # raise Exception(
            #     "Dead key modes are defined for undefined modes: %r"
            #     % (list(undefined_modes),)
            # )
            logger.warn(
                "Dead key modes are defined for undefined modes: %r"
                % (list(undefined_modes),)
            )

        for mode, keys in view.dead_keys().items():
            dead_keys = set(keys)
            layer_keys = set(view.modes()[mode].values())

            logger.trace("Dead: %r, layer: %r" % (dead_keys, layer_keys))

            matched_keys = dead_keys & layer_keys

            if matched_keys != dead_keys:
                raise Exception(
                    "Specified dead keys missing from mode %r: %r"
                    % (mode, list(dead_keys - matched_keys))
                )


class MobileGenerator(Generator):
    def validate_layout(self):
        pass


MSG_LAYOUT_MISSING = "Layout '%s' is missing a required mode: '%s'."


def mode_iter(locale, keyboard, key, target, required=False):
    mode = DesktopLayoutView(keyboard, target).mode(key)
    if mode is None:
        if required:
            raise GenerationError(MSG_LAYOUT_MISSING % (locale, key))
        return itertools.repeat(None)

    return mode.values()


def mode_dict(locale, keyboard, key, target, required=False, space=False):
    mode = DesktopLayoutView(keyboard, target).mode(key)
    if mode is None:
        if required:
            raise GenerationError(MSG_LAYOUT_MISSING % (locale, key))
        return OrderedDict(zip(ISO_KEYS, itertools.repeat(None)))

    # TODO this isn't handled properly yet
    if space:
        sp = keyboard.special.get("space", {}).get(key, " ")
        mode["A03"] = sp
    return mode


def git_update(dst, branch, clean, cwd=".", logger=print):
    msg = "Updating repository '%s'…" % dst
    logger(msg)

    cmd = """git reset --hard &&
             git fetch --all &&
             git checkout %s &&
             %s
             git pull &&
             git submodule init &&
             git submodule sync &&
             git submodule update""" % (
        branch,
        "git clean -fdx &&" if clean else "",
    )
    cmd = cmd.replace("\n", " ")

    cwd = os.path.join(cwd, dst)

    # TODO error checking
    process = subprocess.Popen(cmd, cwd=cwd, shell=True)
    process.wait()


def git_clone(src, dst, branch, clean, cwd=".", logger=print):
    msg = "Cloning repository '%s' to '%s'…" % (src, dst)
    logger(msg)

    cmd = ["git", "clone", src, dst]

    # TODO error checking
    process = subprocess.Popen(cmd, cwd=cwd)
    process.wait()

    # Silence logger for update.
    git_update(dst, branch, cwd, logger=lambda x: None)


def iterable_set(iterable):
    return {i for i in itertools.chain.from_iterable(iterable)}


def filepath(fp, *args):
    return os.path.join(os.path.dirname(fp), *args)


class DictWalker:
    def on_branch(self, base, branch):
        return base, branch

    def on_leaf(self, base, branch, leaf):
        return base, branch, leaf

    def __init__(self, dict_):
        self._dict = dict_

    def __iter__(self):
        def walk(dict_, buf):
            for k, v in dict_.items():
                if isinstance(v, dict):
                    c = yield self.on_branch(tuple(buf), k)
                    if c is False:
                        continue
                    nbuf = buf[:]
                    nbuf.append(k)
                    for vv in walk(v, nbuf):
                        yield vv
                elif isinstance(v, (int, str)):
                    yield self.on_leaf(tuple(buf), k, v)
                else:
                    raise TypeError(v)

        for v in walk(self._dict, []):
            yield v

    def __call__(self):
        # Run iterator to death
        for _ in self:
            pass


def run_process(
    cmd,
    cwd=None,
    env=os.environ,
    show_output=False,
    return_process=False,
    shell=False,
    pipe=None,
):
    logger.trace("%r cwd=%r" % (cmd, cwd))
    try:
        process = subprocess.Popen(
            cmd,
            shell=shell,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            stderr=None if show_output else subprocess.PIPE,
            stdout=None if show_output else subprocess.PIPE,
            stdin=None if pipe is None else subprocess.PIPE,
        )
        if pipe is not None:
            process.stdin.write(pipe)
    except Exception as e:
        logger.error("Process failed to launch with the following error message:")
        logger.error(e)
        sys.exit(1)

    if return_process:
        return process

    if show_output:
        process.wait()
        return process.returncode
    else:
        out, err = process.communicate()

        if process.returncode != 0:
            x = err.decode()
            if x.strip() == "":
                x = out.decode()
            logger.error(x)
            logger.error("Application ended with error code %s." % (process.returncode))
            sys.exit(process.returncode)

        return out, err
