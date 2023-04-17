@echo off

REM Build docs folder with conf.py
REM sphinx-quickstart

REM Update docs/crue10.*rst
sphinx-apidoc --ext-autodoc -d 4 -o docs crue10 crue10\tests

REM Build HTML documentation locally
sphinx-build -b html docs docs\html
