"""Facet canonicalization. Raw columns are dirty; these make clean facets."""

# Canonical location set; everything else (incl. blanks/noise) buckets to "Այլ".
_KNOWN_LOCATIONS = {
    "Տուն", "Դուրս", "Խանութ", "Հիվանդանոց", "Գրասենյակ", "Փողոց", "Մեքենա",
}


def canonicalize_actors(raw, allowlist, typos):
    """Return (actors, roles). Comma-split first; space-split only when no comma."""
    if not isinstance(raw, str) or not raw.strip():
        return [], []
    if "," in raw:
        tokens = [t.strip() for t in raw.split(",")]
    else:
        tokens = [t.strip() for t in raw.split()]
    actors, roles = [], []
    for tok in tokens:
        if not tok:
            continue
        tok = typos.get(tok, tok)
        if tok in allowlist:
            if tok not in actors:
                actors.append(tok)
        else:
            roles.append(tok)
    return actors, roles


def canonicalize_location(raw):
    if isinstance(raw, str):
        v = raw.strip()
        if v in _KNOWN_LOCATIONS:
            return v
    return "Այլ"


def canonicalize_languages(raw):
    if not isinstance(raw, str) or not raw.strip():
        return []
    parts = raw.replace("+", ",").split(",")
    out = []
    for p in (x.strip() for x in parts):
        if p and p not in out:
            out.append(p)
    return out
