#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Poll for new updates"""

# standard imports
import hashlib
import itertools
import logging
import os
import pickle
import re
import shelve
import subprocess
import sys
from distutils.version import StrictVersion
from tempfile import gettempdir
from textwrap import dedent

# external imports
import yaml

# application imports
from . import __program__
from . import configuration, mailer, reporters


def check(updates):
    """Check for updates and return the results as a generator of processes."""
    processes = [execute(**u) for u in updates]

    # start the processes
    for process in processes:
        next(process)

    return (next(p) for p in processes)


def difference(new, old):
    """Compare new update information with old information."""
    data = []
    for current, previous in itertools.zip_longest(new, old):
        if previous is None:
            previous = make_default()

        LOG.debug('processing current: %s', current['description'])
        LOG.debug('processing previous: %s', previous['description'])

        # find the difference between two sets
        new = set(current['stdout']) - set(previous['stdout'])

        LOG.debug('new is %s', new)

        # update the record only if there are new updates or an update poll
        # has been performed without error
        if new or not current['stderr']:
            if new:
                LOG.debug('current record has new updates (%s)', new)
            elif not current['stderr']:
                LOG.debug('current record has no errors')
            LOG.debug('updating record')
            current['new'] = new
            data.append(current)
        else:
            LOG.debug('skipping record')
            previous['description'] = current['description']
            # be sure to wipe the old set before adding it to the data
            previous['new'] = set()
            data.append(previous)

    return data


def execute(description, command, timeout='3m'):
    """Check for updates."""

    # be sure to dedent before inserting command
    cmd = dedent("""\
        timeout {} bash <<EOF
        %s
        EOF""".format(timeout)) % command

    LOG.debug('cmd: %s', repr(cmd))

    with subprocess.Popen(cmd,
                          cwd=gettempdir(),
                          executable='bash',
                          preexec_fn=lambda: os.nice(19),
                          shell=True,
                          stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          universal_newlines=True) as process:
        yield None

        stdout, stderr = process.communicate()
        status = process.wait()
        yield make_result(description, stdout, stderr, status)


def get_data(results, path, updates):
    """Get latest data, compare it to previous data, then shelve the result."""
    with shelve.open(path) as database:

        # get hash of updates file to check whether it has changed
        key = get_hash(updates)
        LOG.debug('current key is %s', key)

        # print keys of all pre-existing entries stored in DB
        LOG.debug('existing keys: %s', list(database))

        # get pre-existing entry stored in DB
        existing = database.get(key, [])
        LOG.debug('existing is %s', existing)

        data = difference(results, existing)

        # write to database
        LOG.debug('updating database')
        database[key] = data

        return data


def get_hash(item):
    """Return the sha1 hash of an object."""

    return hashlib.sha1(pickle.dumps(hashablize(item))).hexdigest()


def get_updates(path):
    """Return list of updates from YAML document."""
    with open(path) as file:
        return list(yaml.load_all(file))


def hashablize(obj):
    """
    Convert a container hierarchy into one that can be hashed.

    Don't use this with recursive structures!
    Also, this won't be useful if you pass dictionaries with
    keys that don't have a total order.
    Actually, maybe you're best off not using this function at all.

    http://stackoverflow.com/a/985369/4117209
    """
    try:
        hash(obj)
    except TypeError:
        if isinstance(obj, dict):
            return tuple(
                (k, hashablize(v)) for (k, v) in sorted(obj.items()))
        elif hasattr(obj, '__iter__'):
            return tuple(hashablize(o) for o in obj)
        else:
            raise TypeError(
                "Can't hashablize object of type %r" % type(obj))
    else:
        return obj


def main(args=None):
    """Start application."""

    # parse command-line arguments into options
    options = configuration.parse_args(args)

    # configure logging
    # _scriptlogger(options.logfile, options.loglevel)
    configuration.initlogger(options.logfile, options.loglevel)

    LOG.debug('options: %s', options)

    config = configuration.populate(options.application)

    if options.set_password:
        LOG.debug('running mailer.set_password')
        mailer.set_password(config.get('email'))
        sys.exit(0)

    updates = get_updates(options.updates)
    LOG.debug('updates: %s', updates)

    results = check(updates)

    if options.list:
        try:
            notify = config['notify']['enabled']
        except KeyError:
            notify = False
        LOG.debug('running reporters.show_all %s notify',
                  'with' if notify else 'without')
        reporters.show_all(results, notify)
        sys.exit(0)
    else:
        data = get_data(results, options.database, updates)

        LOG.debug('running reporters.show_new')
        reporters.show_new(data)

        LOG.debug('running mailer.email_new')
        mailer.email_new(data, config.get('email'))
        sys.exit(0)


def make_default():
    """Return default result."""

    return {
        'description': '',
        'header': None,
        'new': set(),
        'status': 0,
        'stderr': [],
        'stdout': []
    }


def make_result(description, stdout, stderr, status):
    """Return result of update check."""

    LOG.debug('description: %s', repr(description))
    LOG.debug('stdout: %s', repr(stdout))
    LOG.debug('stderr: %s', repr(stderr))
    LOG.debug('status: %d', status)

    header = None
    stdout = stdout.strip().splitlines()
    stderr = stderr.strip().splitlines()

    LOG.debug('stdout.strip().splitlines(): %s', stdout)
    LOG.debug('stderr.strip().splitlines(): %s', stderr)

    if status == 124:
        LOG.debug('command timed out')
        stderr.append('ERROR: command timed out')

    # handle Node.js differently due to it's column headers,
    # colored output, and propensity for displaying modules
    # that are not actually outdated
    if description == 'Node.js modules':
        header, stdout = modifier_node_js(stdout)

    return {
        'description': description,
        'header': header,
        'new': set(),
        'status': status,
        'stderr': stderr,
        'stdout': stdout
    }


def modifier_node_js(stdout):
    """Return the header and modules for Node.js results."""

    LOG.debug('preparing Node.js modules')

    header = None
    modules = []

    LOG.debug('len(stdout): %d', len(stdout))

    if len(stdout) >= 1:
        header = stdout[0]
        LOG.debug('Node.js header: %s', repr(header))

    if len(stdout) >= 2:
        all_module_lines = stdout[1:]
        LOG.debug('Node.js all_module_lines: %s', all_module_lines)
        for module_line in all_module_lines:
            LOG.debug('Node.js module_line: %s', repr(module_line))
            clean_line = reporters.Terminal.clean(module_line)
            LOG.debug('clean_line: %s', clean_line)
            match = re.match(
                r'(?P<package>\S+)\s+(?P<current>\S+)\s+(?P<wanted>\S+)\s+'
                r'(?P<latest>\S+)(\s+(?P<location>\S+))?', clean_line
            ).groupdict()
            package = match['package']
            LOG.debug('Node.js package: %s', package)
            current = match['current']
            LOG.debug('Node.js current: %s', current)
            wanted = match['wanted']
            LOG.debug('Node.js wanted: %s', wanted)
            # check whether the package is actually outdated
            if StrictVersion(current) < StrictVersion(wanted):
                LOG.debug("Node.js package '%s' is wanted", package)
                modules.append(module_line)

    return header, modules


LOG = logging.getLogger(__program__)

if __name__ == '__main__':
    main()
