#!/usr/bin/env python
from setuptools import find_packages, setup

from crue10 import VERSION


with open('requirements.txt') as f:
    requirements = f.read().splitlines()


setup(
    name='Crue10_tools',
    version=VERSION,
    author='Luc DURON',
    author_email='l.duron@cnr.tm.fr',
    packages=find_packages(),
    package_data={'crue10': ['crue10/data/*']},
    include_package_data=True,
    install_requires=requirements,
    description='Librairie Python pour les formats de fichiers Crue10',
    url='https://github.com/CNR-Engineering/crue10_tools',
)
