# coding: utf-8
import logging
import numpy as np
import os.path
import traceback
from operator import attrgetter

from shapely.geometry import Point, LinearRing, LineString

from crue10.emh.branche import BranchePdC, BrancheSeuilTransversal, \
    BrancheSeuilLateral, BrancheOrifice, BrancheStrickler, BrancheNiveauxAssocies, \
    BrancheBarrageGenerique, BrancheBarrageFilEau, BrancheSaintVenant
from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import LimiteGeom, SectionIdem, SectionProfil, SectionSansGeometrie
from crue10.sous_modele import SousModele
from crue10.utils import logger

import arcpy


###### Fonctions #####

def is_not_blank(s):
    return bool(s and s.strip())
    
def getPointsFromGeom(geom):
    lstPoints = []
    for part in geom:
        for pnt in part:
            lstPoints.append((pnt.X, pnt.Y))
    return lstPoints



###### Parametres #####


GDB = arcpy.GetParameterAsText(0)
WHERE_TRONCON = arcpy.GetParameterAsText(1)
FOLDER = arcpy.GetParameterAsText(2)
SM_NAME = arcpy.GetParameterAsText(3)

#Debug
# GDB = r"D:\Temp\CNR\ExportSectionSansBranche\BDD.gdb"
# WHERE_TRONCON = "Troncon IN ('VRH','CAF','RET','AMB','AVB','CAA','USI','ECL','PLAINE')"
# # WHERE_TRONCON = "1=1"
# FOLDER = r"D:\Temp\CNR\ExportSectionSansBranche"
# SM_NAME = 'Sm_T1'



#Init Logger
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


#Constantes
arcpy.env.workspace = GDB

FCLASS_NOEUD = "EMG/NOEUD"
FCLASS_CASIER = "EMG/CASIER"
FCLASS_BRANCHE = "EMG/BRANCHE"
FCLASS_PROFIL_POINT = "EMG/PROFIL_POINT"
FCLASS_PROFIL_TRACE = "EMG/PROFIL_TRACE"
TABLE_SECTION = "SECTION"
TABLE_LIMITE = "LIMITE"
TABLE_CASIER_LOI = "CASIER_LOI"
TABLE_SEUIL_ELEM = "SEUIL_ELEM"


#Variables
lstNoeud = []
hashNoeud = {}
lstCasier = []
hashCasier = {}
lstNomCasier = []
hashCasierLoi = {}

lstNomSection = []
lstSectionIdem = []
lstSectionSansGeometrie = []
lstSectionProfil = []
hashSectionForbranches = {}

hashProfilPointParOID = {}
lstProfilPoint = []

hashProfilPointParSection = {}
hashLimitesParSection = {}
hashProfilTraceParSection = {}

lstBranches = []
hashSeuilParBranche = {}

needSectionPilote = False

try:
# if True:

    logger.info("Parametres")
    logger.info(GDB)
    logger.info(WHERE_TRONCON)
    logger.info(FOLDER)
    logger.info(SM_NAME)
    
    ###### Lecture BDD #####
    logger.info("##Lecture de la base##")

    with arcpy.da.SearchCursor(FCLASS_NOEUD, ["OID@", "Nom_Noeud", "SHAPE@XY"], WHERE_TRONCON) as cursor:
        for row in cursor:
            if not is_not_blank(row[1]):
                logger.warn("Noeud sans nom  - " + str(row[0]))
                continue
                
            lstNoeud.append(row)
            hashNoeud[row[1]] = True

    logger.info("Noeuds- " + str(len(lstNoeud)))

    with arcpy.da.SearchCursor(FCLASS_CASIER, ["OID@", "Nom_casier", "Nom_noeud", "Distance_appli", "SHAPE@"]) as cursor:
        for row in cursor:
            if not is_not_blank(row[1]):
                # logger.warn("Casier sans nom  - " + str(row[0]))
                continue
            if not is_not_blank(row[2]):
                # logger.warn("Casier sans nom  de noeud - " + str(row[1]))
                continue
                
            # filtre sur les casier en fonction des noeuds    
            if not row[2] in hashNoeud:
                continue
                
                
            lstCasier.append(row)
            lstNomCasier.append(row[1])
          
    logger.info("Casiers- " + str(len(lstCasier)))

    if len(lstNomCasier) > 0:
        whereCasier = "Nom_Casier in ('" + "','".join(lstNomCasier) + "')"
        with arcpy.da.SearchCursor(TABLE_CASIER_LOI, ["OID@", "Nom_Casier", "Xt", "Cote"], whereCasier) as cursor:
            for row in cursor:
                nomCasier = row[1]
                
                if not is_not_blank(nomCasier):
                    logger.warn("Casier_Loi sans nom  - " + str(row[0]))
                    continue
                    
                if not nomCasier in hashCasierLoi:
                        hashCasierLoi[nomCasier] = []
                        
                hashCasierLoi[nomCasier].append((row[2], row[3]))

    lstNouvellesSections = []
    with arcpy.da.SearchCursor(TABLE_SECTION, ["OID@", "Nom_section", "Type_section", "Nom_branche", "Xp", "Nom_section_parent", "Delta_Z"], WHERE_TRONCON) as cursor:
        for row in cursor:
            nomSection = row[1]
            typeSection = row[2]
            nomBranche = row[3]
            sectionParent = row[5]
            
            if not is_not_blank(row[1]):
                logger.warn("Section sans nom  - " + str(row[0]))
                continue
                
            # if not is_not_blank(nomBranche):
                # logger.warn("Section sans branche  - " + nomSection)
                # continue
                
            if not typeSection:
                logger.warn("Section sans type  - " + nomSection)
                continue
            
            if typeSection == 1:
                lstSectionSansGeometrie.append(row)
            elif typeSection == 2:
                lstSectionProfil.append(row)
            elif typeSection == 3:
                lstSectionIdem.append(row)
          
            lstNomSection.append(nomSection)
            
    #Une fois que tout est chargée, vérifie que certaines sectionparent ne sont pas manquantes (appartenant à un autre tronçon)
    for row in lstSectionIdem:
        sectionParent = row[5]
        if (sectionParent is not None) and (not sectionParent in lstNomSection):
            lstNouvellesSections.append(sectionParent)

    logger.info("Sections- " + str(len(lstSectionSansGeometrie) + len(lstSectionProfil) + len(lstSectionIdem)))

    #Boucler sur les sections Idem et vérifier que la section parente est déjà récupérée
    if len(lstNouvellesSections) > 0:
        whereSectionParent = "Nom_section in ('" + "','".join(lstNouvellesSections) + "')"
        with arcpy.da.SearchCursor(TABLE_SECTION, ["OID@", "Nom_section", "Type_section", "Nom_branche", "Xp", "Nom_section_parent", "Delta_Z"], whereSectionParent) as cursor:
            for row in cursor:
                nomSection = row[1]
                # print nomSection
                typeSection = row[2]
                nomBranche = row[3]
                sectionParent = row[5]
                
                if not is_not_blank(row[1]):
                    logger.warn("Section sans nom  - " + str(row[0]))
                    continue
                    
                # if not is_not_blank(nomBranche):
                    # logger.warn("Section sans branche  - " + nomSection)
                    # continue
                    
                if not typeSection:
                    logger.warn("Section sans type  - " + nomSection)
                    continue
                
                if typeSection == 1:
                    lstSectionSansGeometrie.append(row)
                elif typeSection == 2:
                    lstSectionProfil.append(row)
                elif typeSection == 3:
                    lstSectionIdem.append(row)

                lstNomSection.append(nomSection)
                
    logger.info("Sections- " + str(len(lstSectionSansGeometrie) + len(lstSectionProfil) + len(lstSectionIdem)))

    if len(lstNomSection) > 0:
        whereSection = "Nom_section in ('" + "','".join(lstNomSection) + "')"
        with arcpy.da.SearchCursor(FCLASS_PROFIL_POINT, ["OID@", "Nom_section", "Absc_proj", "Z", "SHAPE@XY"], whereSection,sql_clause=(None,'ORDER BY Nom_section, Absc_proj')) as cursor:
            for row in cursor:
                hashProfilPointParOID[row[0]] = row
                lstProfilPoint.append(str(row[0]))
            
                nomSection = row[1]
                
                if not is_not_blank(nomSection):
                    logger.warn("Profil_Point sans nom_section - " + str(row[0]))
                    continue
                    
                if not nomSection in hashProfilPointParSection:
                    hashProfilPointParSection[nomSection] = []
                        
                #Stocke le tuple absProj/Z dans un tableau lié à la section
                hashProfilPointParSection[nomSection].append(row)

        with arcpy.da.SearchCursor(FCLASS_PROFIL_TRACE, ["OID@", "Nom_section", "SHAPE@"], whereSection) as cursor:
            for row in cursor:
                nomSection = row[1]
                
                if not is_not_blank(nomSection):
                    logger.warn("Profil_Trace sans nom_section - " + str(row[0]))
                    continue
                    
                if not nomSection in hashProfilTraceParSection:
                    hashProfilTraceParSection[nomSection] = []
                        
                hashProfilTraceParSection[nomSection].append(row[2])
            
   
    if len(lstProfilPoint) > 0:         
        whereProfilPoint = "OID_Profil_Point in (" + ",".join(lstProfilPoint) + ")"
        # print(whereProfilPoint)
        with arcpy.da.SearchCursor(TABLE_LIMITE, ["OID@", "OID_Profil_Point", "Nom_Limite"], whereProfilPoint) as cursor:
            for row in cursor:
                oidProfilPoint = row[1]
                
                # if not oidProfilPoint in hashProfilPointParOID:
                    # logger.warn("Limite sans point - " + str(row[0]))
                    # continue
                
                nomLimite = row[2]
                nomSection = hashProfilPointParOID[oidProfilPoint][1].encode('utf-8')
                abscProj = hashProfilPointParOID[oidProfilPoint][2]
                # print nomSection + " - " + str(nomLimite) + "-" + str(abscProj)
                    
                if not nomSection in hashLimitesParSection:
                    hashLimitesParSection[nomSection] = []
                
                #Stocke le tuple nom_limite/absProj  dans un tableau lié à la section
                hashLimitesParSection[nomSection].append((nomLimite, abscProj))
            

    lstNouveauxNoeuds = []
    lstNomBranches = []        
    with arcpy.da.SearchCursor(FCLASS_BRANCHE, ["OID@", "Nom_branche", "Type_branche", "Longueur", "Nom_noeud_amont", "Nom_noeud_aval", "IsActif", "SHAPE@"], WHERE_TRONCON) as cursor:
        for row in cursor:
            nomBranche = row[1].encode('utf-8')
            typeBranche = row[2]
            noeudAmont = row[4]
            noeudAval = row[5]
            
            if not is_not_blank(nomBranche):
                logger.warn("Section sans nom  - " + str(row[0]))
                continue
                
                
            if not typeBranche:
                logger.warn("Branche sans type  - " + nomBranche)
                continue
            
            lstBranches.append(row)
            lstNomBranches.append(nomBranche)
            
            if not noeudAval in hashNoeud:
                lstNouveauxNoeuds.append(noeudAval)
            if not noeudAmont in hashNoeud:
                lstNouveauxNoeuds.append(noeudAmont)
                
            if typeBranche == 14 or typeBranche == 15:
                needSectionPilote = True
            
    logger.info("Branches - " + str(len(lstBranches)))
    

    if len(lstNouveauxNoeuds) > 0:
        #Noeuds connectés aux branches mais pas déjà récupérés (pas dans les tronçons demandés)
        where_nouveaux_noeuds = "Nom_Noeud in ('"+ "','".join(lstNouveauxNoeuds) + "')"
        with arcpy.da.SearchCursor(FCLASS_NOEUD, ["OID@", "Nom_Noeud", "SHAPE@XY"], where_nouveaux_noeuds) as cursor:
            for row in cursor:
                if not is_not_blank(row[1]):
                    logger.warn("Noeud sans nom  - " + str(row[0]))
                    continue
                    
                lstNoeud.append(row)
                hashNoeud[row[1]] = True

         
    if len(lstNomBranches) > 0:
        whereclauseNomBranche = "Nom_branche in ('" + "','".join(lstNomBranches) + "')"
        # boucle sur Seuil_Elem
        with arcpy.da.SearchCursor(TABLE_SEUIL_ELEM, ["OID@", "Nom_branche", "Largeur", "Z_Seuil", "CoefD", "CoefPDC"], whereclauseNomBranche) as cursor:
            for row in cursor:
                nomBranche = row[1].encode('utf-8')
                Largeur = row[2]
                Z_Seuil = row[3]
                CoefD = row[4] if row[4] is not None else 1
                CoefPDC = row[5] if row[5] is not None else 1
                if Largeur is None:
                    continue #Pas de largeur
                    
                if not nomBranche in hashSeuilParBranche:
                    hashSeuilParBranche[nomBranche] = []
                 # mettre dans un hash par nombranche la liste des [(Abs/Z_classe)]
                hashSeuilParBranche[nomBranche].append((Largeur, Z_Seuil, CoefD, CoefPDC))
         
            
    ###### Ecriture du sous modele #####
    logger.info("##Ecriture sous modele##")

    # Build a sous_modele
    sous_modele = SousModele(SM_NAME, access='w')
    sous_modele.ajouter_lois_frottement_par_defaut()


    #Add noeud
    logger.info("Noeuds")
    for row in lstNoeud:
        nomNoeud = row[1].encode('utf-8')
        logger.debug("Ajour Noeud - " + nomNoeud)
        noeud = Noeud(nomNoeud)
        noeud.set_geom(Point(row[2][0], row[2][1]))
        sous_modele.ajouter_noeud(noeud)

    logger.info("Casiers")
    #Add casier
    for row in lstCasier:
        nomCasier = row[1].encode('utf-8')
        nomNoeud = row[2].encode('utf-8')
        if nomCasier in hashCasierLoi:
            logger.debug("Ajour Casier - " + nomCasier)
            casier = Casier(nomCasier, sous_modele.get_noeud(nomNoeud))
            
            casier.set_geom(LinearRing(getPointsFromGeom(row[4])))
            
            xz = hashCasierLoi[nomCasier]
            
            profilcasier = ProfilCasier('Pc_' + casier.id[3:] + '_001')
            profilcasier.set_longueur(row[3])
            profilcasier.set_xz(np.array(xz))
            casier.ajouter_profil_casier(profilcasier)
            
            
            sous_modele.ajouter_casier(casier)
        else:
            logger.warn("Casier sans loi - " + nomCasier)



    hashSectionsValid = {}

    logger.info("lstSectionSansGeometrie")
    # # Add sections
    for row in lstSectionSansGeometrie:
        nomSection = row[1].encode('utf-8')
        nomBranche = row[3]
        
        xp = row[4]
        logger.debug("Ajout SectionSansGeometrie - " + nomSection)
        section = SectionSansGeometrie(nomSection)
        sous_modele.ajouter_section(section)
        
        
        #Reference dans le dictionnaire des branches
        if nomBranche:
            nomBranche = nomBranche.encode('utf-8')
            if not nomBranche in hashSectionForbranches:
                hashSectionForbranches[nomBranche] = []
            hashSectionForbranches[nomBranche].append((nomSection, xp))

    logger.info("SectionProfil")
    for row in lstSectionProfil:
        nomSection = row[1].encode('utf-8')
        nomBranche = row[3]
        xp = row[4]
        
        if not nomSection in hashProfilPointParSection:
            logger.warn("Section sans point - " + nomSection)
            continue

        if not nomSection in hashProfilTraceParSection:
            logger.warn("Section sans trace - " + nomSection)
            continue        
            
        if not nomSection in hashLimitesParSection:
            logger.warn("Section sans limites - " + nomSection)
            continue 
          
        
        #Limites - il doit y avoir les limites 1 à 6 et la limite 14
        hasLimiteAxe = False
        hasLimitesNum = True
        limiteNumerote = [None] * 6
        limitesGeom = []
        for limite in hashLimitesParSection[nomSection]:
            idLimite = limite[0]
            absLimite = limite[1]
            # print str(idLimite) + "  -  " + str(absLimite)
            if idLimite < 7:
                limiteNumerote[idLimite -1] = absLimite
            elif idLimite == 14:
                hasLimiteAxe = True
                limitesGeom.append(("Et_AxeHyd", absLimite))
            elif idLimite == 13:
                limitesGeom.append(("Et_Thalweg", absLimite))
            
        for i in range(0, 6):
            if limiteNumerote[i] is None:
                hasLimitesNum = False
                break
        
        if not hasLimiteAxe:
            logger.warn("Section sans limite Et_AxeHyd - " + nomSection)
            continue 

        if not hasLimitesNum:
            logger.warn("Section sans limites numerotes - " + nomSection)
            continue 
            
            
        logger.debug("SectionProfil - " + nomSection)
        section = SectionProfil(nomSection)
        
        #ProfilPoint Abs/Z
        AbsZTuples = [(row[2], row[3]) for row in hashProfilPointParSection[nomSection]]
        # print(AbsZTuples)
        section.set_xz(np.array(AbsZTuples))  
        
        # logger.debug(limiteNumerote)
        section.set_lits_numerotes(limiteNumerote)
        for limite in limitesGeom:
            # logger.debug(limite[0])
            section.ajouter_limite_geom(LimiteGeom(limite[0], limite[1]))
            
        
        #Profil_Trace Geom : uniquement les points compris entre le premièr et la dernièr Lit_Numerote
        points = [(row[4][0], row[4][1]) for row in hashProfilPointParSection[nomSection] if (row[2] >= limiteNumerote[0]  and row[2] <= limiteNumerote[5])]

        section.set_geom_trace(LineString(points))
        
        sous_modele.ajouter_section(section)
        
        hashSectionsValid[nomSection] = True


        #Reference dans le dictionnaire des branches
        if nomBranche:
            nomBranche = nomBranche.encode('utf-8')
            if not nomBranche in hashSectionForbranches:
                hashSectionForbranches[nomBranche] = []
            hashSectionForbranches[nomBranche].append((nomSection, xp))
        
    logger.debug("SectionIdem")
    for row in lstSectionIdem:
        nomSection = row[1].encode('utf-8')
        nomBranche = row[3]
        xp = row[4]
        nomSectionParent = row[5].encode('utf-8')
        dz = row[6]
        
        if dz is None:
            dz = 0
            
        if not nomSectionParent in hashSectionsValid:
            logger.warn("SectionIdem [" + nomSection + "] - SectionParente non reconnue [" + nomSectionParent + "]")
            continue 
        
        logger.debug("Ajout SectionIdem - " + nomSection)
        section_parent = sous_modele.get_section(nomSectionParent)
        section = SectionIdem(nomSection, section_parent, dz)
        sous_modele.ajouter_section(section)


        #Reference dans le dictionnaire des branches
        if nomBranche:
            nomBranche = nomBranche.encode('utf-8')
            if not nomBranche in hashSectionForbranches:
                hashSectionForbranches[nomBranche] = []
            hashSectionForbranches[nomBranche].append((nomSection, xp))


    if needSectionPilote:
        sectionPilote = SectionSansGeometrie("St_Section_Pilote")
        sous_modele.ajouter_section(sectionPilote)
        
        
    # # Add branches
    #Fields : "OID@", "Nom_branche", "Type_branche", "Longueur", "Nom_noeud_amont", "Nom_noeud_aval", "IsActif"
    logger.debug("Branches")
    for row in lstBranches:
        nomBranche = row[1].encode('utf-8')
        typebranche = row[2]
        
        if not row[4] in hashNoeud:
            logger.warn("Branche sans noeud amont - " + nomBranche)
            continue 
        if not row[5] in hashNoeud:
            logger.warn("Branche sans noeud aval - " + nomBranche)
            continue 

        if not nomBranche in hashSectionForbranches:
            logger.warn("Branche sans sections - " + nomBranche)
            continue 

        if len(hashSectionForbranches[nomBranche]) < 2:
            logger.warn("Branche avec moins de 2 sections - " + nomBranche)
            continue 
            
        noeud1 = sous_modele.get_noeud(row[4].encode('utf-8'))
        noeud2 = sous_modele.get_noeud(row[5].encode('utf-8'))
        
        sections = hashSectionForbranches[nomBranche]
        sections.sort(key=lambda tup: tup[1])
        
        logger.debug("Ajout Branche - " + nomBranche)
        
        branche = None
        if typebranche == 1:
            branche = BranchePdC(nomBranche, noeud1, noeud2)
        elif typebranche == 2:
            branche = BrancheSeuilTransversal(nomBranche, noeud1, noeud2)
        elif typebranche == 4:
            branche = BrancheSeuilLateral(nomBranche, noeud1, noeud2)
        elif typebranche == 5:
            branche = BrancheOrifice(nomBranche, noeud1, noeud2)
        elif typebranche == 6:
            branche = BrancheStrickler(nomBranche, noeud1, noeud2)
        elif typebranche == 12:
            branche = BrancheNiveauxAssocies(nomBranche, noeud1, noeud2)
        elif typebranche == 14:
            branche = BrancheBarrageGenerique(nomBranche, noeud1, noeud2)
            branche.section_pilote = sous_modele.get_section("St_Section_Pilote")
        elif typebranche == 15:
            branche = BrancheBarrageFilEau(nomBranche, noeud1, noeud2)
            branche.section_pilote = sous_modele.get_section("St_Section_Pilote")
        elif typebranche == 20:
            branche = BrancheSaintVenant(nomBranche, noeud1, noeud2)    
        
        branche.set_geom(LineString(getPointsFromGeom(row[7])))
            
        for section in sections:
            nomSection = section[0].encode('utf-8')
            xp = section[1]
            section = sous_modele.get_section(nomSection)
            # if nomBranche == "Br_SBE21_BE26":
                # print nomSection
                # print section
                # print isinstance(section, SectionSansGeometrie)
                
            branche.ajouter_section_dans_branche(section, xp)
            
            # si seuils, ajouter
            if nomBranche in hashSeuilParBranche:
                branche.set_liste_elements_seuil(np.array(hashSeuilParBranche[nomBranche]))
            
        sous_modele.ajouter_branche(branche)


    ###### Enregistrement du sous modele #####
    logger.info("##Validation##")
    sous_modele.log_validation()  # could be called before `write_all`

    logger.info("##Enregistrement##")
    sous_modele.write_all(os.path.join(FOLDER, SM_NAME), 'Config')

    logger.info("##Verification##")
    sous_modele.log_check_xml(os.path.join(FOLDER, SM_NAME))  # has to be called after `write_all`
    logger.info("##Fin du traitement##")

# except IOError as e:
    # logger.critical(e)
    # sys.exit(1)
except Exception as e:
    logger.critical(e)
    logger.critical(traceback.format_exc())
    sys.exit(2)