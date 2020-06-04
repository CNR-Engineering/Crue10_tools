# coding: utf-8
import os


CRUE10_EXE_PATH = 'P:/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', os.sep)  # Crue PROD
CRUE10_EXE_OPTS = ['-r', '-g', '-i', '-c']  # Run complet (avec tous les pré-traitements)

CSV_DELIMITER = ';'  # delimiter for output CSV files

GRAVITE_MAX = 'FATAL'
GRAVITE_MIN = 'DEBUG3'
GRAVITE_AVERTISSEMENT = 'WARN'
GRAVITE_MIN_ERROR = 'ERRNBLK'
GRAVITE_MIN_ERROR_BLK = 'ERRBLK'

try:
    from psutil import cpu_count
    NCSIZE = cpu_count(logical=False)  # does not include logical
except ImportError:
    from multiprocessing import cpu_count
    NCSIZE = cpu_count()  # includes logical


XML_ENCODING = 'utf-8'
