
# HTML entities corresponding table
HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def html_escape(text):
    """Produce entities within text."""
    return "".join(HTML_ESCAPE_TABLE.get(c, c) for c in text)


def float2str(value):
    """
    34.666664123535156 => not changed!
    1e30 => 1.0E30
    """
    text = str(value).replace('e+', 'E')
    if 'E' in text:
        # Exponent case
        if '.' not in text:
            text = text.replace('E', '.0E')
    return text
    # # Conventional rendering
    # text = format(value, '.15f')
    # return re.sub(r'\.([0-9])([0]+)$', r'.\1', text) # remove ending useless zeros


def typeclim2str_calcpseudoperm(type_clim):
    from crue10.scenario.calcul import CalcPseudoPerm
    return CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE[type_clim]


def typeclim2str_calctrans(type_clim):
    from crue10.scenario.calcul import CalcTrans
    return CalcTrans.CLIM_TYPE_TO_TAG_VALUE[type_clim]
