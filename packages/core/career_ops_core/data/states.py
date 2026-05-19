"""Canonical application statuses from templates/states.yml."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

CANONICAL_STATUSES = [
    "Evaluated",
    "Applied",
    "Responded",
    "Interview",
    "Offer",
    "Rejected",
    "Discarded",
    "SKIP",
]

# All known aliases → canonical label
ALIASES: dict[str, str] = {
    # Spanish
    "evaluada": "Evaluated",
    "condicional": "Evaluated",
    "hold": "Evaluated",
    "evaluar": "Evaluated",
    "verificar": "Evaluated",
    "aplicado": "Applied",
    "enviada": "Applied",
    "aplicada": "Applied",
    "applied": "Applied",
    "sent": "Applied",
    "respondido": "Responded",
    "entrevista": "Interview",
    "oferta": "Offer",
    "rechazado": "Rejected",
    "rechazada": "Rejected",
    "descartado": "Discarded",
    "descartada": "Discarded",
    "cerrada": "Discarded",
    "cancelada": "Discarded",
    "no aplicar": "SKIP",
    "no_aplicar": "SKIP",
    "skip": "SKIP",
    "monitor": "SKIP",
    "geo blocker": "SKIP",
}

# Pipeline advancement order (higher = more advanced)
STATUS_RANK: dict[str, int] = {
    "skip": 0,
    "discarded": 0,
    "rejected": 1,
    "evaluated": 2,
    "applied": 3,
    "responded": 4,
    "interview": 5,
    "offer": 6,
}


def load_states_yml(states_path: Path) -> dict:
    """Load and return the raw states.yml data."""
    if not states_path.exists():
        return {}
    with open(states_path) as f:
        return yaml.safe_load(f) or {}


def normalize_status(raw: str) -> Optional[str]:
    """Map raw status text to a canonical label. Returns None if unknown."""
    # Strip markdown bold and leading/trailing whitespace
    s = raw.replace("**", "").strip()
    # Strip trailing dates like "Applied 2024-01-15"
    import re
    s = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", s).strip()

    lower = s.lower()

    # Direct canonical match (case-insensitive)
    for canonical in CANONICAL_STATUSES:
        if lower == canonical.lower():
            return canonical

    # Alias lookup
    if lower in ALIASES:
        return ALIASES[lower]

    # DUPLICADO / DUP / Repost → Discarded
    if lower.startswith(("duplicado", "dup", "repost")):
        return "Discarded"

    # Em dash / empty → Discarded
    if s in ("—", "-", ""):
        return "Discarded"

    return None
