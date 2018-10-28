import itertools
import logging
import os
import os.path
import subprocess
import sys

from functools import lru_cache
from collections import OrderedDict

from ..base import ISO_KEYS, KbdgenException

logger = logging.getLogger()


class MissingApplicationException(KbdgenException):
    pass


class GenerationError(KbdgenException):
    pass


def bind_iso_keys(other):
    return OrderedDict(((k, v) for k, v in zip(ISO_KEYS, other)))


class Generator:
    def __init__(self, project, args=None):
        self._project = project
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

    @property
    @lru_cache(maxsize=1)
    def supported_layouts(self):
        t = self._args["target"]
        o = OrderedDict()
        for k, v in self._project.layouts.items():
            if v.supported_target(t):
                o[k] = v
        return o

    def sanity_check(self) -> bool:
        if len(self.supported_layouts) == 0:
            logger.error("This project defines no supported layouts for this target.")
            return False
        else:
            logger.debug("Supported layouts: %s" % ", ".join(self.supported_layouts))

        return True


class PhysicalGenerator(Generator):
    def validate_layout(self, layout):
        # TODO finish cls-based validate_layout
        mode_keys = set(layout.modes.keys())
        deadkey_keys = set(layout.dead_keys.keys())

        undefined_modes = deadkey_keys - mode_keys

        if len(undefined_modes) > 0:
            raise Exception(
                "Dead key modes are defined for undefined modes: %r"
                % (list(undefined_modes),)
            )

        for mode, keys in layout.dead_keys.items():
            dead_keys = set(keys)
            layer_keys = set(layout.modes[mode].values())

            matched_keys = dead_keys & layer_keys

            if matched_keys != dead_keys:
                raise Exception(
                    "Specified dead keys missing from mode %r: %r"
                    % (mode, list(dead_keys - matched_keys))
                )


class TouchGenerator(Generator):
    def validate_layout(self):
        pass


MSG_LAYOUT_MISSING = "Layout '%s' is missing a required mode: '%s'."


def mode_iter(keyboard, key, required=False):
    mode = keyboard.modes.get(key, None)
    if mode is None:
        if required:
            raise GenerationError(MSG_LAYOUT_MISSING % (keyboard.internal_name, key))
        return itertools.repeat(None)

    return mode.values()


def mode_dict(keyboard, key, required=False, space=False):
    mode = keyboard.modes.get(key, None)
    if mode is None:
        if required:
            raise GenerationError(MSG_LAYOUT_MISSING % (keyboard.internal_name, key))
        return OrderedDict(zip(ISO_KEYS, itertools.repeat(None)))

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


def run_process(cmd, cwd=None, show_output=False):
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd is not None else None,
            stderr=None if show_output else subprocess.PIPE,
            stdout=None if show_output else subprocess.PIPE,
        )
    except Exception as e:
        logger.error("Process failed to launch with the following error message:")
        logger.error(e)
        sys.exit(1)

    if show_output:
        process.wait()
        return None, None
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
