# -*- coding: utf-8 -*-
"""Application configuration."""

# standard imports
import argparse
import copy
import errno
import logging
import os

# external imports
import appdirs
import yaml

# application imports
from . import __program__, __version__


def directory(path):
    """Ensure `path` is a directory."""

    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(
            "invalid directory path: '%s'" % path)
    return path


def initialize_logging(logfile=None, loglevel=logging.WARNING):
    """Initialize program logger."""

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


def merge(source, destination):
    """
    Merge dictionaries.
    See: http://stackoverflow.com/a/20666342
    """

    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value

    return destination


def parse_args(args):
    """Parse command-line arguments."""

    class SmartFormatter(argparse.HelpFormatter):
        """Permit the use of raw text in help messages with 'r|' prefix."""

        def _split_lines(self, text, width):
            """argparse.RawTextHelpFormatter._split_lines"""
            if text.startswith('r|'):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    default_directory = appdirs.user_config_dir(__program__)

    parser = argparse.ArgumentParser(
        add_help=False,
        description='Poll for new updates.',
        formatter_class=SmartFormatter,
        usage='%(prog)s [-d DIRECTORY] [COMMAND]')

    parser.add_argument(
        '-d', '--dir',
        dest='directory',
        help='r|override default config directory\n'
             '(typically %s)' % default_directory,
        type=directory)
    parser.add_argument(
        '-s', '--single',
        action='store_false',
        dest='multiprocess',
        help='use a single process for checking updates')

    cgroup = parser.add_argument_group('commands')
    mgroup = cgroup.add_mutually_exclusive_group()
    # leave -l flag for backwards compatibility
    mgroup.add_argument(
        '-l',
        action='store_true',
        dest='list',
        help=argparse.SUPPRESS)
    mgroup.add_argument(
        '--list',
        action='store_true',
        help='list available updates')
    mgroup.add_argument(
        '--list-from-cache',
        action='store_true',
        help='list available updates from cache')
    mgroup.add_argument(
        '--run-from-cache',
        action='store_true',
        help='list new updates from cache')
    mgroup.add_argument(
        '--set-password',
        action='store_true',
        help='set email account password')

    lgroup = parser.add_argument_group('logging options')
    lgroup.add_argument(
        '--debug',
        action='store_true',
        help='set the logging level to debug')
    lgroup.add_argument(
        '--log',
        const=True,
        dest='logfile',
        help='set log file destination',
        nargs='?')

    pgroup = parser.add_argument_group('program options')
    pgroup.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    pgroup.add_argument(
        '--version',
        action='version',
        help=argparse.SUPPRESS,
        version='%(prog)s ' + __version__)

    options = parser.parse_args(args)

    # if no application directory has been set, configure a default
    # and create the directory if none exists
    if options.directory is None:
        options.directory = default_directory
        os.makedirs(options.directory, exist_ok=True)

    # application config paths
    options.application = os.path.join(options.directory,
                                       __program__ + '.yaml')
    options.database = os.path.join(options.directory, __program__ + '.db')
    options.updates = os.path.join(options.directory, 'updates.yaml')

    # logging config
    options.logfile = os.path.join(options.directory, __program__ + '.log') \
        if options.logfile is True else options.logfile
    options.loglevel = logging.DEBUG if options.debug else logging.WARNING

    # remove this useless property now that loglevel is set
    del options.debug

    return options


def populate(path):
    """
    Return the application's configuration data, populating it
    if necessary.
    """

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
        'notify': False
    }

    LOG.debug('running configuration.populate')

    try:
        original = yaml_load(path)
        merged = merge(original, copy.deepcopy(skeleton))
        if original == merged:
            return original
        yaml_dump(merged, path)
        LOG.debug('merged existing YAML document')
        return merged
    except IOError as exc:
        if exc.errno == errno.ENOENT:
            yaml_dump(skeleton, path)
            LOG.debug('created and populated default YAML document')
            return skeleton
        raise


def yaml_dump(data, path):
    """Write YAML document to `path`."""
    with open(path, 'w') as file:
        yaml.safe_dump(data, file)


def yaml_load(path):
    """Return YAML document from `path`."""
    with open(path) as file:
        return yaml.safe_load(file)


LOG = logging.getLogger(__program__)
