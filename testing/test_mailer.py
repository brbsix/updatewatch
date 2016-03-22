# -*- coding: utf-8 -*-
"""Tests for mailer.py"""

# standard imports
import random
from email.mime.text import MIMEText
from textwrap import dedent
from unittest import mock

# external imports
import minimock
import pytest

# application imports
from updatewatch import __program__
from updatewatch import mailer


RESULTS = [
    {'description': 'update A',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': []},
    {'description': 'update B',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': []},
    {'description': 'update C',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': ['someapp']},
    {'description': 'update D',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': []},
    {'description': 'update E',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': ['warning'],
     'stdout': ['otherapp']},
    {'description': 'Node.js modules',
     'header': '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
               '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
               '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
               'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': [
         '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
         '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m'
     ]}
]

RESULTS_NEW = [
    {'description': 'update A',
     'header': None,
     'new': set('crazyapp'),
     'status': 0,
     'stderr': [],
     'stdout': ['crazyapp', 'lazyapp']},
    {'description': 'update B',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': []},
    {'description': 'update C',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': ['someapp']},
    {'description': 'update D',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': []},
    {'description': 'update E',
     'header': None,
     'new': set(),
     'status': 0,
     'stderr': ['warning'],
     'stdout': ['otherapp']},
    {'description': 'Node.js modules',
     'header': '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
               '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
               '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
               'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
     'new': set(),
     'status': 0,
     'stderr': [],
     'stdout': [
         '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
         '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m'
     ]}
]

HTML = dedent("""\
    <span style="font-family: Courier, monospace;">
    <span style="font-size: 14px;">

    <p>
    &nbsp;<b>update C</b><br>
    &nbsp;someapp<br>
    </p>
    <p>
    &nbsp;<b>update E</b><br>
    &nbsp;otherapp<br>
    </p>
    <p>
    &nbsp;<b>Node.js modules</b><br>
    &nbsp;npm<br>
    </p>
    </span>

    <span style="font-size: 12px;">
    <p>
    <i>Sent courtesy updatewatch</i>
    <br>
    <i>Copyright ©2016 Six (brbsix@gmail.com)</i>
    </p>
    </span>
    </span>
    """)


class TestEmailNew:
    def test_email_new(self):
        """Ensure correct email is sent when there are new results."""
        email_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        msg_wanted = ('Content-Type: text/html; charset="utf-8"\n'
                      'MIME-Version: 1.0\n'
                      'Content-Transfer-Encoding: base64\n'
                      'Subject: updatewatch\n'
                      'From: example@domain.com\n'
                      'To: example@domain.com\n\n'
                      'PHNwYW4gc3R5bGU9ImZvbnQtZmFtaWx5OiBDb3VyaWVyLCBtb25vc3B'
                      'hY2U7Ij4KPHNwYW4gc3R5\nbGU9ImZvbnQtc2l6ZTogMTRweDsiPgoK'
                      'PHA+CiZuYnNwOzxiPnVwZGF0ZSBBPC9iPjxicj4KJm5i\nc3A7Y3Jhe'
                      'nlhcHA8YnI+CiZuYnNwO2xhenlhcHA8YnI+CjwvcD4KPHA+CiZuYnNw'
                      'OzxiPnVwZGF0\nZSBDPC9iPjxicj4KJm5ic3A7c29tZWFwcDxicj4KP'
                      'C9wPgo8cD4KJm5ic3A7PGI+dXBkYXRlIEU8\nL2I+PGJyPgombmJzcD'
                      'tvdGhlcmFwcDxicj4KPC9wPgo8cD4KJm5ic3A7PGI+Tm9kZS5qcyBtb'
                      '2R1\nbGVzPC9iPjxicj4KJm5ic3A7bnBtPGJyPgo8L3A+Cjwvc3Bhbj'
                      '4KCjxzcGFuIHN0eWxlPSJmb250\nLXNpemU6IDEycHg7Ij4KPHA+Cjx'
                      'pPlNlbnQgY291cnRlc3kgdXBkYXRld2F0Y2g8L2k+Cjxicj4K\nPGk+'
                      'Q29weXJpZ2h0IMKpMjAxNiBTaXggKGJyYnNpeEBnbWFpbC5jb20pPC9'
                      'pPgo8L3A+Cjwvc3Bh\nbj4KPC9zcGFuPgo=\n')

        with mock.patch('updatewatch.mailer.send_email'):
            mailer.email_new(RESULTS_NEW, email_config)
            mailer.send_email.assert_called_once_with(msg_wanted, email_config)

    def test_email_new_disabled(self):
        """Ensure no email is sent when it is disabled."""
        email_config = {
            'enabled': False,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        with mock.patch('updatewatch.mailer.send_email'):
            mailer.email_new(RESULTS_NEW, email_config)
            assert not mailer.send_email.called

    def test_email_new_no_new(self):
        """Ensure no email is sent when there are no new results."""
        email_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        with mock.patch('updatewatch.mailer.send_email'):
            mailer.email_new(RESULTS, email_config)
            assert not mailer.send_email.called


class TestMakeMsg:
    def test_make_msg_default(self):
        """Create an email message without passing it a subject."""
        msg = MIMEText(HTML, 'html')
        msg['Subject'] = __program__
        msg['From'] = 'example@domain.com'
        msg['To'] = 'example@domain.com'
        msg_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        assert mailer.make_msg(RESULTS, msg_config) == \
            msg.as_string()

    def test_make_msg_custom(self):
        """Create an email message with a custom subject."""
        subject = 'custom subject'
        msg = MIMEText(HTML, 'html')
        msg['Subject'] = subject
        msg['From'] = 'example@domain.com'
        msg['To'] = 'example@domain.com'
        msg_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'subject': subject,
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        assert mailer.make_msg(RESULTS, msg_config) == \
            msg.as_string()


class TestSendEmail:
    def test_send_email(self, mock_send_email):
        """Send email with `from` address as login."""
        tracker = mock_send_email

        email_from = 'from@gmail.com'
        email_to = 'to@gmail.com'
        smtp_server = 'smtp.gmail.com'

        # arguments to send_email
        msg = 'message'
        email_config = {
            'enabled': True,
            'from': email_from,
            'to': email_to,
            'subject': 'updatewatch',
            'smtp': {
                'host': smtp_server,
                'port': 587
            }
        }

        # expected trace from minimock
        want = dedent("""\
            Called keyring.get_password('{smtp_server}', '{email_from}')
            Called smtplib.SMTP('{smtp_server}', 587)
            Called smtp_connection.ehlo()
            Called smtp_connection.starttls()
            Called smtp_connection.ehlo()
            Called smtp_connection.login(
                '{email_from}',
                'send_email_secret')
            Called smtp_connection.sendmail(
                '{email_from}',
                '{email_to}',
                '{msg}')""".format(
            email_from=email_from, email_to=email_to,
            smtp_server=smtp_server, msg=msg))

        # send email with mockups
        mailer.send_email(msg, email_config)

        # assert trace of all calls to smtplib are as expected
        minimock.assert_same_trace(tracker, want)

    def test_send_email_with_login(self, mock_send_email):
        """Send email with login account that differs from `from` address."""
        tracker = mock_send_email

        email_from = 'from@gmail.com'
        email_to = 'to@gmail.com'
        login = 'postmaster@sandbox7e7bc2edea94ddbae209e700c0017727.mailgun.org'
        smtp_server = 'smtp.gmail.com'

        # arguments to send_email
        msg = 'message'
        email_config = {
            'enabled': True,
            'from': email_from,
            'to': email_to,
            'subject': 'updatewatch',
            'smtp': {
                'login': login,
                'host': smtp_server,
                'port': 587
            }
        }

        # expected trace from minimock
        want = dedent("""\
            Called keyring.get_password(
                '{smtp_server}',
                '{login}')
            Called smtplib.SMTP('{smtp_server}', 587)
            Called smtp_connection.ehlo()
            Called smtp_connection.starttls()
            Called smtp_connection.ehlo()
            Called smtp_connection.login(
                '{login}',
                'send_email_secret')
            Called smtp_connection.sendmail(
                '{email_from}',
                '{email_to}',
                '{msg}')""".format(
            email_from=email_from, email_to=email_to, login=login,
            smtp_server=smtp_server, msg=msg))

        # send email with mockups
        mailer.send_email(msg, email_config)

        # assert trace of all calls to smtplib are as expected
        minimock.assert_same_trace(tracker, want)


class TestSetPassword:
    def test_set_password(self, mock_set_password):
        """Set password with `from` address as login."""
        tracker = mock_set_password

        email_from = 'from@gmail.com'
        smtp_server = 'smtp.gmail.com'

        # argument to set_password
        email_config = {
            'enabled': True,
            'from': email_from,
            'to': 'to@gmail.com',
            'subject': 'updatewatch',
            'smtp': {
                'host': smtp_server,
                'port': 587
            }
        }

        # expected trace from minimock
        want = dedent("""\
            Called getpass.getpass(
                prompt="Enter password for '{email_from}' using '{smtp_server}': ")
            Called keyring.set_password(
                '{smtp_server}',
                '{email_from}',
                'set_password_secret')""".format(
            email_from=email_from, smtp_server=smtp_server))

        # set password with mockups
        mailer.set_password(email_config)

        # assert trace of all calls to smtplib are as expected
        minimock.assert_same_trace(tracker, want)

    def test_set_password_with_login(self, mock_set_password):
        """Set password with login account that differs from `from` address."""
        tracker = mock_set_password

        login = 'postmaster@sandbox6265b22b66502d70d5f004f08238ac3c.mailgun.org'
        smtp_server = 'smtp.gmail.com'

        # argument to set_password
        email_config = {
            'enabled': True,
            'from': 'from@gmail.com',
            'to': 'to@gmail.com',
            'subject': 'updatewatch',
            'smtp': {
                'login': login,
                'host': smtp_server,
                'port': 587
            }
        }

        # expected trace from minimock
        want = dedent("""\
            Called getpass.getpass(
                prompt="Enter password for '{login}' using '{smtp_server}': ")
            Called keyring.set_password(
                '{smtp_server}',
                '{login}',
                'set_password_secret')""".format(
            login=login, smtp_server=smtp_server))

        # set password with mockups
        mailer.set_password(email_config)

        # assert trace of all calls to smtplib are as expected
        minimock.assert_same_trace(tracker, want)


@pytest.fixture(scope='function')
def mock_send_email(request):
    """Mock up smtplib.SMTP and keyring.get_password for send_email."""
    import smtplib
    import keyring

    # capture all calls into mock objects
    # (instead of letting output go to stdout)
    tracker = minimock.TraceTracker()

    # mock up smtplib
    minimock.mock('smtplib.SMTP',
                  returns=minimock.Mock('smtp_connection', tracker=tracker),
                  tracker=tracker)

    # mock up keyring.get_password
    minimock.mock('keyring.get_password',
                  returns='send_email_secret',
                  tracker=tracker)

    def finalizer():
        # restore all objects in global module state that minimock replaced
        minimock.restore()

    request.addfinalizer(finalizer)

    return tracker


@pytest.fixture(scope='function')
def mock_set_password(request):
    """Mock up getpass.getpass and keyring.set_password for set_password."""
    import getpass
    import keyring

    # capture all calls into mock objects
    # (instead of letting output go to stdout)
    tracker = minimock.TraceTracker()

    # mock up getpass.getpass
    minimock.mock('getpass.getpass',
                  returns='set_password_secret',
                  tracker=tracker)

    # mock up keyring.set_password
    minimock.mock('keyring.set_password',
                  tracker=tracker)

    def finalizer():
        # restore all objects in global module state that minimock replaced
        minimock.restore()

    request.addfinalizer(finalizer)

    return tracker


def test_keyring():
    """Test keyring functionality."""
    import keyring

    dummy_domain = '%s.com' % str(random.random())[2:]
    dummy_email_from = 'example@%s' % dummy_domain
    dummy_smtp_server = 'example.%s' % dummy_domain
    dummy_password = 'keyring_secret'

    try:
        keyring.set_password(service_name=dummy_smtp_server,
                             username=dummy_email_from,
                             password=dummy_password)

        password = keyring.get_password(service_name=dummy_smtp_server,
                                        username=dummy_email_from)

        assert password == dummy_password
    finally:
        keyring.delete_password(service_name=dummy_smtp_server,
                                username=dummy_email_from)


def test_make_html():
    assert mailer.make_html(RESULTS) == HTML
