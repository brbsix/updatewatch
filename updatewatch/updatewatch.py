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


def action_default(options):
    """Poll for new updates."""
    LOG.debug('running action_default')
    config = configuration.populate(options.application)
    updates = get_updates(options.updates)
    LOG.debug('updates: %s', updates)

    # check for updates
    results = check(updates)

    # compare results with cache and store changes
    data = get_data(results, options.database, updates)

    reporters.show_new(data)
    mailer.email_new(data, config.get('email'))


def action_list(options):
    """List available updates."""
    LOG.debug('running action_list')
    config = configuration.populate(options.application)
    updates = get_updates(options.updates)
    LOG.debug('updates: %s', updates)

    # check for updates
    results = check(updates)

    # determine whether to notify upon results
    try:
        notify = config['notify']['enabled']
    except KeyError:
        notify = False

    reporters.show_all(results, notify)


def action_list_from_cache(options):
    """List available updates from cache."""
    LOG.debug('running action_list_from_cache')
    updates = get_updates(options.updates)
    LOG.debug('updates: %s', updates)
    cache = get_cache(options.database, updates)
    reporters.show_all(cache)


def action_run_from_cache(options):
    """List new updates from cache."""
    LOG.debug('running action_run_from_cache')
    updates = get_updates(options.updates)
    LOG.debug('updates: %s', updates)
    cache = get_cache(options.database, updates)
    reporters.show_new(cache)


def action_set_password(options):
    """Set email account password."""
    LOG.debug('running action_set_password')
    config = configuration.populate(options.application)
    mailer.set_password(config['email'])


def check(updates):
    """Check for updates and return the results as a generator of processes."""
    processes = [execute(**u) for u in updates]

    # start the processes
    for process in processes:
        next(process)

    return (next(p) for p in processes)


def difference(current, previous):
    """Compare new information with old information."""
    if previous is None:
        previous = make_default()

    LOG.debug('processing current: %s', current['description'])
    LOG.debug('processing previous: %s', previous['description'])

    # find the difference between two sets
    new = set(current['stdout']) - set(previous['stdout'])

    LOG.debug('new is %s', new)
    current['new'] = new

    # preserve stdout of previous result if update check experiences
    # and error and has no output
    # Note: this won't be displayed by any reporters because new is empty
    if (current['stderr'] or current['status'] != 0) and \
            not current['stdout'] and previous['stdout']:
        LOG.debug('preserving previous stdout: %s', previous['stdout'])
        current['stdout'] = previous['stdout']

    return current


def difference_list(current, previous):
    """Compare list of new information with list of old information."""
    return [difference(c, p) for c, p in
            itertools.zip_longest(current, previous)]


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


def get_action(options):
    """Return the appropriate function."""
    if options.set_password:
        return action_set_password
    elif options.list:
        return action_list
    elif options.list_from_cache:
        return action_list_from_cache
    elif options.run_from_cache:
        return action_run_from_cache
    else:
        return action_default


def get_cache(path, updates):
    """Get previous results from cache."""
    with shelve.open(path) as database:

        # get hash of updates dictionary
        key = get_hash(updates)
        LOG.debug('current key is %s', key)

        # print keys of all pre-existing entries stored in DB
        LOG.debug('previous keys: %s', list(database))

        # get pre-existing entry stored in DB
        previous = database.get(key, [])
        LOG.debug('previous is %s', previous)

        return previous


def get_data(results, path, updates):
    """Get latest data, compare it to previous data, then shelve the result."""
    with shelve.open(path) as database:

        # get hash of updates dictionary to check whether it has changed
        key = get_hash(updates)
        LOG.debug('current key is %s', key)

        # print keys of all pre-existing entries stored in DB
        LOG.debug('previous keys: %s', list(database))

        # get pre-existing entry stored in DB
        previous = database.get(key, [])
        LOG.debug('previous is %s', previous)

        data = difference_list(results, previous)

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
    configuration.initialize_logging(options.logfile, options.loglevel)

    LOG.debug('options: %s', options)

    # determine the appropriate action
    action = get_action(options)

    LOG.debug('action: %s', action)

    # run the action
    action(options)

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
            try:
                match = re.match(
                    r'(?P<package>\S+)\s+(?P<current>\S+)\s+(?P<wanted>\S+)\s+'
                    r'(?P<latest>\S+)(\s+(?P<location>\S+))?', clean_line
                ).groupdict()
            except AttributeError:
                continue
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
