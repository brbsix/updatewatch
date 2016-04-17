# -*- coding: utf-8 -*-
"""
Application setup script

To build package:
python3 setup.py sdist bdist_wheel clean

To run tests in an virtualenv:
python3 setup.py test

To run tests directly with verbose output:
python3 -m pytest -vv
"""

from setuptools import find_packages, setup
from updatewatch import __description__, __program__, __version__



SETUP_REQUIRES = ['pytest-runner']
INSTALL_REQUIRES = ['appdirs', 'keyring', 'PyYAML']
TEST_REQUIRE = ['minimock', 'pytest', 'pytest-datafiles']

# install standalone mock if necessary (Python 3.2 and below)
try:
    __import__('unittest.mock')
except ImportError:
    TEST_REQUIRE.append('mock')

setup(
    name=__program__,
    version=__version__,
    description=__description__,
    author='Brian Beffa',
    author_email='brbsix@gmail.com',
    url='https://github.com/brbsix/updatewatch',
    license='GPLv3',
    packages=find_packages(),
    setup_requires=SETUP_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    tests_require=TEST_REQUIRE,
    entry_points={
        'console_scripts': ['updatewatch=updatewatch.updatewatch:main'],
    },
    keywords=['monitor', 'notify', 'updates'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities',
    ]
)
