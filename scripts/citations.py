"""Turn the free-text citation labels used in v7 into atomic publication ids.

A v7 label such as
    "Liu-Zeng et al., 2009; Xu et al., 2009, Yu et al., 2009; Zhang et al., 2012"
is split into four separate publications; spelling variants such as
"Lee et al., 2003", "Lee et al, 2003" and "Lee et al. (2003)" collapse to one id;
footnote text ("SRL is cumulative length") is separated from the citation.
"""
import re
import unicodedata

TYPO_FIX = {"papazachis": "papazachos", "landridge": "langridge"}

# agencies / catalogs / databases cited without a year
AGENCIES = {
    "ISC-GEM": ("isc-gem", "ISC-GEM catalogue", "catalog"),
    "GCMT": ("gcmt", "Global CMT (GCMT) catalogue", "catalog"),
    "USGS": ("usgs", "USGS", "agency"),
    "INGV": ("ingv", "INGV", "agency"),
    "GNS": ("gns", "GNS Science", "agency"),
    "GA": ("ga", "Geoscience Australia (GA)", "agency"),
    "NSHA18": ("nsha18", "NSHA18 (Geoscience Australia)", "database"),
    "AIST database": ("aist-afd", "AIST Active Fault Database", "database"),
    "SURE 2.0": ("sure2", "SURE 2.0 surface-rupture database", "database"),
}

AUTH = r"[A-Z][\w'’\-]+"
CITE = re.compile(
    rf"(?P<auth>{AUTH}(?:\s+(?:and|&)\s+{AUTH})?(?:\s+et\s+al\.?)?)"
    r"\s*,?\s*\(?\s*(?P<year>(?:19|20)\d{2})(?P<suf>[a-z])?\s*\)?"
)
AGENCY_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(AGENCIES, key=len, reverse=True)) + r")\b")


def _slug(surname):
    s = unicodedata.normalize("NFKD", surname).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return TYPO_FIX.get(s, s)


def _clean_auth(auth):
    a = re.sub(r"\s*&\s*", " and ", auth)
    a = re.sub(r"\s+et\s+al\.?", " et al.", a).strip()
    return a


def parse_label(label):
    """Return (pubs, annotation).

    pubs: list of dicts {pub_id, auth, year, suf, kind, short}
    annotation: leftover free text that is not a citation ('' if none)
    """
    text = str(label or "").replace("U.S. Geological Survey", "USGS")
    text = text.replace("AIST Active Fault Database (2019)", "AIST database")
    spans, pubs = [], []
    for m in CITE.finditer(text):
        first = re.split(r"\s+(?:and|&)\s+|\s+et\s+al", m.group("auth"))[0]
        slug = _slug(first)
        if not slug:
            continue
        year, suf = m.group("year"), m.group("suf") or ""
        auth = _clean_auth(m.group("auth"))
        # fix typo in the displayed surname too
        for bad, good in TYPO_FIX.items():
            auth = re.sub(bad, good, auth, flags=re.I) if bad in auth.lower() else auth
        if auth.split()[0].lower() in TYPO_FIX.values():
            auth = auth[0].upper() + auth[1:]
        kind = "agency" if first.upper() in AGENCIES else "publication"
        pub_id = f"{slug}_{year}{suf}"
        short = f"{auth} ({year}{suf})"
        pubs.append(dict(pub_id=pub_id, auth=auth, year=year, suf=suf, kind=kind, short=short))
        spans.append(m.span())
    for m in AGENCY_RE.finditer(text):
        if any(a <= m.start() < b for a, b in spans):
            continue
        pid, short, kind = AGENCIES[m.group(1)]
        pubs.append(dict(pub_id=pid, auth=short, year="", suf="", kind=kind, short=short))
        spans.append(m.span())
    # leftover text
    rest = list(text)
    for a, b in spans:
        for i in range(a, b):
            rest[i] = " "
    rest = "".join(rest)
    rest = re.sub(r"\b(and|&)\b", " ", rest)
    rest = re.sub(r"[;,&()\s\-]+", " ", rest).strip()
    annotation = rest if re.search(r"[A-Za-z0-9*]", rest) else ""
    # de-duplicate while keeping first spelling
    seen, uniq = set(), []
    for p in pubs:
        if p["pub_id"] not in seen:
            seen.add(p["pub_id"])
            uniq.append(p)
    return uniq, annotation


if __name__ == "__main__":  # quick self-check
    for lab in [
        "Liu-Zeng et al., 2009; Xu et al., 2009, Yu et al., 2009; Zhang et al., 2012",
        "Lee et al, 2003", "Lee et al. (2003)", "Lee et al., 2003",
        "Suter (2015); *Combined segments, **End-to-end",
        "U.S. Geological Survey (1964), Witkind et al. (1962), Johnson et al., (2018)",
        "NSHA18, GA", "Papazachis (1979)", "Philip and Meghraoui (1983), Yielding et al (1981)",
        "Wesnousky (2008) - probably includes afterslip (Sharp et al., 1982)",
    ]:
        p, a = parse_label(lab)
        print(lab, "->", [x["pub_id"] for x in p], "| note:", a)
