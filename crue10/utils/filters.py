
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


def float2str(x: float) -> str:
    if abs(x) >= 1e9 or (0 < abs(x) < 1e-6):
        # Si c’est un grand ou petit nombre, utiliser la notation scientifique en majuscules
        return f"{x:.1E}".replace('E+', 'E')
    else:
        # Sinon, garder la précision complète
        s = str(x)
        # S'assurer que les entiers aient ".0"
        if '.' not in s:
            s += '.0'
        return s
