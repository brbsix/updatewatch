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


class Result:  # pylint: disable=too-few-public-methods
    """Store result of update check."""

    def __init__(self, description, stdout, stderr, status):
        self.description = description
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        self.status = status

        self.header = None
        self.new = set()

        if status == 124:
            self.stderr = 'ERROR: command timed out' + \
                ('\n' + self.stderr if self.stderr else '')

        # handle Node.js differently due to it's column headers,
        # colored output, and propensity for displaying modules
        # that are not actually outdated
        if self.description == 'Node.js modules' and self.stdout:
            modules = []

            lines = self.stdout.splitlines()
            if len(lines) >= 2:
                self.header = lines[0]
                all_module_lines = lines[1:]
                for module_line in all_module_lines:
                    clean_line = reporters.Terminal.clean(module_line)
                    _, current, wanted, _ = clean_line.split()
                    # check whether the package is actually outdated
                    if StrictVersion(current) < StrictVersion(wanted):
                        modules.append(module_line)

            self.stdout = '\n'.join(modules) if modules else ''

    def __bool__(self):
        return bool(self.stdout or self.stderr)

    @property
    def updates(self):
        """Return a set of updates."""
        return set(self.stdout.splitlines())


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
        LOG.debug('processing current: %s', current.description)
        LOG.debug('processing previous: %s', previous.description
                  if previous is not None else previous)

        try:
            # find the difference between two sets
            new = current.updates - previous.updates
        except AttributeError:
            new = current.updates

        LOG.debug('new is %s', new)

        # update the record only if there are new updates or an update poll
        # has been performed without error
        if new or not current.stderr:
            if new:
                LOG.debug('current record has new updates (%s)', new)
            elif not current.stderr:
                LOG.debug('current record has no errors')
            LOG.debug('updating record')
            current.new = new
            data.append(current)
        else:
            LOG.debug('skipping record')
            # be sure to wipe the old set before adding it to the data
            previous.new = set()
            data.append(previous)

    return data


def execute(description, command):
    """Check for updates."""

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
        yield Result(description, stdout, stderr, status)


def get_data(results, config):
    """Get latest data, compare it to previous data, then shelve the result."""
    with shelve.open(config.database) as database:

        # get hash of updates file to check whether it has changed
        key = get_hash(config.updates)
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
    return hashlib.sha1(pickle.dumps(hashablize(item))).hexdigest()


def get_updates(path):
    """Return list of updates from configuration file."""
    with open(path) as file:
        return list(yaml.load_all(file))


def main(args=None):
    """Start application."""

    # parse command-line arguments into options
    options = parse_args(args)

    # if no application directory has been set, configure a default
    # and create the directory if none exists
    if options.directory is None:
        options.directory = appdirs.user_config_dir(__program__)
        os.makedirs(options.directory, exist_ok=True)

    config = Config(options.directory)

    # configure logging
    logfile = config.logfile if options.logfile is None else None if \
        options.logfile is False else options.logfile
    loglevel = logging.DEBUG if options.debug else logging.WARNING
    _scriptlogger(logfile, loglevel)

    LOG.debug('options: %s', options)
    LOG.debug('config: %s', config)

    # populate the application's configuration file with a default
    # if none exists
    populate(config.application)

    if options.set_password:
        LOG.debug('running mailer.set_password')
        mailer.set_password(config.application)
        sys.exit(0)

    updates = get_updates(config.updates)
    LOG.debug('updates: %s', updates)

    results = check(updates)

    if options.list:
        LOG.debug('running reporters.show_all')
        reporters.show_all(results)
        sys.exit(0)
    else:
        data = get_data(results, config)

        LOG.debug('running reporters.show_new')
        reporters.show_new(data)

        LOG.debug('running mailer.email_new')
        mailer.email_new(data, config.application)
        sys.exit(0)


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
    """Populate the application's default configuration file."""

    data = {
        'email': {
            'enabled': False,
            'from': 'username@gmail.com',
            'to': 'username@gmail.com',
            'subject': 'updatewatch',
            'smtp': {
                'host': 'smtp.gmail.com',
                'port': 587
                }
            }
        }

    try:
        with open(path) as file:
            yaml.load(file)
        LOG.debug('found YAML document')
    except FileNotFoundError:
        LOG.debug('did not find YAML document')
        with open(path, 'w') as file:
            yaml.dump(data, file)
        LOG.debug('created and populated default YAML document')


LOG = logging.getLogger(__program__)

if __name__ == '__main__':
    main()
