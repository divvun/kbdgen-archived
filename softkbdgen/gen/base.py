import itertools
import os
import os.path
import random
import re
import subprocess

from collections import OrderedDict

class MissingApplicationException(Exception): pass

ISO_KEYS = ( "E00",
    "E01", "E02", "E03", "E04", "E05", "E06",
    "E07", "E08", "E09", "E10", "E11", "E12",
    "D01", "D02", "D03", "D04", "D05", "D06",
    "D07", "D08", "D09", "D10", "D11", "D12",
    "C01", "C02", "C03", "C04", "C05", "C06", # TODO fix the D13 special case.
    "C07", "C08", "C09", "C10", "C11", "D13", # C12 -> D13
    "B00", "B01", "B02", "B03", "B04", "B05",
    "B06", "B07", "B08", "B09", "B10" )

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

# TODO create proper layout class with .list and .dict props.
def mode_iter(layout, key, required=False, fallback=None):
    mode = layout.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("'%s' has a required mode." % key)
        return itertools.repeat(fallback)

    if isinstance(mode, dict):
        def wrapper():
            for iso in ISO_KEYS:
                yield mode.get(iso, fallback)
        return wrapper()
    else:
        return itertools.chain.from_iterable(mode)

def mode_dict(layout, key, required=False, space=False):
    mode = layout.modes.get(key, None)
    if mode is None:
        if required:
            raise Exception("'%s' has a required mode." % key)
        return {}

    sp = layout.special.get('space', {}).get(key, " ")

    if isinstance(mode, dict):
        mode['A03'] = sp
        return mode

    mode = OrderedDict(zip(ISO_KEYS,
        itertools.chain.from_iterable(mode)))
    mode['A03'] = sp
    return mode

def git_clone(src, dst, branch, cwd='.'):
    print("Cloning repository '%s' to '%s'..." % (src, dst))

    cmd = ['git', 'clone', src, dst]

    process = subprocess.Popen(cmd, cwd=cwd)
    process.wait()

    git_update(dst, branch, cwd)


def git_update(dst, branch, cwd='.'):
    print("Updating repository '%s'..." % dst)

    cmd = """git reset --hard;
             git checkout %s;
             git clean -fdx;
             git pull;""" % branch

    cwd = os.path.join(cwd, dst)

    process = subprocess.Popen(cmd, cwd=cwd, shell=True)
    process.wait()

def iterable_set(iterable):
    return {i for i in itertools.chain.from_iterable(iterable)}

def random_id():
    return str(-random.randrange(1, 32768))

