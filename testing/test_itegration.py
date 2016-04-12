# -*- coding: utf-8 -*-
"""updatewatch integration tests"""

# standard imports
import os
import sys
import subprocess

# external imports
import py
import pytest

# application imports
from updatewatch import __program__
from updatewatch.updatewatch import main


FIXTURE_DIR = py.path.local(
    os.path.dirname(
        os.path.realpath(__file__)
    )
) / 'data'

DATA_FILES = pytest.mark.datafiles(
    FIXTURE_DIR / 'updates.yaml',
    FIXTURE_DIR / __program__ + '.yaml'
)


def getstatusoutput(cmd):
    """Return (status, output) of executing cmd in a shell."""
    env = os.environ.copy()
    # copy the current sys.path to PYTHONPATH so subprocesses have access
    # to libs pulled by tests_require
    # See: https://github.com/pytest-dev/pytest-runner/issues/13
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    try:
        data = subprocess.check_output(cmd,
                                       env=env,
                                       shell=True,
                                       stderr=subprocess.DEVNULL,
                                       universal_newlines=True)
        status = 0
    except subprocess.CalledProcessError as exc:
        data = exc.output
        status = exc.returncode

    return status, data.rstrip('\n')


@DATA_FILES
def test_integration_is_a_tty(datafiles):

    stdout_wanted = "\x1b[1mChecking system packages...\x1b[0m\n\x1b[92mdocker-engine\x1b[0m\n\n\x1b[1mChecking Ruby 1.9.1 packages...\x1b[0m\n\x1b[92mmustache (0.99.8 < 1.0.2)\x1b[0m\n\n\x1b[1mChecking Ruby 2.1 packages...\x1b[0m\n\x1b[92mcommander (4.2.1 < 4.4.0)\x1b[0m\n\x1b[92mslop (3.6.0 < 4.2.1)\x1b[0m\n\n\x1b[1mChecking Node.js modules...\x1b[0m\n\x1b[?25h\x1b[K\x1b[?25h\x1b[K\x1b[4mPackage\x1b[24m  \x1b[4mCurrent\x1b[24m  \x1b[4mWanted\x1b[24m  \x1b[4mLatest\x1b[24m  \x1b[4mLocation\x1b[24m\n\x1b[33mnpm\x1b[39m        3.7.5   \x1b[32m3.8.0\x1b[39m   \x1b[35m3.8.0\x1b[39m  \x1b[90m\x1b[39m\n\n\x1b[1mChecking Vagrant boxes...\x1b[0m\n\x1b[92m* 'ubuntu/wily64' is outdated! Current: 20160107.0.0. Latest: 20160305.0.0\x1b[0m\n"

    directory = str(datafiles)

    # fool the program into thinking it has a tty
    command = '''script -eqfc "python3 -m updatewatch.updatewatch --dir '%s' --list" /dev/null''' % directory

    status, stdout = getstatusoutput(command)

    assert stdout == stdout_wanted and status is 0


@DATA_FILES
def test_integration_not_a_tty(datafiles, capfd):
    directory = str(datafiles)

    with pytest.raises(SystemExit) as exception:
        main(['--dir', directory, '--list'])

    status = exception.value.code

    stdout = capfd.readouterr()[0]

    stdout_wanted = "Checking system packages...\ndocker-engine\n\nChecking Ruby 1.9.1 packages...\nmustache (0.99.8 < 1.0.2)\n\nChecking Ruby 2.1 packages...\ncommander (4.2.1 < 4.4.0)\nslop (3.6.0 < 4.2.1)\n\nChecking Node.js modules...\nPackage  Current  Wanted  Latest  Location\nnpm        3.7.5   3.8.0   3.8.0  \n\nChecking Vagrant boxes...\n* 'ubuntu/wily64' is outdated! Current: 20160107.0.0. Latest: 20160305.0.0\n\n"

    assert stdout == stdout_wanted and status is 0
