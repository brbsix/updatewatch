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
import re
import shelve
import smtplib
import subprocess
import sys
from distutils.version import StrictVersion
from textwrap import dedent

# external imports
import appdirs
import keyring
import yaml

# application imports
from updatewatch import __program__, __version__


class Config:  # pylint: disable=too-few-public-methods
    """Store global script configuration values."""

    def __init__(self, directory):
        self.directory = directory
        self.application = os.path.join(self.directory, __program__ + '.yaml')
        self.database = os.path.join(self.directory, __program__ + '.db')
        self.logfile = os.path.join(self.directory, __program__ + '.log')
        self.updates = os.path.join(self.directory, 'updates.yaml')


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
                    _, current, wanted, _ = Terminal.clean(module_line).split()
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


class Terminal:
    """Adjust and colorize terminal text."""
    BRIGHT = '\x1b[1m'
    LIGHTGREEN = '\x1b[92m'
    LIGHTRED = '\x1b[91m'
    RESET_ALL = '\x1b[0m'
    isatty = sys.stdout.isatty()
    TERM = []

    @staticmethod
    def clean(msg):
        """Stip terminal codes from text."""
        return re.sub(r'\x1b[^m]*m', '', msg)

    @staticmethod
    def error(msg):
        """Print red error message."""
        msg = Terminal.fix(msg)
        if not Terminal.isatty:
            print(Terminal.clean(msg))
        elif '\x1b' in msg:
            print(msg, file=sys.stderr)
        else:
            print(Terminal.LIGHTRED + msg + Terminal.RESET_ALL)

    @staticmethod
    def fix(msg):
        """
        Strip the 'move to start of line' terminal code
        that breaks indentation.
        """
        return msg.replace('\x1b[0G', '')

    @staticmethod
    def header(msg):
        """Print header message."""
        Terminal.plain(msg)

    @staticmethod
    def info(msg):
        """Print info message."""
        msg = Terminal.fix(msg)
        if not Terminal.isatty:
            print(Terminal.clean(msg))
        elif '\x1b' in msg:
            print(msg)
        else:
            print(Terminal.LIGHTGREEN + msg + Terminal.RESET_ALL)

    @staticmethod
    def plain(msg):
        """Print plain message."""
        msg = Terminal.fix(msg)
        if not Terminal.isatty:
            print(Terminal.clean(msg))
        else:
            print(msg)

    @staticmethod
    def title(msg):
        """Print title message."""
        msg = Terminal.fix(msg)
        if not Terminal.isatty:
            print(Terminal.clean(msg))
        else:
            print(Terminal.BRIGHT + msg + Terminal.RESET_ALL)


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


# def check(updates):
#     """Check for updates and return the results as a list of processes."""
#     processes = [execute(**u) for u in updates]

#     # start the processes then wait for them to finish
#     for _ in range(2):
#         results = [next(p) for p in processes]

#     return results


def email(msg, config):
    """Send an email message."""
    email_from = config['from']
    email_to = config['to']
    server = config['smtp']['host']
    port = config['smtp']['port']
    password = keyring.get_password(server, email_from)

    mailer = smtplib.SMTP(server, port)
    mailer.ehlo()
    mailer.starttls()
    mailer.login(email_from, password)
    mailer.sendmail(email_from, email_to, msg)


def email_new(results, path):
    """Email the results (if it is enabled and there is anything new)."""

    try:
        with open(path) as file:
            try:
                config = yaml.load(file)['email']
                enabled = config['enabled']
            except KeyError:
                return
            if enabled:
                new = any(r.new for r in results)
                if new:
                    subject = config.get('subject')
                    html = make_html(results, subject)
                    email(html, config)
    except FileNotFoundError:
        return


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

    options = parse_args(args)

    if options.directory is None:
        options.directory = appdirs.user_config_dir(__program__)
        # create directory if it does not exist
        os.makedirs(options.directory, exist_ok=True)
        # TODO: populate it with a sample updates.yaml file

    config = Config(options.directory)

    # configure logging
    logfile = config.logfile if options.logfile is None else None if \
        options.logfile is False else options.logfile
    loglevel = logging.DEBUG if options.debug else logging.WARNING
    _scriptlogger(logfile, loglevel)

    LOG.debug('config: %s', config)

    updates = get_updates(config.updates)

    LOG.debug('updates: %s', updates)

    results = check(updates)

    if options.list:
        LOG.debug('running show_all(results)')
        show_all(results)
        return

    with shelve.open(config.database) as database:

        # get hash of updates file to check whether it has changed
        key = get_hash(config.updates)
        LOG.debug('current key is %s', key)

        # print keys of all pre-existing entries stored in DB
        LOG.debug('existing keys: %s', list(database))

        # get pre-existing entry stored in DB
        existing = database.get(key, [])
        LOG.debug('existing is %s', existing)

        data = []
        for current, previous in itertools.zip_longest(results, existing):
            LOG.debug('processing current: %s', current.description)
            LOG.debug('processing previous: %s', previous.description
                      if previous is not None else previous)
            try:
                # find the difference between two sets
                new = current.updates - previous.updates
            except AttributeError:
                new = current.updates

            LOG.debug('new is %s', new)
            current.new = new

            # update the record if there are new updates or
            # an update has been performed without error
            if new or not current.stderr:
                LOG.debug('updating record')
                data.append(current)
            else:
                # be sure to wipe the old set
                previous.new = set()
                data.append(previous)

        # write to database
        LOG.debug('writing to database')
        database[key] = data

    LOG.debug('running show_new()')
    show_new(data)
    LOG.debug('running email_new()')
    email_new(data, config.application)


def make_html(results, subject=None):
    """Return HTML message."""
    def iter_html():
        """Generate strings of HTML."""
        yield dedent(
            '''\
            Content-type: text/html
            Subject: {subject}

            <span style="font-family: Courier, monospace;">
            <span style="font-size: 14px;">
            '''.format(
                subject=subject if subject is not None else __program__))
        for result in results:
            if result.stdout:
                yield '<p>'
                yield '&nbsp;<b>%s</b><br>' % result.description
                for line in result.stdout.splitlines():
                    # ignore headers and just print the first field
                    newline = line.split(' ')[0]
                    if line in result.new:
                        yield '+%s<br>' % Terminal.clean(newline)
                    else:
                        yield '&nbsp;%s<br>' % Terminal.clean(newline)
                yield '</p>'
        yield dedent(
            '''\
            </span>

            <span style="font-size: 12px;">
            <p>
            <i>Sent courtesy updatewatch</i>
            <br>
            <i>Copyright ©2016 Six (brbsix@gmail.com)</i>
            </p>
            </span>
            </span>
            ''')
    return '\n'.join(iter_html()).encode()


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


def show_all(results):
    """Display results via terminal and `notify-send`."""

    count = 0
    for result in results:
        if not result:
            continue

        Terminal.title('Checking %s...' % result.description)
        if result.stderr:
            Terminal.error(result.stderr)
        if result.stdout:
            if result.header:
                Terminal.header(result.header)
            for line in result.stdout.splitlines():
                Terminal.info(line)
                count += 1

        print()  # put empty line between different types of updates

    # only show notification if there are updates and the script is
    # being run interactively (e.g. from a TTY)
    if count > 0 and Terminal.isatty:
        subprocess.call([
            'notify-send', '-i', 'aptdaemon-update-cache', '-u', 'critical',
            'Update Notifier', '%d update%s available!' %
            (count, 's' if count > 1 else '')])


def show_new(results):
    """Display results (if there is anything new)."""

    new = any(r.new for r in results)

    if new:
        for result in results:
            if result.stdout:
                Terminal.title(' Checking %s...' % result.description)
                if result.header:
                    Terminal.header(' %s' % result.header)
                for line in result.stdout.splitlines():
                    if line in result.new:
                        Terminal.info('+%s' % line)
                    else:
                        Terminal.info(' %s' % line)
                Terminal.plain(' ')


LOG = logging.getLogger(__program__)

if __name__ == '__main__':
    main()
