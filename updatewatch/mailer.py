# -*- coding: utf-8 -*-
"""Email update results."""

# standard imports
import getpass
import smtplib
import sys
from email.mime.text import MIMEText
from textwrap import dedent

# external imports
import keyring

# application imports
from . import __program__, reporters


def send_email(msg, email_config):
    """Send an email message."""
    email_from = email_config['from']
    email_to = email_config['to']
    smtp_server = email_config['smtp']['host']
    port = email_config['smtp']['port']
    try:
        login = email_config['smtp']['login']
    except KeyError:
        login = email_from
    password = keyring.get_password(smtp_server, login)

    mailer = smtplib.SMTP(smtp_server, port)
    # identify ourselves to smtp gmail client
    mailer.ehlo()
    # secure connection with TLS encryption
    mailer.starttls()
    # re-identify encrypted connection
    mailer.ehlo()
    mailer.login(login, password)
    mailer.sendmail(email_from, email_to, msg)


def email_new(results, email_config):
    """Email the results (if it is enabled and there is anything new)."""

    if email_config.get('enabled'):
        new = any(r.get('new') for r in results)
        if new:
            msg = make_msg(results, email_config)
            send_email(msg, email_config)


def make_html(results):
    """Return HTML message."""
    def iter_html():
        """Generate strings of HTML."""
        yield dedent(
            '''\
            <span style="font-family: Courier, monospace;">
            <span style="font-size: 14px;">
            ''')
        for result in results:
            if result['stdout']:
                yield '<p>'
                yield '&nbsp;<b>%s</b><br>' % result['description']
                for line in result['stdout']:
                    # ignore headers and just print the first field
                    newln = line.lstrip(' \t*').split()[0].strip('\'"')
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
    return '\n'.join(iter_html())


def make_msg(results, email_config):
    """Return email message."""

    html = make_html(results)
    msg = MIMEText(html, 'html')
    msg['Subject'] = email_config.get('subject', __program__)
    msg['From'] = email_config['from']
    msg['To'] = email_config['to']

    return msg.as_string()


def set_password(email_config):
    """
    Interactively set a keyring password for the
    configured email account.
    """

    email_from = email_config['from']
    smtp_server = email_config['smtp']['host']
    try:
        login = email_config['smtp']['login']
    except KeyError:
        login = email_from

    try:
        password = getpass.getpass(
            prompt="Enter password for '{}' using '{}': ".format(
                login, smtp_server))
    except KeyboardInterrupt:
        print()
        sys.exit(1)

    keyring.set_password(smtp_server, login, password)
