#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Poll for new updates"""

# standard imports
import argparse
import hashlib
import itertools
import logging
import os
import pickle
import shelve
import subprocess
import sys
from distutils.version import StrictVersion

# external imports
import appdirs
import yaml

# application imports
from . import __program__, __version__
from . import mailer, reporters


class Config:  # pylint: disable=too-few-public-methods
    """Store global script configuration values."""

    def __init__(self, directory):
        self.application = os.path.join(directory, __program__ + '.yaml')
        self.database = os.path.join(directory, __program__ + '.db')
        self.logfile = os.path.join(directory, __program__ + '.log')
        self.updates = os.path.join(directory, 'updates.yaml')


def _scriptlogger(logfile=None, loglevel=logging.WARNING):
    """Configure program logger."""

    scriptlogger = logging.getLogger(__program__)

    # ensure logger is not reconfigured
    if not scriptlogger.hasHandlers():

        # set log level
        scriptlogger.setLevel(loglevel)

        fmt = '%(levelname)s: %(message)s'

        # configure terminal log
        streamhandler = logging.StreamHandler()
        streamhandler.setFormatter(logging.Formatter(fmt))
        scriptlogger.addHandler(streamhandler)

        # configure log file (if necessary)
        if logfile is not None:
            fileformatter = logging.Formatter('%(asctime)s.%(msecs)03d ' + fmt,
                                              '%Y-%m-%d %H:%M:%S')
            filehandler = logging.FileHandler(logfile)
            filehandler.setFormatter(fileformatter)
            scriptlogger.addHandler(filehandler)


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


# def difference(new, old):
#     """Compare new update information with old information."""
#     data = []
#     for current, previous in itertools.zip_longest(new, old):
#         LOG.debug('processing current: %s', current['description'])
#         LOG.debug('processing previous: %s', previous['description']
#                   if previous is not None else previous)

#         # find the difference between two sets
#         new = set(current['stdout']) - \
#             set([] if previous is None else previous['stdout'])

#         LOG.debug('new is %s', new)

#         # update the record only if there are new updates or an update poll
#         # has been performed without error
#         if new or not current['stderr']:
#             if new:
#                 LOG.debug('current record has new updates (%s)', new)
#             elif not current['stderr']:
#                 LOG.debug('current record has no errors')
#             LOG.debug('updating record')
#             current['new'] = new
#             data.append(current)
#         else:
#             LOG.debug('skipping record')
#             # be sure to wipe the old set before adding it to the data
#             try:
#                 previous['new'] = set()
#             except TypeError:
#                 pass
#             data.append(previous)

#     return data


def execute(description, command):
    """
    Check for updates.

    >>> result = execute('sample update', 'echo output; echo error >&2')
    >>> next(result)
    >>> next(result) == {'description': 'sample update', \
                         'header': None, \
                         'new': set(), \
                         'status': 0, \
                         'stderr': ['error'], \
                         'stdout': ['output'] }
    True

    >>> result = execute('sample update', 'echo something; exit 3')
    >>> next(result)
    >>> next(result) == {'description': 'sample update', \
                         'header': None, \
                         'new': set(), \
                         'status': 3, \
                         'stderr': [], \
                         'stdout': ['something'] }
    True
    """

    with subprocess.Popen('timeout 3m %s' % command,
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


def get_data(results, config, updates):
    """Get latest data, compare it to previous data, then shelve the result."""
    with shelve.open(config.database) as database:

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
    """
    Return the sha1 hash of an object.

    >>> get_hash([1, 2, 3])
    '28e379c2b3c22a61bdf6f4f52036ccb3c4d2e968'
    """

    return hashlib.sha1(pickle.dumps(hashablize(item))).hexdigest()


def get_updates(path):
    """Return list of updates from configuration file."""
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

    >>> hashablize([1, 2, 3])
    (1, 2, 3)

    >>> hashablize({'key': 'value', 'otherkey': 'othervalue'})
    (('key', 'value'), ('otherkey', 'othervalue'))

    >>> hashablize([{'keyA': 'valueA'}, {'keyB': 'valueB'}])
    ((('keyA', 'valueA'),), (('keyB', 'valueB'),))
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
    options = parse_args(args)

    # if no application directory has been set, configure a default
    # and create the directory if none exists
    if options.directory is None:
        options.directory = appdirs.user_config_dir(__program__)
        os.makedirs(options.directory, exist_ok=True)

    config_paths = Config(options.directory)

    # configure logging
    logfile = config_paths.logfile if options.logfile is None else None if \
        options.logfile is False else options.logfile
    loglevel = logging.DEBUG if options.debug else logging.WARNING
    _scriptlogger(logfile, loglevel)

    LOG.debug('options: %s', options)
    LOG.debug('config: %s', config_paths)

    # populate the application's configuration file with a default
    # if none exists
    config_file = populate(config_paths.application)

    if options.set_password:
        LOG.debug('running mailer.set_password')
        mailer.set_password(config_file.get('email'))
        sys.exit(0)

    updates = get_updates(config_paths.updates)
    LOG.debug('updates: %s', updates)

    results = check(updates)

    if options.list:
        try:
            notify = config_file['notify']['enabled']
        except KeyError:
            notify = False
        LOG.debug('running reporters.show_all %s notify',
                  'with' if notify else 'without')
        reporters.show_all(results, notify)
        sys.exit(0)
    else:
        data = get_data(results, config_paths, updates)

        LOG.debug('running reporters.show_new')
        reporters.show_new(data)

        LOG.debug('running mailer.email_new')
        mailer.email_new(data, config_file.get('email'))
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


# def make_default(description=None,
#                  header=None,
#                  new=None,
#                  status=None,
#                  stderr=None,
#                  stdout=None):
#     """Create and return default result."""

#     return {
#         'description': '' if description is None else description,
#         'header': None if header is None else header,
#         'new': set() if new is None else new,
#         'status': 0 if status is None else status,
#         'stderr': [] if stderr is None else stderr,
#         'stdout': [] if stdout is None else stdout
#     }


# def make_result(description, stdout, stderr, status):
#     """Return result of update check."""

#     result = make_default()
#     result['description'] = description
#     result['stderr'] = stderr.strip().splitlines()
#     result['stdout'] = stdout.strip().splitlines()
#     result['status'] = status

#     if result['status'] == 124:
#         LOG.debug('command timed out')
#         result['stderr'].append('ERROR: command timed out')

#     # handle Node.js differently due to it's column headers,
#     # colored output, and propensity for displaying modules
#     # that are not actually outdated
#     if result['description'] == 'Node.js modules' and result['stdout']:
#         LOG.debug('preparing Node.js modules')
#         modules = []

#         if len(result['stdout']) >= 2:
#             result['header'] = result['stdout'][0]
#             LOG.debug('Node.js header: %s', result['header'])
#             all_module_lines = result['stdout'][1:]
#             LOG.debug('Node.js all_module_lines: %s', all_module_lines)
#             for module_line in all_module_lines:
#                 LOG.debug('Node.js module_line: %s', module_line)
#                 clean_line = reporters.Terminal.clean(module_line)
#                 _, current, wanted, _ = clean_line.split()
#                 LOG.debug('Node.js current: %s', current)
#                 LOG.debug('Node.js wanted: %s', wanted)
#                 # check whether the package is actually outdated
#                 if StrictVersion(current) < StrictVersion(wanted):
#                     LOG.debug("Node.js package '%s' is wanted", module_line)
#                     modules.append(module_line)

#         result['stdout'] = modules

#     return result


def make_result(description, stdout, stderr, status):
    """Return result of update check."""

    header = None
    stderr = stderr.strip().splitlines()
    stdout = stdout.strip().splitlines()

    if status == 124:
        LOG.debug('command timed out')
        stderr.append('ERROR: command timed out')

    # handle Node.js differently due to it's column headers,
    # colored output, and propensity for displaying modules
    # that are not actually outdated
    if description == 'Node.js modules' and stdout:
        LOG.debug('preparing Node.js modules')
        modules = []

        if len(stdout) >= 2:
            header = stdout[0]
            LOG.debug('Node.js header: %s', header)
            all_module_lines = stdout[1:]
            LOG.debug('Node.js all_module_lines: %s', all_module_lines)
            for module_line in all_module_lines:
                LOG.debug('Node.js module_line: %s', module_line)
                clean_line = reporters.Terminal.clean(module_line)
                _, current, wanted, _ = clean_line.split()
                LOG.debug('Node.js current: %s', current)
                LOG.debug('Node.js wanted: %s', wanted)
                # check whether the package is actually outdated
                if StrictVersion(current) < StrictVersion(wanted):
                    LOG.debug("Node.js package '%s' is wanted", module_line)
                    modules.append(module_line)

        stdout = modules

    return {
        'description': description,
        'header': header,
        'new': set(),
        'status': status,
        'stderr': stderr,
        'stdout': stdout
    }


def parse_args(args):
    """Parse command-line arguments."""

    def directory(path):
        """Ensure `path` is a directory."""
        if not os.path.isdir(path):
            raise argparse.ArgumentTypeError(
                "invalid directory path: '%s'" % path)
        return path

    parser = argparse.ArgumentParser(
        add_help=False,
        description='Poll for new updates.',
        usage='%(prog)s [-l|--list]')
    parser.add_argument(
        '-d', '--dir',
        dest='directory',
        help='override default configuration directory',
        type=directory)
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='list available updates')
    parser.add_argument(
        '--set-password',
        action='store_true',
        help='set email account password')

    group = parser.add_argument_group('logging options')
    group.add_argument(
        '--debug',
        action='store_true',
        # help='set the logging level to debug'
        help=argparse.SUPPRESS)
    group.add_argument(
        '--log',
        default=False,
        dest='logfile',
        # help='set log file destination'
        help=argparse.SUPPRESS,
        nargs='?')

    group = parser.add_argument_group('program options')
    group.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    group.add_argument(
        '--version',
        action='version',
        help=argparse.SUPPRESS,
        version='%(prog)s ' + __version__)

    return parser.parse_args(args)


def populate(path):
    """
    Return the application's configuration data, populating it
    if necessary.
    """

    try:
        return yaml_load(path)
    except FileNotFoundError:
        LOG.debug('did not find YAML document')
        skeleton = {
            'email': {
                'enabled': False,
                'from': 'username@gmail.com',
                'to': 'username@gmail.com',
                'subject': 'updatewatch',
                'smtp': {
                    'host': 'smtp.gmail.com',
                    'port': 587
                }
            },
            'notify': {
                'enabled': False,
            }
        }
        yaml_dump(skeleton, path)
        LOG.debug('created and populated default YAML document')
        return skeleton


def yaml_dump(data, path):
    """Write YAML document to `path`."""
    with open(path, 'w') as file:
        yaml.dump(data, file)


def yaml_load(path):
    """Return YAML document from `path`."""
    with open(path) as file:
        return yaml.load(file)


LOG = logging.getLogger(__program__)

if __name__ == '__main__':
    main()
