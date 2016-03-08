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

# application imports
from . import __program__, reporters


def email(message, email_config):
    """Send an email message."""
    email_from = email_config['from']
    email_to = email_config['to']
    smtp_server = email_config['smtp']['host']
    port = email_config['smtp']['port']
    password = keyring.get_password(smtp_server, email_from)

    mailer = smtplib.SMTP(smtp_server, port)
    mailer.ehlo()
    mailer.starttls()
    mailer.login(email_from, password)
    mailer.sendmail(email_from, email_to, message)


def email_new(results, email_config):
    """Email the results (if it is enabled and there is anything new)."""

    if email_config.get('enabled'):
        new = any(r.get('new') for r in results)
        if new:
            subject = email_config.get('subject')
            html = make_html(results, subject)
            email(html, email_config)


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


def set_password(email_config):
    """
    Interactively set a keyring password for the
    configured email account.
    """

    email_from = email_config['from']
    smtp_server = email_config['smtp']['host']

    try:
        password = getpass.getpass(
            prompt="Enter password for '{}' using '{}': ".format(
                email_from, smtp_server))
    except KeyboardInterrupt:
        print()
        sys.exit(1)

    keyring.set_password(smtp_server, email_from, password)
