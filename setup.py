#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, print_function

import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    return io.open(join(dirname(__file__), *names), encoding=kwargs.get('encoding', 'utf8')).read()


setup(
    name='spiderkeeper-deploy',
    version='0.1.3',
    license='MIT license',
    description='Deploy to SpiderKeeper',
    long_description=read('README.rst'),
    author='Sam Kleiner',
    author_email='sam@skleiner.com',
    url='https://github.com/StoicPerlman/spiderkeeper-deploy',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
    ],
    keywords=['spiderkeeper', 'scrapy', 'devops'],
    install_requires=['click', 'configparser', 'requests', 'scrapy', 'scrapyd_client'],
    entry_points={'console_scripts': [
        'spiderkeeper-deploy = spiderkeeper_deploy.cli:main',
    ]},
)
