# -*- coding: utf-8 -*-
"""Tests for mailer.py"""

# standard imports
import random

# external imports
import keyring

# application imports
from updatewatch import __program__
from updatewatch import mailer


class TestMakeHTML:
    def test_make_html(self):
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

        html_template = (
            'Content-type: text/html\n'
            'Subject: {subject}\n\n'
            '<span style="font-family: Courier, monospace;">\n'
            '<span style="font-size: 14px;">\n\n'
            '<p>\n'
            '&nbsp;<b>update C</b><br>\n'
            '&nbsp;someapp<br>\n'
            '</p>\n<p>\n'
            '&nbsp;<b>update E</b><br>\n'
            '&nbsp;otherapp<br>\n'
            '</p>\n<p>\n'
            '&nbsp;<b>Node.js modules</b><br>\n'
            '&nbsp;npm<br>\n'
            '</p>\n'
            '</span>\n\n'
            '<span style="font-size: 12px;">\n'
            '<p>\n'
            '<i>Sent courtesy updatewatch</i>\n<br>\n'
            '<i>Copyright ©2016 Six (brbsix@gmail.com)</i>\n</p>\n'
            '</span>\n</span>\n'
        )

        assert mailer.make_html(results) == \
            html_template.format(subject=__program__)

        subject = 'custom subject'
        assert mailer.make_html(results, subject) == \
            html_template.format(subject=subject)


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
