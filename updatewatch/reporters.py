# -*- coding: utf-8 -*-
"""Display update results."""

# standard imports
import logging
import re
import subprocess
import sys

# application imports
from . import __program__


class Terminal:
    """Adjust and colorize terminal text."""
    BRIGHT = '\x1b[1m'
    LIGHTGREEN = '\x1b[92m'
    LIGHTRED = '\x1b[91m'
    RESET_ALL = '\x1b[0m'
    isatty = sys.stdout.isatty()

    @staticmethod
    def clean(msg):
        """Strip terminal codes from text."""
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


def show_all(results, notify=False):
    """Display results via terminal and `notify-send`."""

    LOG.debug('running reporters.show_all %s notify',
              'with' if notify else 'without')

    count = 0
    for result in results:
        if result['stderr'] or result['stdout']:
            Terminal.title('Checking %s...' % result['description'])
            # print any errors first
            if result['stderr']:
                Terminal.error('\n'.join(result['stderr']))
            if result['stdout']:
                if result['header']:
                    Terminal.header(result['header'])
                for line in result['stdout']:
                    Terminal.info(line)
                    count += 1
            # print an empty line between different types of updates
            print()

    # show notification if it is enabled and there are updates
    if notify and count > 0:
        subprocess.call([
            'notify-send', '-i', 'aptdaemon-update-cache', '-u', 'critical',
            'Update Notifier', '%d update%s available!' %
            (count, 's' if count > 1 else '')])


def show_new(results):
    """Display results (if there is anything new)."""

    LOG.debug('running reporters.show_new')

    new = any(r['new'] for r in results)

    if new:
        for result in results:
            if result['stdout']:
                Terminal.title(' Checking %s...' % result['description'])
                if result['header']:
                    Terminal.header(' %s' % result['header'])
                for line in result['stdout']:
                    if line in result['new']:
                        Terminal.info('+%s' % line)
                    else:
                        Terminal.info(' %s' % line)
                Terminal.plain(' ')


LOG = logging.getLogger(__program__)
