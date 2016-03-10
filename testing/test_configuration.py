# -*- coding: utf-8 -*-
"""Tests for config.py"""

# standard imports
import argparse
import os
import logging
import random
import sys
from textwrap import dedent

# external imports
import appdirs
import pytest

# application imports
from updatewatch import __program__, __version__
from updatewatch import configuration


PROGRAM = os.path.basename(sys.argv[0])


class TestDirectory:
    def test_directory_exists(self, tmpdir):
        path = str(tmpdir)
        assert configuration.directory(path) == path

    def test_directory_does_not_exist(self, tmpdir):
        while True:
            badpath = str(tmpdir / str(random.random())[2:])
            if not os.path.isdir(badpath):
                break

        with pytest.raises(argparse.ArgumentTypeError) as exception:
            configuration.directory(badpath)

        assert str(exception.value) == "invalid directory path: '%s'" % badpath


class TestParseArgs:
    def test_parse_args(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args([]) == argparse.Namespace(
            application=os.path.join(directory, __program__ + '.yaml'),
            database=os.path.join(directory, __program__ + '.db'),
            directory=directory,
            list=False,
            logfile=None,
            loglevel=logging.WARNING,
            set_password=False,
            updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_debug(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args(['--debug']) == argparse.Namespace(
            application=os.path.join(directory, __program__ + '.yaml'),
            database=os.path.join(directory, __program__ + '.db'),
            directory=directory,
            list=False,
            logfile=None,
            loglevel=logging.DEBUG,
            set_password=False,
            updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_log_simple(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args(['--log']) == argparse.Namespace(
            application=os.path.join(directory, __program__ + '.yaml'),
            database=os.path.join(directory, __program__ + '.db'),
            directory=directory,
            list=False,
            logfile=os.path.join(directory, __program__ + '.log'),
            loglevel=logging.WARNING,
            set_password=False,
            updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_log_path(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args(
            ['--log', 'somepath']) == argparse.Namespace(
                application=os.path.join(directory, __program__ + '.yaml'),
                database=os.path.join(directory, __program__ + '.db'),
                directory=directory,
                list=False,
                logfile='somepath',
                loglevel=logging.WARNING,
                set_password=False,
                updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_dir_exists(self, tmpdir):
        directory = str(tmpdir)

        assert configuration.parse_args(
            ['--dir', directory]) == argparse.Namespace(
                application=os.path.join(directory, __program__ + '.yaml'),
                database=os.path.join(directory, __program__ + '.db'),
                directory=directory,
                list=False,
                logfile=None,
                loglevel=logging.WARNING,
                set_password=False,
                updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_dir_does_not_exist(self, capfd, tmpdir):
        while True:
            badpath = str(tmpdir / str(random.random())[2:])
            if not os.path.isdir(badpath):
                break

        with pytest.raises(SystemExit) as exception:
            configuration.parse_args(['--dir', badpath])

        assert exception.value.code is 2

        stderr = capfd.readouterr()[1]

        assert stderr == dedent("""\
            usage: {0} [-l|--list]
            {0}: error: argument -d/--dir: invalid directory path: '{1}'
            """.format(PROGRAM, badpath))

    def test_parse_args_list(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args(['--list']) == argparse.Namespace(
            application=os.path.join(directory, __program__ + '.yaml'),
            database=os.path.join(directory, __program__ + '.db'),
            directory=directory,
            list=True,
            logfile=None,
            loglevel=logging.WARNING,
            set_password=False,
            updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_set_password(self):
        directory = appdirs.user_config_dir(__program__)

        assert configuration.parse_args(
            ['--set-password']) == argparse.Namespace(
                application=os.path.join(directory, __program__ + '.yaml'),
                database=os.path.join(directory, __program__ + '.db'),
                directory=directory,
                list=False,
                logfile=None,
                loglevel=logging.WARNING,
                set_password=True,
                updates=os.path.join(directory, 'updates.yaml'))

    def test_parse_args_conflict(self, capfd):
        with pytest.raises(SystemExit) as exception:
            configuration.parse_args(['--list', '--set-password'])

        assert exception.value.code is 2

        stderr = capfd.readouterr()[1]

        assert stderr == dedent("""\
            usage: {0} [-l|--list]
            {0}: error: argument --set-password: not allowed with argument -l/--list
            """.format(PROGRAM))

    def test_parse_args_version(self, capfd):
        wanted = '{} {}\n'.format(PROGRAM, __version__)

        with pytest.raises(SystemExit) as exception:
            configuration.parse_args(['--version'])

        assert exception.value.code is 0

        stdout, stderr = capfd.readouterr()

        assert stdout == wanted or stderr == wanted


class TestPopulate:
    def test_populate_exists(self, tmpdir):
        document = dedent("""\
            email:
              enabled: false
              from: username@gmail.com
              smtp: {host: smtp.gmail.com, port: 587}
              subject: updatewatch
              to: username@gmail.com
            notify: {enabled: false}
            """)

        data_wanted = {
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

        path = str(tmpdir / 'file.yaml')

        with open(path, 'w') as file:
            file.write(document)

        data_returned = configuration.populate(path)

        assert data_returned == data_wanted

    def test_populate_does_not_exist(self, tmpdir):
        data_wanted = {
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

        document_wanted = dedent("""\
            email:
              enabled: false
              from: username@gmail.com
              smtp: {host: smtp.gmail.com, port: 587}
              subject: updatewatch
              to: username@gmail.com
            notify: {enabled: false}
            """)

        while True:
            path = str(tmpdir / str(random.random())[2:])
            if not os.path.exists(path):
                break

        data_returned = configuration.populate(path)

        assert data_returned == data_wanted

        with open(path) as file:
            document_returned = file.read()

        assert document_returned == document_wanted


class TestYampDump:
    def test_yaml_dump(self, tmpdir):
        data = {
            'key': 'value',
            'otherkey': 'othervalue',
            'somekey': 'somevalue'
        }

        document = '{key: value, otherkey: othervalue, somekey: somevalue}\n'

        path = str(tmpdir / 'file.yaml')

        configuration.yaml_dump(data, path)

        with open(path) as file:
            assert file.read() == document


class TestYamlLoad:
    def test_yaml_load(self, tmpdir):
        document = '{key: value, otherkey: othervalue, somekey: somevalue}\n'

        data = {
            'key': 'value',
            'otherkey': 'othervalue',
            'somekey': 'somevalue'
        }

        path = str(tmpdir / 'file.yaml')

        with open(path, 'w') as file:
            file.write(document)

        assert configuration.yaml_load(path) == data
