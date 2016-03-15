# -*- coding: utf-8 -*-
"""Tests for mailer.py"""

# standard imports
import random
from email.mime.text import MIMEText
from textwrap import dedent

# external imports
import keyring

# application imports
from updatewatch import __program__
from updatewatch import mailer


class TestMakeMsg:
    def test_make_msg(self):
        results = [
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

        html = dedent("""\
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

        msg_default = MIMEText(html, 'html')
        msg_default['Subject'] = __program__
        msg_default['From'] = 'example@domain.com'
        msg_default['To'] = 'example@domain.com'
        msg_default_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        assert mailer.make_msg(results, msg_default_config) == \
            msg_default.as_string()

        custom_subject = 'custom subject'
        msg_custom = MIMEText(html, 'html')
        msg_custom['Subject'] = custom_subject
        msg_custom['From'] = 'example@domain.com'
        msg_custom['To'] = 'example@domain.com'
        msg_custom_config = {
            'enabled': True,
            'from': 'example@domain.com',
            'to': 'example@domain.com',
            'subject': custom_subject,
            'smtp': {
                'host': 'smtp.domain.com',
                'login': 'example@domain.com',
                'port': 587
            }
        }

        assert mailer.make_msg(results, msg_custom_config) == \
            msg_custom.as_string()


class TestSetPasword:
    def test_set_password(self):
        """
        I don't know a simple way to mock up mailer.set_password(),
        so this is a rough approximation.
        """
        dummy_domain = '%s.com' % str(random.random())[2:]
        dummy_email_from = 'example@%s' % dummy_domain
        dummy_smtp_server = 'example.%s' % dummy_domain
        dummy_password = 'topsecret'

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
