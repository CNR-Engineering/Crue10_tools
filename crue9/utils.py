

def cvt_time_to_sec(jjhhmmss):
    """
    Convertir une chaîne représentant un temps en valeur numérique en secondes

    :param jjhhmmss: chaîne en entrée, par exemple 01:02:03:04
    :return: valeur en secondes, par exemple 93784
    """
    tab = jjhhmmss.split(":")
    val = 0.
    val += float(tab[0]) * 86400.
    val += 3600. * float(tab[1])
    val += 60. * float(tab[2])
    val += float(tab[3])
    return val
