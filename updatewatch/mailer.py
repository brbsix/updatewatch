#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Email update results."""

# standard imports
import getpass
import smtplib
import sys
from textwrap import dedent

# external imports
import keyring
import yaml

# application imports
from . import __program__, reporters


def email(message, config):
    """Send an email message."""
    email_from = config['from']
    email_to = config['to']
    smtp_server = config['smtp']['host']
    port = config['smtp']['port']
    password = keyring.get_password(smtp_server, email_from)

    mailer = smtplib.SMTP(smtp_server, port)
    mailer.ehlo()
    mailer.starttls()
    mailer.login(email_from, password)
    mailer.sendmail(email_from, email_to, message)


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
                new = any(r['new'] for r in results)
                if new:
                    subject = config.get('subject')
                    html = make_html(results, subject)
                    email(html, config)
    except FileNotFoundError:
        return


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
            if result['stdout']:
                yield '<p>'
                yield '&nbsp;<b>%s</b><br>' % result['description']
                for line in result['stdout']:
                    # ignore headers and just print the first field
                    newln = line.split(' ')[0]
                    if line in result['new']:
                        yield '+%s<br>' % reporters.Terminal.clean(newln)
                    else:
                        yield '&nbsp;%s<br>' % reporters.Terminal.clean(newln)
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


def set_password(path):
    """
    Interactively set a keyring password for the
    configured email account.
    """

    with open(path) as file:
        config = yaml.load(file)['email']
        email_from = config['from']
        smtp_server = config['smtp']['host']

    try:
        password = getpass.getpass(
            prompt="Enter password for '{}' using '{}': ".format(
                email_from, smtp_server))
    except KeyboardInterrupt:
        print()
        sys.exit(1)

    keyring.set_password(smtp_server, email_from, password)
