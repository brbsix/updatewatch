#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Display update results."""

# standard imports
import re
import subprocess
import sys


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
