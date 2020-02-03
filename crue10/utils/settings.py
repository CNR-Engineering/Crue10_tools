# coding: utf-8
import os


CRUE10_EXE_PATH = 'P:/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', os.sep)  # Crue PROD

CRUE10_EXE_OPTS = ['-r', '-g', '-i', '-c']  # Run complet (avec tous les pré-traitements)

GRAVITE_MIN = 'DEBUG3'

GRAVITE_MIN_ERROR = 'ERRNBLK'  # FIXME: pourquoi pas ERRBLK qui est encore plus grave ?

XML_ENCODING = 'utf-8'
