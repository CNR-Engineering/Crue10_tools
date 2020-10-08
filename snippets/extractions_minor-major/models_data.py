import os
os.chdir('/home/yassine.kaddi/Scripts/Untitled Folder/Methodo/Script_CNR/Crue10_tools-master')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy.integrate import trapz

from crue10.etude import Etude
from crue10.emh.section import SectionProfil

none=999

def upt():
    mpl.rcParams['figure.figsize']= (10,7)
    mpl.rc('xtick', labelsize=15)
    mpl.rc('ytick', labelsize=15)
    mpl.rc('legend', fontsize=15)


def X_AxeH(results, branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section if isinstance(sect,SectionProfil)]
    if len(section)>0:
        return section[0].xt_axe
    else:
        return none

def section_pos(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    return section.xp
    
def Z_AxeH(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    z = [elt[1] for elt in section.xz if elt[0]==results.X_AxeH][0]
    return z

def X_intG(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    for li in section.lits_numerotes:
        if 'MajG' in li.id:
            if (li.xt_max != li.xt_min):
                return li.xt_min
            else:
                return none
            
def X_intD(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section ][0]

    for li in section.lits_numerotes:
        if 'MajD' in li.id:
            if (li.xt_max != li.xt_min):
                return li.xt_max
            else:
                return none
            
def Z_intG(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    z= [elt[1] for elt in section.xz if elt[0]==results.X_intG]
    if len(z)>0:
        return z[0]
    else:
        return none
    
def Z_intD(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    z= [elt[1] for elt in section.xz if elt[0]==results.X_intD]
    if len(z)>0:
        return z[0]
    else:
        return none

#Largeur FP gauche
def BG(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    if results.X_intG==none:
        return 0
    
    # Les abscisses/cotes du FP gauche 
    xz = [elt for elt in section.xz if elt[0] >= results.X_intG]

    # On peut avoir un débordement au point de l'interface mais que le fond > niveau d'eau juste avant dans le lit mineur (ex St_RET87.900 ds BV)
    xz_bug = [elt for elt in section.xz if elt[0] < results.X_intG][-1]
    
    if (results.Z <= xz[0][1]) or (results.Z <= xz_bug[1]):
        return 0
    # Les signes de Z - abscisses
    signs = [np.sign(results.Z - z[1]) for z in xz]
    # Abscisse de la limite
    if -1 in signs:
        X_apres,Z_apres = xz[signs.index(-1)]
        X_avant,Z_avant = xz[signs.index(-1)-1]
        
        X_lim = X_avant + (results.Z-Z_avant)*(X_apres-X_avant)/(Z_apres-Z_avant)
        
    else:
        X_lim = xz[-1][0]

    return X_lim-results.X_intG

#Largeur FP Droit
def BD(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    if results.X_intD==none:
        return 0
    # Les abscisses/cotes du FP droite 
    xz = [elt for elt in section.xz if elt[0] <= results.X_intD]
    xz.reverse()
    
    # On peut avoir un débordement au point de l'interface mais que le fond > niveau d'eau juste avant dans le lit mineur (ex St_RET87.900 ds BV)
    xz_bug = [elt for elt in section.xz if elt[0] > results.X_intD][0]
    
    #Si le niveau d'eau à l'interface <= fond de l'interface : pas de débordement
    if (results.Z <= xz[0][1]) or (results.Z <= xz_bug[1]):
        return 0
    
    # Les signes de Z - abscisses
    signs = [np.sign(results.Z - z[1]) for z in xz]
    # Abscisse de la limite
    if -1 in signs:
        X_apres,Z_apres = xz[signs.index(-1)-1]
        X_avant,Z_avant = xz[signs.index(-1)]
        
        X_lim = X_apres + (results.Z-Z_apres)*(X_avant-X_apres)/(Z_avant-Z_apres)
    else:
        X_lim = xz[-1][0]

    return results.X_intD-X_lim

#Largeur MC
def BM(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    if results.BG==0:   
        # On prends l'intersection avec le lit mineur
        xz = [elt for elt in section.xz if (elt[0] <= results.X_intG) and (elt[0] >= results.X_AxeH)]
        signs = [np.sign(results.Z - z[1]) for z in xz]
        
        if -1 in signs:    
            #niveau d'eau au dessous de celui du fond de l'interface
            X_apres,Z_apres = xz[signs.index(-1)]
            X_avant,Z_avant = xz[signs.index(-1)-1]
            Xmax = X_avant + (results.Z-Z_avant)*(X_apres-X_avant)/(Z_apres-Z_avant)
        else:
             #niveau d'eau à l'interface
            Xmax = xz[-1][0]   

    else:
        MC=[lit for lit in section.lits_numerotes if 'Mineur' in lit.id][0]
        Xmax = MC.xt_max
        
        
    if results.BD==0:   
#         On prends l'intersection avec le lit mineur
        xz = [elt for elt in section.xz if (elt[0] <= results.X_AxeH) and (elt[0] >= results.X_intD)]
        signs = [np.sign(results.Z - z[1]) for z in xz]
        if -1 in signs:
            #niveau d'eau au dessous de celui du fond de l'interface
            X_avant,Z_avant = xz[signs.index(-1)]
            X_apres,Z_apres = xz[signs.index(-1)-1]
            Xmin = X_apres + (results.Z-Z_apres)*(X_avant-X_apres)/(Z_avant-Z_apres)
        else:
            #niveau d'eau à l'interface
            Xmin = xz[0][0]           

    else:
        MC=[lit for lit in section.lits_numerotes if 'Mineur' in lit.id][0]
        Xmin = MC.xt_min
    
    return Xmax-Xmin

# Surface moyenne
def Smoy(results):    
    return results.Q/results.Vact

def Smoy_FP(results,branch):
    section = [sect for sect in branch.liste_sections_dans_branche if sect.id==results.section][0]
    
    if results.BG !=0:
        xi_G = [elt[0] for elt in section.xz if (elt[0] >= results.X_intG) and (elt[0] <= results.X_intG+results.BG)]
        zi_G = [elt[1] for elt in section.xz if (elt[0] >= results.X_intG) and (elt[0] <= results.X_intG+results.BG)]
    
        Z_eau = [results.Z]*len(xi_G)
        Smoy_G = trapz(Z_eau,xi_G)-trapz(zi_G,xi_G)
    else:
        Smoy_G=0
        
    if results.BD !=0:
        xi_D = [elt[0] for elt in section.xz if (elt[0] >= results.X_intD-results.BD) and (elt[0] <= results.X_intD)]
        zi_D = [elt[1] for elt in section.xz if (elt[0] >= results.X_intD-results.BD) and (elt[0] <= results.X_intD)]
        
        if len(xi_D)==1:
            xi_D = [results.X_intD-results.BD] + xi_D
            zi_D = [zi[zi.index(zi_D)+1]] + zi_D

        Z_eau = [results.Z]*len(xi_D)
        Smoy_D = trapz(Z_eau,xi_D)-trapz(zi_D,xi_D)
    else:
        Smoy_D=0
    return Smoy_D+Smoy_G



def compute_hf(results):
    if results.X_intD==none:
        hf = results.Z - results.Z_intG
    elif results.X_intG==none:
        hf = results.Z - results.Z_intD
    else:
        hf = max(results.Z - results.Z_intD,results.Z - results.Z_intG)
    return hf



# functions II
def info_branch(results,Cc,branche,min_section):
    # Get results
    res2_perm = results.get_res_steady_at_sections_along_branches_as_dataframe(Cc, [branche])

    # Compute AxeH
    res2_perm['X_AxeH']= res2_perm.apply(X_AxeH,axis=1,args=(branche,))

    # Filter to remove copied section, only Section profile
    res2_perm = res2_perm.loc[res2_perm['X_AxeH']!=999]

    res2_perm['Z_AxeH']= res2_perm.apply(Z_AxeH,axis=1,args=(branche,))

    # Get total nb of sections + indices
    nb_section_total = len(res2_perm)
    indices_ini = list(res2_perm.index)
    
    # Compute sections position
    res2_perm['section_pos']= res2_perm.apply(section_pos,axis=1,args=(branche,))

    # # Compute the coordinates of Int
    res2_perm['X_intD']= res2_perm.apply(X_intD,axis=1,args=(branche,))
    res2_perm['Z_intD']= res2_perm.apply(Z_intD,axis=1,args=(branche,))
    res2_perm['X_intG']= res2_perm.apply(X_intG,axis=1,args=(branche,))
    res2_perm['Z_intG']= res2_perm.apply(Z_intG,axis=1,args=(branche,))

    # # Filter to keep only flooding
    res2_perm = res2_perm.loc[(res2_perm['Z']>res2_perm['Z_intD']) | (res2_perm['Z']>res2_perm['Z_intG'])]
    
    if len(res2_perm)>=min_section :

        #BD , BG & BM: width of FPleft and right. We take next point
        res2_perm['BG']= res2_perm.apply(BG,axis=1,args=(branche,))
        res2_perm['BD']= res2_perm.apply(BD,axis=1,args=(branche,))
        res2_perm['BM']= res2_perm.apply(BM,axis=1,args=(branche,))
        res2_perm['Br']=(res2_perm['BG']+res2_perm['BD'])/(res2_perm['BG']+res2_perm['BM']+res2_perm['BD'])

        # Calcul de la surface moyenne
        res2_perm['Smoy']= res2_perm.apply(Smoy,axis=1)
        res2_perm['Smoy_FP']= res2_perm.apply(Smoy_FP,axis=1,args=(branche,))

        # Calcul de hf et hmoy
        res2_perm['hmoy']= res2_perm['Smoy']/(res2_perm['BG']+res2_perm['BM']+res2_perm['BD'])
        res2_perm['hmoy_FP']= res2_perm['Smoy_FP']/(res2_perm['BG']+res2_perm['BD'])
        res2_perm['hf']= res2_perm.apply(compute_hf,axis=1)
        return (res2_perm,nb_section_total,indices_ini)

    return (pd.DataFrame(),0,0)

def Info_calcul(results,Cc,modele,min_section):    
    all_branches= modele.get_liste_branches()
    res= {}
    info_res = {}
    for branch in all_branches:
        try:
            info,nb_section_total,indices_ini=info_branch(results,Cc, branch,min_section)
            if not info.empty:
                res[branch.id] = info
                info_res[branch.id+'nbS'] = nb_section_total
                info_res[branch.id+'ind'] = indices_ini
        except:
            print('Erreur dans : ', branch.id)
    
    return (res,info_res)
