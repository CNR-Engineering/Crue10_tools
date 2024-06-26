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
    include_package_data=True,  # includes all non `.py` files found inside package directory (see MANIFEST.in)
    install_requires=requirements,
    description='Librairie Python pour les formats de fichiers Crue10',
    url='https://github.com/CNR-Engineering/crue10_tools',
)
