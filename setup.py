# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from updatewatch import __description__, __program__, __version__


# def read(filename):
#     with open(filename) as f:
#         return f.read()


setup(
    name=__program__,
    version=__version__,
    description=__description__,
    author='Brian Beffa',
    author_email='brbsix@gmail.com',
    # long_description=read('README.rst'),
    url='https://github.com/brbsix/updatewatch',
    license='GPLv3',
    keywords=['monitor', 'notify', 'updates'],
    packages=find_packages(),
    install_requires=[
        'appdirs', 'keyring', 'PyYAML'
    ],
    entry_points={
        'console_scripts': ['updatewatch=updatewatch.updatewatch:main'],
    },
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
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
    ],
)
