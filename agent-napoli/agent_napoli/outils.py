"""Lecture tolérante des cellules du tableur (format français ou ISO)."""

from __future__ import annotations

import re
from datetime import date


def lire_date(texte) -> date | None:
    """Accepte 2026-10-17, 17/10/2026, 17/10/26 et 17-10-2026. None si illisible."""
    t = str(texte or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        a, mo, j = (int(x) for x in m.groups())
    else:
        m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$", t)
        if not m:
            return None
        j, mo, a = (int(x) for x in m.groups())
        a += 2000 if a < 100 else 0
    try:
        return date(a, mo, j)
    except ValueError:
        return None


def lire_nombre(texte) -> float | None:
    """Accepte 1234.5, 1 234,50, 1 234,50 € ; None si illisible."""
    t = re.sub(r"[\s\xa0 €]", "", str(texte or ""))
    if t.count(",") == 1 and "." in t:          # 1.234,50
        t = t.replace(".", "")
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return None
