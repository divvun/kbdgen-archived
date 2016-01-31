import itertools
import os
import os.path
import random
import re
import subprocess

from collections import OrderedDict

from ..base import ISO_KEYS

class MissingApplicationException(Exception): pass

def bind_iso_keys(other):
    return OrderedDict(((k, v) for k, v in zip(ISO_KEYS, other)))

class Generator:
    def __init__(self, project, args=None):
        self._project = project
        self._args = args or {}

    @property
    def repo(self):
        return self._args.get('repo', None)

    @property
    def branch(self):
        return self._args.get('branch', 'stable')

    @property
    def is_release(self):
        return self._args.get('release', False)

    @property
    def dry_run(self):
        return self._args.get('dry_run', False)

class PhysicalGenerator(Generator):
    @classmethod
    def validate_layout(cls, data):
        # TODO finish cls-based validate_layout
        pass

class TouchGenerator(Generator):
    @classmethod
    def validate_layout(cls, data):
        return True

def mode_iter(keyboard, key, required=False):
    mode = keyboard.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("Layout '%s' has a required mode: '%s'." % (keyboard.internal_name, key))
        return itertools.repeat(None)

    return mode.values()

def mode_dict(keyboard, key, required=False, space=False):
    mode = keyboard.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("Layout '%s' has a required mode: '%s'." % (keyboard.internal_name, key))
        return OrderedDict(zip(ISO_KEYS, itertools.repeat(None)))

    if space:
        sp = keyboard.special.get('space', {}).get(key, " ")
        mode['A03'] = sp
    return mode

def git_update(dst, branch, clean, cwd='.', logger=print):
    msg = "Updating repository '%s'..." % dst
    logger(msg)

    cmd = """git reset --hard;
             git fetch --all;
             git checkout %s;
             %s
             git pull;
             git submodule init;
             git submodule sync;
             git submodule update;""" % (
                branch,
                "git clean -fdx;" if clean else ""
            )

    cwd = os.path.join(cwd, dst)

    process = subprocess.Popen(cmd, cwd=cwd, shell=True)
    process.wait()

def git_clone(src, dst, branch, clean, cwd='.', logger=print):
    msg = "Cloning repository '%s' to '%s'..." % (src, dst)
    logger(msg)

    cmd = ['git', 'clone', src, dst]

    process = subprocess.Popen(cmd, cwd=cwd)
    process.wait()

    # Silence logger for update.
    git_update(dst, branch, cwd, logger=lambda x: None)

def iterable_set(iterable):
    return {i for i in itertools.chain.from_iterable(iterable)}

def random_id():
    return str(-random.randrange(1, 32768))

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
                    yield self.on_branch(tuple(buf), k)
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
        for _ in self: pass
