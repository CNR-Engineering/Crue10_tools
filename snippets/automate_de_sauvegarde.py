import matplotlib.pyplot as plt
import numpy as np
import os.path

from crue10.etude import Etude
from crue10.utils import logger


CALCUL_TRANS = 'Cc_dcnc1400-5min'
LOI_BARRAGE = 'LoiTQapp_BgeVS0'
NOM_SCENARIO_CIBLE = 'Sc_AS'

SECTION_BGE = 'St_RET33.700'
SECTION_AS = 'St_RET33.600'
SECTION_USINE = 'St_USI33.700'

Q_RESERVE = 0.0  # m3/s
TEMPS_MAX = 2 * 3600.0  # s


def get_time_of_first_value_above(x_array, y_array, y_target):
    if y_array[0] > y_target:
        return x_array[0]
    for i, y in enumerate(y_array):
        if y > y_target:
            # alpha = 0 => y = y_array[i-1] ; alpha = 1 => y = y_array[i]
            alpha = (y_target - y_array[i - 1]) / (y - y_array[i - 1])
            return alpha * x_array[i] + (1 - alpha) * x_array[i - 1]
    raise RuntimeError("Aucune valeur trouvée au-dessus de %f" % y_target)


def xy_array_tronquer_avant(xy_array, x_target):
    """Tronquer une loi avant une abscisse cible
    :param xy_array: tableau en entrée
    :param x_target: valeur de x avant laquelle tronquer
    :return: np.ndarray
    """
    x_array, y_array = xy_array.T
    x_array_new = x_array[x_array < x_target]
    x_array_new = np.append(x_array_new, x_target)
    return np.column_stack((x_array_new, np.interp(x_array_new, x_array, y_array)))


def xy_array_ajouter_gradient_apres(xy_array, gradient, duration):
    """Ajouter un point après la loi actuelle pour modélisation un gradient constant sur une durée définie
    :param xy_array: tableau en entrée
    :param gradient: gradient en m3/s/h
    :param duration: durée en s
    :return: np.ndarray
    """
    last_x = xy_array[-1, 0]
    last_y = xy_array[-1, 1]
    return np.vstack((xy_array,
                      np.array([(last_x + duration, last_y + gradient * duration / 3600.0)])))


class AutomateSauvegarde:
    """Automate de sauvegarde

    NH = niveau haut => procédure : ouverture barrage avec lâcher d'alerte si besoin
    NTH = niveau très haut => procédure : gradient barrage

    Principes :
    * 3 calculs successifs pour un calcul AS
    * Aucune temporisation n'est prise en compte
    * DeltaH n'est pas considéré
    """
    def __init__(self, scenario, nh_z, nth_z, nh_gradient, nth_gradient):
        self.scenario = scenario
        self.loi_hydraulique = scenario.get_loi_hydraulique(LOI_BARRAGE)
        self.hydrogramme = None
        self.time = None
        self.z_array = None

        self.nh_z = nh_z
        self.nth_z = nth_z
        self.nh_gradient = nh_gradient
        self.nth_gradient = nth_gradient

    def set_hydrogramme_and_run(self, run_id=None, comment=''):
        self.loi_hydraulique.set_values(self.hydrogramme)
        run = scenario.create_and_launch_new_run(etude, run_id=run_id, comment=comment, force=True)
        results = run.get_results()
        calc = results.get_calc_unsteady(CALCUL_TRANS)
        self.time = calc.time_serie()
        self.z_array = results.get_res_unsteady_var_at_emhs(CALCUL_TRANS, 'Z', [SECTION_AS])[:, 0]
        return run

    def run_all(self):
        self.hydrogramme = np.array([(0.0, -Q_RESERVE), (TEMPS_MAX, -Q_RESERVE)])

        # Etape 1 : Barrage au débit réservé
        self.set_hydrogramme_and_run('Etape2', comment='Procédure NH')
        nh_time = get_time_of_first_value_above(self.time, self.z_array, as_vs.nh_z)
        logger.info("NH atteint à t=%ss" % nh_time)

        # Etape 2 : Procédure NH
        self.hydrogramme = xy_array_ajouter_gradient_apres(xy_array_tronquer_avant(self.hydrogramme, nh_time),
                                                           -self.nh_gradient, TEMPS_MAX)
        self.set_hydrogramme_and_run('Etape2', comment='Procédure NH')
        nth_time = get_time_of_first_value_above(self.time, self.z_array, as_vs.nth_z)
        logger.info("NTH atteint à t=%ss" % nth_time)

        # Etape 3 : Procédure NTH
        self.hydrogramme = xy_array_ajouter_gradient_apres(xy_array_tronquer_avant(self.hydrogramme, nth_time),
                                                           -self.nth_gradient, TEMPS_MAX)
        run = self.set_hydrogramme_and_run('Etape3', comment='Procédure NTH')

        return run


# Lecture étude et création scénario pour l'étude AS
etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc', 'Etu_VS2015_conc',
                           'Etu_VS2003_Conc.etu.xml'))
etude.read_all()
etude.supprimer_scenario(NOM_SCENARIO_CIBLE, ignore=True, sleep=1.0)  # supprime le scénario s'il existe déjà
scenario = etude.ajouter_scenario_par_copie('Sc_VS2013-dclt', NOM_SCENARIO_CIBLE)


# Création et lancement d'un calcul AS
as_vs = AutomateSauvegarde(
    scenario,
    nh_z=150.30,  # mNGFO
    nth_z=150.60,  # mNGFO
    # Procédure NH : gradient 600 m3/s/h
    nh_gradient=600.0,
    # Procédure NTH : gradient 1500 m3/s/h
    nth_gradient=1500.0,
)
run = as_vs.run_all()

etude.write_etu()


# Extraction des résultats pour le graphique
results = run.get_results()
z_array = results.get_res_unsteady_var_at_emhs(CALCUL_TRANS, 'Z', [SECTION_AS])[:, 0]
q_barrage, q_usine = results.get_res_unsteady_var_at_emhs(CALCUL_TRANS, 'Q', [SECTION_BGE, SECTION_USINE]).T

# Mise en graphique des résultats
fig, ax1 = plt.subplots(figsize=(16, 9))

color = 'tab:red'
ax1.set_xlabel('Temps (s)')
ax1.set_ylabel('Z @ %s [mNGFO]' % SECTION_AS, color=color)

ax1.plot(as_vs.time, z_array, label='AS', color=color)

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

ax2.set_ylabel('Q [m3/s]')  # we already handled the x-label with ax1
ax2.plot(as_vs.time, q_barrage, label='Barrage @ %s' % SECTION_BGE, color='tab:blue')
ax2.plot(as_vs.time, q_usine, label='Usine @ %s' % SECTION_USINE, color='tab:green')
ax2.tick_params(axis='y')

ax2.legend(loc='upper right')
plt.show()
