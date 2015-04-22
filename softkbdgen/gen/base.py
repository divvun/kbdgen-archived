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

def mode_iter(layout, key, required=False):
    mode = layout.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("'%s' has a required mode." % key)
        return itertools.repeat(None)

    return mode.values()

def mode_dict(layout, key, required=False, space=False):
    mode = layout.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("'%s' has a required mode." % key)
        return OrderedDict(zip(ISO_KEYS, itertools.repeat(None)))

    if space:
        sp = layout.special.get('space', {}).get(key, " ")
        mode['A03'] = sp
    return mode

def git_update(dst, branch, cwd='.', logger=print):
    msg = "Updating repository '%s'..." % dst
    logger(msg)

    cmd = """git reset --hard;
             git checkout %s;
             git clean -fdx;
             git pull;""" % branch

    cwd = os.path.join(cwd, dst)

    process = subprocess.Popen(cmd, cwd=cwd, shell=True)
    process.wait()

def git_clone(src, dst, branch, cwd='.', logger=print):
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

