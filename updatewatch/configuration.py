# -*- coding: utf-8 -*-
"""Application configuration."""

# standard imports
import argparse
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


def initlogger(logfile=None, loglevel=logging.WARNING):
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


def parse_args(args):
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        add_help=False,
        description='Poll for new updates.',
        usage='%(prog)s [-l|--list]')

    parser.add_argument(
        '-d', '--dir',
        dest='directory',
        help='override default configuration directory',
        type=directory)

    mgroup = parser.add_mutually_exclusive_group()
    mgroup.add_argument(
        '-l', '--list',
        action='store_true',
        help='list available updates')
    mgroup.add_argument(
        '--set-password',
        action='store_true',
        help='set email account password')

    lgroup = parser.add_argument_group('logging options')
    lgroup.add_argument(
        '--debug',
        action='store_true',
        # help='set the logging level to debug'
        help=argparse.SUPPRESS)
    lgroup.add_argument(
        '--log',
        const=True,
        dest='logfile',
        # help='set log file destination'
        help=argparse.SUPPRESS,
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
        options.directory = appdirs.user_config_dir(__program__)
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

    # add support for Python 3.3 and below
    try:
        FileNotFoundError
    except NameError:
        # pylint: disable=invalid-name,redefined-builtin
        FileNotFoundError = IOError

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
