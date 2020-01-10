#!/usr/bin/env python

from setuptools import find_packages, setup


with open('requirements.txt') as f:
    requirements = f.read().splitlines()


setup(
    name='Crue10_tools',
    version='2.0',
    author='Luc Duron',
    author_email='l.duron@cnr.tm.fr',
    packages=find_packages(),
    install_requires=requirements,
    description='Python library for Crue10 file formats',
    url='https://github.com/CNR-Engineering/crue10_tools',
)
