# coding: utf-8
from crue10.utils.crueconfigmetier import ENUM_SEVERITE
from crue10.utils import ExceptionCrue10
from crue10.utils.message import parse_message
from crue10.utils.settings import GRAVITE_AVERTISSEMENT, GRAVITE_MIN_ERROR


class Trace:
    """
    Trace

    :param date: date
    :type date: str
    :param id: identifiant du message
    :type id: str
    :param gravite: gravité
    :type gravite: str
    :param localisation_methode: localisation méthode C++
    :type localisation_methode: str
    :param localisation_fichier: localisation fichier C++
    :type localisation_fichier: str
    :param localisation_ligne: localisation ligne dans fichier C++
    :type localisation_ligne: str
    :param nom_emh: nom EMH
    :type nom_emh: str
    :param parametres: liste des paramètrse numérotés
    :type parametres: str
    :param gravite_int: gravité (0=min, 100=max)
    :type gravite_int: int

    Exemple d'une ligne contenant dans l'ordre les 7 premiers attributs de la trace (séparés par des ;) :
    2019-04-16T14:09:21.661;ID_VERSION;INFO;Crue10::EMHModeleBase::utiliserParametresSortiesService;EMHModeleBase.cpp;198;Mo_VS2013_c10_octobre_2014;"10";"2";"0";"1";"2"
    """
    def __init__(self, line):
        """
        :param line: ligne d'un fichier CSV contenant des traces
        :type line: str
        Ex: 2019-04-16T14:09:21.661;ID_VERSION;INFO;Crue10::EMHModeleBase::utiliserParametresSortiesService;EMHModeleBase.cpp;198;Mo_VS2013_c10_octobre_2014;"10";"2";"0";"1";"2"
        """
        if not isinstance(line, str):
            line = line.encode('utf-8')  # Python2 fix: required to convert from unicode
        cells = line.replace('\n', '').replace('"', '').split(';')
        if len(cells) < 7:
            raise ExceptionCrue10("La trace ne contient pas assez de colonnes pour être lue :\n%s" % line)
        self.date, self.id, self.gravite, self.localisation_methode, self.localisation_fichier, \
            self.localisation_ligne, self.nom_emh = cells[:7]
        self.parametres = cells[7:]
        self.gravite_int = ENUM_SEVERITE[self.gravite]

    def is_erreur(self):
        """
        :return: est une erreur
        :rtype: bool
        """
        gravite_min_int = ENUM_SEVERITE[GRAVITE_MIN_ERROR]
        return self.gravite_int <= gravite_min_int

    def is_avertissement(self):
        """
        :return: est un avertissement
        :rtype: bool
        """
        return self.gravite == GRAVITE_AVERTISSEMENT

    def get_message(self):
        """Obtenir le message de la trace"""
        return parse_message(self.id, self.nom_emh, self.parametres)

    def __repr__(self):
        return '>%s|%s|%s|%s|%s' \
               % (self.date.ljust(23), self.gravite.ljust(6), self.nom_emh.ljust(32),
                  self.id.ljust(33), self.get_message())
