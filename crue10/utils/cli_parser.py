"""
Prepare module logger
"""
import argparse
import logging

from . import logger


LINE_WIDTH = 80


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


class MyArgParse(argparse.ArgumentParser):
    """
    Derived ArgumentParser with improved help message rendering
    """
    def __init__(self, description=None, *args, **kwargs):
        kwargs['formatter_class'] = CustomFormatter
        new_description = '_' * LINE_WIDTH + '\n' + description + '_' * LINE_WIDTH + '\n'
        super().__init__(add_help=False, description=new_description, *args, **kwargs)
        self._positionals.title = self._title_group('Positional and compulsory arguments')
        self._optionals.title = self._title_group('Optional arguments')
        self.add_argument('-v', '--verbose', help="increase output verbosity", action="store_true")

    @staticmethod
    def _title_group(label):
        """Decorates group title label"""
        return '~> ' + label

    def add_argument_group(self, name, *args, **kwargs):
        """Add title group decoration"""
        return super().add_argument_group(self._title_group(name), *args, **kwargs)

    def parse_args(self, *args, **kwargs):
        """Change verbosity is needed"""
        new_args = super().parse_args(*args, **kwargs)

        if 'verbose' in new_args:
            # Change verbosity globally
            logger.set_level(logging.DEBUG)

        return new_args
