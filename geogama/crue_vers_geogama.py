# coding: utf-8
"""
Lecture de plusieurs sous-modèles Crue10
"""
import logging
import re
import sys
import traceback

from crue10.emh.branche import BrancheAvecElementsSeuil
from crue10.emh.section import SectionIdem, SectionProfil, SectionSansGeometrie
from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger

import arcpy


# Parameters
if arcpy.GetArgumentCount() == 3:
    GDB = arcpy.GetParameterAsText(0)
    EDU_PATH = arcpy.GetParameterAsText(1)
    LST_SOUSMODELE = arcpy.GetParameterAsText(2).split(";")
else:
    # Debug
    GDB = r"C:\temp\BDD.gdb"
    EDU_PATH = r"Etu_from_scratch_2-Sm\Etu_from_scratch.etu.xml"
    LST_SOUSMODELE = ['Sm_amont', 'Sm_aval']


# Constants
FCLASS_NOEUD = "EMG/Noeud"
FCLASS_CASIER = "EMG/Casier"
FCLASS_BRANCHE = "EMG/Branche"
FCLASS_PROFIL_POINT = "EMG/Profil_Point"
FCLASS_PROFIL_TRACE = "EMG/Profil_Trace"
TABLE_SECTION = "Section"
TABLE_LIMITE = "Limite"
TABLE_CASIER_LOI = "Casier_Loi"
FCLASS_SEUIL_ELEM = "Seuil_Elem"

arcpy.env.workspace = GDB


# Init Logger
formatter = logging.Formatter('%(levelname)s: %(message)s')

logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

# handler2 = logging.StreamHandler(sys.stderr)
# handler2.setLevel(logging.DEBUG)
# handler2.setFormatter(formatter)
# logger.addHandler(handler2)


# Functions

def truncateAllClass():
    logger.info("Vidage des tables")

    arcpy.DeleteRows_management(GDB+"/"+FCLASS_NOEUD)
    arcpy.DeleteRows_management(GDB+"/"+FCLASS_CASIER)
    arcpy.DeleteRows_management(GDB+"/"+FCLASS_BRANCHE)
    arcpy.DeleteRows_management(GDB+"/"+FCLASS_PROFIL_POINT)
    arcpy.DeleteRows_management(GDB+"/"+FCLASS_PROFIL_TRACE)
    arcpy.DeleteRows_management(GDB+"/"+TABLE_SECTION)
    arcpy.DeleteRows_management(GDB+"/"+TABLE_LIMITE)
    arcpy.DeleteRows_management(GDB+"/"+TABLE_CASIER_LOI)
    arcpy.DeleteRows_management(GDB+"/"+FCLASS_SEUIL_ELEM)


def getDist(ptA, ptB):
    return math.sqrt((ptA.X - ptB.X)**2 + (ptA.Y - ptB.Y)**2)  


def getMPolyline(coords, distanceTot):
    points = arcpy.Array()
    currentDist = 0
    lastPoint = None
    for coord in coords:
        x = coord[0]
        y = coord[1]
        point = arcpy.Point(x, y)
        if not lastPoint is None:
            dist = getDist(point, lastPoint)
            currentDist += dist

        point.M = currentDist
        points.append(point)

        lastPoint = arcpy.Point(x, y)

    if distanceTot is not None:
        ratio = distanceTot / currentDist

        for point in points:
            point.M = point.M * ratio

    return arcpy.Polyline(points)


def getTroncon(emh_name):
    if '-' in emh_name:
        # St_VRH173.000-CDN_Am
        name = emh_name.split('-')[1]
    else:
        name = emh_name[3:]  # remove St_, Nd_, Br_, Ca_
    m = re.match(r"^(?P<troncon>[A-Za-z]+)", name)
    if m is None:
        return ''
    return m.group('troncon')[:10]


try:
    logger.info("Parametres")
    logger.info(GDB)
    logger.info(EDU_PATH)
    logger.info(LST_SOUSMODELE)

    # Ouverture session d'édition
    edit = arcpy.da.Editor(arcpy.env.workspace)
    edit.startEditing(False, False)

    # edit.startOperation()

    # Vidage des tables
    # truncateAllClass()

    # edit.stopOperation()

    # Liste des noeuds, pour éviter qu'ils soient insérés en double sur plusieurs sous-modèles
    hashNoeuds = {}

    # Get Etude
    study = Etude(EDU_PATH)

    for sm_elem in LST_SOUSMODELE:
        logger.info("Lecture Sous-modele- " + sm_elem)
        # Get Sous-modele
        sous_modele = study.get_sous_modele(sm_elem)
        sous_modele.read_all()

        # Suppression sections interpolées
        sous_modele.remove_sectioninterpolee()

        # Modifie le xp aval  des sections sansgeometrie a partir des branches
        sous_modele.replace_zero_xp_sectionaval()

        edit.startOperation()

        logger.info("Noeuds - " + str(len(sous_modele.noeuds)))
        with arcpy.da.InsertCursor(FCLASS_NOEUD, ["Troncon", "Nom_noeud", "SHAPE@"]) as cursor:
            for nomNoeud in sous_modele.noeuds:
                # Vérifie que le noeud n'a pas déjà été importé
                if nomNoeud not in hashNoeuds:
                    hashNoeuds[nomNoeud] = True
                    noeud = sous_modele.noeuds[nomNoeud]
                    if noeud.geom is not None:
                        logger.debug("Noeud - " + nomNoeud)
                        point = arcpy.Point(noeud.geom.x, noeud.geom.y)
                        cursor.insertRow([getTroncon(nomNoeud), nomNoeud, point])

        edit.stopOperation()
        edit.startOperation()

        logger.info("Casiers - " + str(len(sous_modele.casiers)))
        with arcpy.da.InsertCursor(FCLASS_CASIER, ["Nom_casier", "Nom_noeud", "Distance_appli", "SHAPE@"]) as cursor:
            for nomCasier in sous_modele.casiers:
                casier = sous_modele.casiers[nomCasier]
                logger.debug("Casier - " + nomCasier)
                polygon = arcpy.Polygon( arcpy.Array([arcpy.Point(*coords) for coords in casier.geom.coords]))
                cursor.insertRow((nomCasier,  casier.noeud_reference.id, casier.somme_longueurs(), polygon))

        edit.stopOperation()
        edit.startOperation()

        logger.info("Branches - " + str(len(sous_modele.branches)))
        with arcpy.da.InsertCursor(FCLASS_BRANCHE,  ["Troncon", "Nom_branche", "Type_branche", "Longueur", "Nom_noeud_amont", "Nom_noeud_aval", "IsActif", "SHAPE@"]) as cursor:
            for nomBranche in sous_modele.branches:
                logger.debug("Branche - " + nomBranche)
                branche = sous_modele.branches[nomBranche]
                polyline = getMPolyline(branche.geom.coords, branche.length)
                cursor.insertRow([getTroncon(nomBranche), nomBranche, branche.type, branche.length, branche.noeud_amont.id, branche.noeud_aval.id, branche.is_active, polyline])

        edit.stopOperation()
        edit.startOperation()

        logger.info("Sections - " + str(len(sous_modele.sections)))
        listSectionProfil = []
        with arcpy.da.InsertCursor(TABLE_SECTION, ["Troncon", "Nom_section", "Type_section", "Nom_branche", "Xp", "Nom_section_parent", "Delta_Z"]) as cursor:
            for nomBranche in sous_modele.branches:
                branche = sous_modele.branches[nomBranche]
                for section in branche.liste_sections_dans_branche:
                    nomSection = section.id
                    logger.debug("Section - " + nomSection)
                    nom_section_parent = None
                    dz = None
                    if isinstance(section, SectionSansGeometrie):
                        typeSection = 1
                        # TODO : Appeler méthode du coeur pour calculer le xp aval = branche.length
                    elif isinstance(section, SectionProfil):
                        typeSection = 2
                        # Merge lits numérotés
                        section.merge_consecutive_lit_numerotes()
                        listSectionProfil.append(section)
                    elif isinstance(section, SectionIdem):
                        typeSection = 3
                        nom_section_parent = section.section_reference.id
                        dz = section.dz_section_reference
                    cursor.insertRow([getTroncon(nomBranche), nomSection, typeSection, nomBranche, section.xp ,nom_section_parent, dz])

        edit.stopOperation()
        edit.startOperation()

        logger.info("ProfilPoints (par profil) - " + str(len(listSectionProfil)))
        list_limite_point = []
        with arcpy.da.InsertCursor(FCLASS_PROFIL_POINT, ["Nom_section", "Absc_proj", "Z", "SHAPE@"]) as cursor:
            for profil in listSectionProfil:
                if profil.geom_trace is not None:
                    logger.debug("Profil - " + profil.id)
                    # logger.debug("XY - " + str(len(profil.geom_trace.coords)))
                    # logger.debug("XZ - " + str(len(profil.xz)))

                    line = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in profil.geom_trace.coords[:]]))
                    i = 0
                    premier_point_x = 0
                    hashOIDPointParAbs = {}
                    for p in profil.xz:
                        absc_proj = p[0]  # x
                        z = p[1]  # z
                        if i == 0:
                            point = line.positionAlongLine(p[0])
                            premier_point_x = p[0]
                        else:
                            point = line.positionAlongLine(p[0] - premier_point_x)

                        id = cursor.insertRow([profil.id, absc_proj, z,  point])
                        hashOIDPointParAbs[absc_proj] = id
                        i += 1
                    for _, limite in profil.limites_geom.items():
                        oidPoint = hashOIDPointParAbs[limite.xt]
                        if limite.id == "Et_AxeHyd":
                            id_limite = 14
                        elif limite.id == "Et_Thalweg":
                            id_limite = 13
                        else:
                            continue
                        list_limite_point.append([oidPoint, id_limite])

                    for j in range(0, 6):
                        if j == 5:  # on prend le max
                            xt = profil.lits_numerotes[j - 1].xt_max
                        else:
                            xt = profil.lits_numerotes[j].xt_min
                        oidPoint = hashOIDPointParAbs[xt]
                        id_limite = j + 1
                        list_limite_point.append([oidPoint, id_limite])
                else:
                    logger.warning("Profil sans geom - " + profil.id)

        del cursor

        edit.stopOperation()
        edit.startOperation()

        logger.info("Limites - " + str(len(list_limite_point)))
        with arcpy.da.InsertCursor(TABLE_LIMITE, ["OID_Profil_Point", "Nom_Limite"]) as cursor_limite:
            for limite in list_limite_point:
                cursor_limite.insertRow(limite)
        del cursor_limite

        edit.stopOperation()
        edit.startOperation()

        logger.info("Profil_Trace - " + str(len(listSectionProfil)))
        with arcpy.da.InsertCursor(FCLASS_PROFIL_TRACE, ["Nom_section", "SHAPE@"]) as cursor:
            for profil in listSectionProfil:
                if profil.geom_trace is not None:
                    logger.debug("Profil - " + profil.id)
                    line = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in profil.geom_trace.coords[:]]))
                    cursor.insertRow([profil.id, line])
        del cursor

        edit.stopOperation()
        edit.startOperation()

        logger.info("Seuil_Elem")
        with arcpy.da.InsertCursor(FCLASS_SEUIL_ELEM, ["Nom_branche", "Largeur", "Z_Seuil", "CoefD", "CoefPDC"]) as cursor:
            for nomBranche in sous_modele.branches:
                branche = sous_modele.branches[nomBranche]
                if isinstance(branche, BrancheAvecElementsSeuil):
                    logger.debug("Seuil - " + nomBranche)
                    for seuil in branche.liste_elements_seuil:  # larg, z_seuil, coeff_d, coeff_pdc
                        cursor.insertRow([nomBranche, seuil[0], seuil[1], seuil[2], seuil[3]])
        del cursor

        edit.stopOperation()
        edit.startOperation()

        logger.info("Casier_Loi")
        with arcpy.da.InsertCursor(TABLE_CASIER_LOI, ["Nom_casier", "Xt", "Cote"]) as cursor:
            for nomCasier in sous_modele.casiers:
                casier = sous_modele.casiers[nomCasier]

                if len(casier.profils_casier) > 1:
                    logger.debug("Casier_Loi - Fusion - " + nomCasier)
                    casier.fusion_profil_casiers()

                if len(casier.profils_casier) > 0:
                    logger.debug("Casier_Loi - " + nomCasier)
                    for xz in casier.profils_casier[0].xz:
                        cursor.insertRow([nomCasier, xz[0], xz[1]])
        del cursor

        edit.stopOperation()

    logger.info("Enregistrement")
    edit.stopEditing(True)


except ExceptionCrue10 as e:
    # edit.stopOperation()
    # edit.stopEditing(False)
    logger.critical(e)


except Exception as ex:
    # edit.stopOperation()
    # edit.stopEditing(False)
    logger.critical(ex)
    traceback.print_exc()


logger.info("## Fin du traitement ##")
