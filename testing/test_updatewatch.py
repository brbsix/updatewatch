# -*- coding: utf-8 -*-
"""Tests for updatewatch.py"""

# standard imports
import itertools
import os
import types
from tempfile import gettempdir
from textwrap import dedent

# application imports
from updatewatch import updatewatch


class TestCheck:
    def test_check(self):
        updates = [
            {'description': 'update A', 'command': 'echo'},
            {'description': 'update B', 'command': 'echo'},
            {'description': 'update C', 'command': 'echo someapp'},
            {'description': 'update D', 'command': 'echo'},
            {'description': 'update E',
             'command': 'echo otherapp; echo warning >&2'},
            {'description': 'Node.js modules',
             'command': "echo -e '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b[K"
                        "\x1b[4mPackage\x1b[24m  \x1b[4mCurrent\x1b[24m  \x1b["
                        "4mWanted\x1b[24m  \x1b[4mLatest\x1b[24m  \x1b[4mLocat"
                        "ion\x1b[24m\n\x1b[33mnpm\x1b[39m        3.7.5   \x1b"
                        "[32m3.8.0\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m"
                        "\x1b[39m'"}
        ]

        data_wanted = [
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

        data_returned = updatewatch.check(updates)

        assert isinstance(data_returned, types.GeneratorType)

        for returned, wanted in itertools.zip_longest(
                data_returned, data_wanted):
            assert returned == wanted


class TestDifference:
    def test_difference_empty(self):
        current = make_result(description='system packages',
                              stdout=['docker-engine', 'golang'])
        previous = updatewatch.make_default()
        difference = make_result(description='system packages',
                                 new={'docker-engine', 'golang'},
                                 stdout=['docker-engine', 'golang'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_simple(self):
        current = make_result(description='system packages',
                              stdout=['docker-engine', 'golang'])
        previous = make_result(description='system packages')
        difference = make_result(description='system packages',
                                 new={'docker-engine', 'golang'},
                                 stdout=['docker-engine', 'golang'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_incremental(self):
        current = make_result(description='system packages',
                              stdout=['docker-engine', 'golang'])
        previous = make_result(description='system packages',
                               stdout=['docker-engine'])
        difference = make_result(description='system packages',
                                 new={'golang'},
                                 stdout=['docker-engine', 'golang'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_same(self):
        current = make_result(description='system packages',
                              stdout=['docker-engine', 'golang'])
        previous = make_result(description='system packages',
                               stdout=['docker-engine', 'golang'])
        difference = make_result(description='system packages',
                                 stdout=['docker-engine', 'golang'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_status_and_stderr(self):
        current = make_result(description='system packages',
                              status=1,
                              stderr=['ERROR: Failed to resynchronize package index files from their sources'])
        previous = make_result(description='system packages',
                               stdout=['docker-engine', 'golang'])
        difference = make_result(description='system packages',
                                 status=1,
                                 stdout=['docker-engine', 'golang'],
                                 stderr=['ERROR: Failed to resynchronize package index files from their sources'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_status(self):
        current = make_result(description='system packages',
                              status=1)
        previous = make_result(description='system packages',
                               stdout=['docker-engine', 'golang'])
        difference = make_result(description='system packages',
                                 status=1,
                                 stdout=['docker-engine', 'golang'])

        assert updatewatch.difference(current, previous) == difference

    def test_difference_stderr(self):
        current = make_result(description='system packages',
                              stderr=['ERROR: Failed to resynchronize package index files from their sources'])
        previous = make_result(description='system packages',
                               stdout=['docker-engine', 'golang'])
        difference = make_result(description='system packages',
                                 stdout=['docker-engine', 'golang'],
                                 stderr=['ERROR: Failed to resynchronize package index files from their sources'])

        assert updatewatch.difference(current, previous) == difference


class TestExecute:
    def test_execute(self):
        kwargs = {
            'description': 'generic packages',
            'command': 'echo "line 1"; echo "line 2"; echo error >&2; exit 6'
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 6,
            'stderr': ['error'],
            'stdout': ['line 1', 'line 2']
        }

        process = updatewatch.execute(**kwargs)

        for _ in range(2):
            result = next(process)

        assert result == result_wanted

    def test_execute_timeout(self):
        kwargs = {
            'description': 'generic packages',
            'command': 'echo output; echo error >&2; sleep 0.2',
            'timeout': '0.1s'
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 124,
            'stderr': ['error', 'ERROR: command timed out'],
            'stdout': ['output']
        }

        process = updatewatch.execute(**kwargs)

        for _ in range(2):
            result = next(process)

        assert result == result_wanted

    def test_execute_working_directory(self):
        """
        Ensure the process's working directory is /tmp
        so as to not accidentally write to the program's
        pwd in the event of a misconfigured update command
        """
        kwargs = {
            'description': 'generic packages',
            'command': 'pwd'
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 0,
            'stderr': [],
            'stdout': [gettempdir()]
        }

        # ensure we're not already in /tmp
        os.chdir(os.environ['HOME'])

        process = updatewatch.execute(**kwargs)

        for _ in range(2):
            result = next(process)

        assert result == result_wanted


class TestGetHash:
    def test_get_hash_string(self):
        assert updatewatch.get_hash('string') == \
            '5484d51de6a7c5e04925f77637fe52b70dfaa1cb'

    def test_get_hash_list(self):
        assert updatewatch.get_hash([1, 2, 3]) == \
            '28e379c2b3c22a61bdf6f4f52036ccb3c4d2e968'

    def test_get_hash_dict(self):
        assert updatewatch.get_hash({'key': 'value',
                                     'otherkey': 'othervalue'}) == \
            'fbbfe7bab33048431f36c7686acb79a45dc0eb0b'

    def test_get_hash_list_of_simple_dicts(self):
        assert updatewatch.get_hash(
            [{'keyA': 'valueA'}, {'keyB': 'valueB'}]
            ) == '7ee146a87a81fff9799afaedffbea38a240c7682'

    def test_get_hash_list_of_complex_dicts(self):
        assert updatewatch.get_hash(
            [{'keyA': 'valueA',
              'otherkeyA': 'othervalueA'}, {'keyB': 'valueB',
                                            'otherkeyB': 'othervalueB'},
             {'keyC': 'valueC',
              'otherkeyC': 'othervalueC'}]
            ) == 'c55a6edfeee89d4af64632b35836d680d92b95b1'


class TestGetUpdates:
    def test_get_updates(self, tmpdir):
        document = dedent("""\
            description: update A
            command: command A
            ---
            description: update B
            command: command B
            ---
            description: update C
            command: command C
            ---
            description: update D
            command: command D
            ---
            description: update E
            command: command E
            """)

        data_wanted = [
            {'command': 'command A', 'description': 'update A'},
            {'command': 'command B', 'description': 'update B'},
            {'command': 'command C', 'description': 'update C'},
            {'command': 'command D', 'description': 'update D'},
            {'command': 'command E', 'description': 'update E'}
        ]

        path = str(tmpdir / 'updates.yaml')

        with open(path, 'w') as file:
            file.write(document)

        data_returned = updatewatch.get_updates(path)

        assert data_returned == data_wanted


class TestHashablize:
    def test_hashablize_string(self):
        assert updatewatch.hashablize('string') == 'string'

    def test_hashablize_list(self):
        assert updatewatch.hashablize([1, 2, 3]) == (1, 2, 3)

    def test_hashablize_dict(self):
        assert updatewatch.hashablize({'key': 'value',
                                       'otherkey': 'othervalue'}) == (
                                           ('key', 'value'),
                                           ('otherkey', 'othervalue'))

    def test_hashablize_list_of_simple_dicts(self):
        assert updatewatch.hashablize(
            [{'keyA': 'valueA'}, {'keyB': 'valueB'}]) == (
                (('keyA', 'valueA'), ), (('keyB', 'valueB'), ))

    def test_hashablize_list_of_complex_dicts(self):
        assert updatewatch.hashablize(
            [{'keyA': 'valueA',
              'otherkeyA': 'othervalueA'}, {'keyB': 'valueB',
                                            'otherkeyB': 'othervalueB'},
             {'keyC': 'valueC',
              'otherkeyC': 'othervalueC'}]) == ((('keyA', 'valueA'),
                                                 ('otherkeyA', 'othervalueA')),
                                                (('keyB', 'valueB'),
                                                 ('otherkeyB', 'othervalueB')),
                                                (('keyC', 'valueC'),
                                                 ('otherkeyC', 'othervalueC')))


class TestMakeResult:
    def test_make_result_simple(self):
        kwargs = {
            'description': 'generic packages',
            'stdout': '',
            'stderr': '',
            'status': 0
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 0,
            'stderr': [],
            'stdout': []
        }

        assert updatewatch.make_result(**kwargs) == result_wanted

    def test_make_result_empty(self):
        kwargs = {
            'description': 'generic packages',
            'stdout': '   ',
            'stderr': '',
            'status': 0
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 0,
            'stderr': [],
            'stdout': []
        }

        assert updatewatch.make_result(**kwargs) == result_wanted

    def test_make_result_more_empty(self):
        kwargs = {
            'description': 'generic packages',
            'stdout': ' \n \t \t\n \n  ',
            'stderr': '',
            'status': 0
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 0,
            'stderr': [],
            'stdout': []
        }

        assert updatewatch.make_result(**kwargs) == result_wanted

    def test_make_result_error(self):
        kwargs = {
            'description': 'generic packages',
            'stdout': '',
            'stderr': '\tline one\nline two\nline three\n\n',
            'status': 1
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 1,
            'stderr': ['line one', 'line two', 'line three'],
            'stdout': []
        }

        assert updatewatch.make_result(**kwargs) == result_wanted

    def test_make_result_timeout_error(self):
        kwargs = {
            'description': 'generic packages',
            'stdout': '',
            'stderr': '\tline one\nline two\nline three\n\n',
            'status': 124
        }

        result_wanted = {
            'description': 'generic packages',
            'header': None,
            'new': set(),
            'status': 124,
            'stderr': [
                'line one',
                'line two',
                'line three',
                'ERROR: command timed out'
            ],
            'stdout': []
        }

        assert updatewatch.make_result(**kwargs) == result_wanted


class TestModifierNodeJs:
    def test_modifer_node_js_empty(self):
        header, stdout = updatewatch.modifier_node_js([])

        assert header is None
        assert stdout == []

    def test_modifer_node_js_header_only(self):
        original_stdout = ['\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                           '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                           '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                           'atest\x1b[24m  \x1b[4mLocation\x1b[24m']

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                          '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                          '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                          'atest\x1b[24m  \x1b[4mLocation\x1b[24m')
        assert stdout == []

    def test_modifer_node_js_header_only_malformed(self):
        original_stdout = ['\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                           '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                           '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                           'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
                           'somejunk']

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                          '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                          '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                          'atest\x1b[24m  \x1b[4mLocation\x1b[24m')
        assert stdout == []

    def test_modifer_node_js_header_only_not_outdated(self):
        original_stdout = [
            '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
            '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
            '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
            'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
            '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.7.5'
            '\x1b[39m   \x1b[35m3.9.0\x1b[39m  \x1b[90m\x1b[39m'
        ]

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                          '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                          '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                          'atest\x1b[24m  \x1b[4mLocation\x1b[24m')
        assert stdout == []

    def test_modifer_node_js_with_one_outdated(self):
        original_stdout = [
            '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
            '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
            '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
            'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
            '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
            '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m'
        ]

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                          '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                          '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                          'atest\x1b[24m  \x1b[4mLocation\x1b[24m')
        assert stdout == ['\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
                          '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m']

    def test_modifer_node_js_with_multiple_outdated(self):
        original_stdout = [
            '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
            '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
            '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
            'atest\x1b[24m  \x1b[4mLocation\x1b[24m',
            '\x1b[33mjshint\x1b[39m        2.9.1   \x1b[32m2.9.1'
            '\x1b[39m   \x1b[35m2.9.1\x1b[39m  \x1b[90m\x1b[39m',
            '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
            '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m',
            '\x1b[33myo\x1b[39m        1.6.0   \x1b[32m1.7.0'
            '\x1b[39m   \x1b[35m1.7.0\x1b[39m  \x1b[90m\x1b[39m'
        ]

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b'
                          '[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent'
                          '\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mL'
                          'atest\x1b[24m  \x1b[4mLocation\x1b[24m')
        assert stdout == [
            '\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0'
            '\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m',
            '\x1b[33myo\x1b[39m        1.6.0   \x1b[32m1.7.0'
            '\x1b[39m   \x1b[35m1.7.0\x1b[39m  \x1b[90m\x1b[39m'
        ]

    def test_modifer_node_js_with_location(self):
        original_stdout = [
            '\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b[K\x1b[4mPackage\x1b[2'
            '4m           \x1b[4mCurrent\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b'
            '[4mLatest\x1b[24m  \x1b[4mLocation\x1b[24m',
            '\x1b[33mare-we-there-yet\x1b[39m    1.0.6   \x1b[32m1.1.1\x1b[39'
            'm   \x1b[35m1.1.1\x1b[39m  \x1b[90mnpmlog\x1b[39m',
            '\x1b[33mnpm\x1b[39m                1.1.25  \x1b[32m3.8.0\x1b[39'
            'm   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m']

        header, stdout = updatewatch.modifier_node_js(original_stdout)

        assert header == ('\x1b[?25h\x1b[0G\x1b[K\x1b[?25h\x1b[0G\x1b[K\x1b[4m'
                          'Package\x1b[24m           \x1b[4mCurrent\x1b[24m  '
                          '\x1b[4mWanted\x1b[24m  \x1b[4mLatest\x1b[24m  \x1b['
                          '4mLocation\x1b[24m')

        assert stdout == [
            '\x1b[33mare-we-there-yet\x1b[39m    1.0.6   \x1b[32m1.1.1\x1b[39m'
            '   \x1b[35m1.1.1\x1b[39m  \x1b[90mnpmlog\x1b[39m',
            '\x1b[33mnpm\x1b[39m                1.1.25  \x1b[32m3.8.0\x1b[39m '
            '  \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m'
        ]


def make_result(description=None,
                header=None,
                new=None,
                status=None,
                stderr=None,
                stdout=None):
    """Create a result."""

    # configure defaults
    description = '' if description is None else description
    new = set() if new is None else new
    status = 0 if status is None else status
    stderr = [] if stderr is None else stderr
    stdout = [] if stdout is None else stdout

    # validate input
    assert isinstance(description, str)
    assert isinstance(header, (str, type(None)))
    assert isinstance(new, set)
    assert isinstance(status, int)
    assert isinstance(stderr, list)
    assert isinstance(stdout, list)

    return {
        'description': description,
        'header': header,
        'new': new,
        'status': status,
        'stderr': stderr,
        'stdout': stdout
    }
