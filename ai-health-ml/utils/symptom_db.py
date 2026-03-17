from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from utils.config import DATA_DIR
from utils.hf_client import call_huggingface_api


SYMPTOM_DB_PATH = DATA_DIR / "symptom_db.json"


@dataclass
class SymptomEntry:
    name: str
    aliases: list[str]
    related: list[str]
    source: str = "learned"


def _clean_text(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip().lower())
    t = t.strip(" ,.;:()[]{}\"'")
    return t


def _dedup(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for x in items:
        t = _clean_text(x)
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _ensure_db_file() -> None:
    if not SYMPTOM_DB_PATH.exists():
        SYMPTOM_DB_PATH.write_text("[]", encoding="utf-8")


def load_symptom_db() -> list[SymptomEntry]:
    _ensure_db_file()
    try:
        raw = json.loads(SYMPTOM_DB_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[SymptomEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = _clean_text(str(item.get("name", "")))
            if not name:
                continue
            aliases = item.get("aliases", [])
            related = item.get("related", [])
            out.append(
                SymptomEntry(
                    name=name,
                    aliases=_dedup(aliases if isinstance(aliases, list) else []),
                    related=_dedup(related if isinstance(related, list) else []),
                    source=str(item.get("source", "learned") or "learned"),
                )
            )
        return out
    except Exception:
        return []


def save_symptom_db(entries: list[SymptomEntry]) -> None:
    _ensure_db_file()
    data_out = [
        {"name": e.name, "aliases": _dedup(e.aliases), "related": _dedup(e.related), "source": e.source}
        for e in sorted(entries, key=lambda x: x.name)
    ]
    SYMPTOM_DB_PATH.write_text(json.dumps(data_out, indent=2), encoding="utf-8")


def find_symptom(name_or_alias: str, entries: Optional[list[SymptomEntry]] = None) -> Optional[SymptomEntry]:
    q = _clean_text(name_or_alias)
    if not q:
        return None
    db = entries if entries is not None else load_symptom_db()
    for e in db:
        if e.name == q:
            return e
        if q in set(e.aliases):
            return e
    return None


def add_symptom(symptom: str, *, source: str = "user_input") -> bool:
    """
    Add symptom to symptom_db.json if missing.
    Returns True if a new entry was added.
    """
    name = _clean_text(symptom)
    if not name:
        return False
    entries = load_symptom_db()
    if find_symptom(name, entries) is not None:
        return False
    entries.append(SymptomEntry(name=name, aliases=[], related=[], source=source))
    save_symptom_db(entries)
    return True


def upsert_related(symptom: str, related: list[str], *, source: str = "learned") -> bool:
    """
    Merge related symptoms into an existing entry (or create it).
    Returns True if something changed.
    """
    name = _clean_text(symptom)
    if not name:
        return False
    rel = _dedup(related)
    if not rel:
        return False

    entries = load_symptom_db()
    changed = False
    e = find_symptom(name, entries)
    if e is None:
        entries.append(SymptomEntry(name=name, aliases=[], related=rel, source=source))
        changed = True
    else:
        before = set(e.related)
        merged = _dedup([*e.related, *rel])
        if set(merged) != before:
            e.related = merged
            changed = True
        # If entry was purely user_input but we enriched it, mark learned
        if e.source == "user_input" and source != "user_input":
            e.source = source
            changed = True

    if changed:
        save_symptom_db(entries)
    return changed


def expand_related_online(symptom: str, *, limit: int = 8) -> list[str]:
    """
    Ask HF for related symptoms to a symptom phrase.
    Returns list of phrases (plain text, lowercased & cleaned).
    """
    name = _clean_text(symptom)
    if not name:
        return []
    prompt = (
        f"What are related symptoms to {name}? "
        f"Return ONLY a Python list of strings (max {limit}).\n"
        "Answer:"
    )
    text = call_huggingface_api(prompt, model_env="HF_DISEASE_MODEL")
    if not text:
        return []
    items = re.findall(r"['\"]([^'\"]{2,80})['\"]", text)
    out = []
    for it in items:
        t = _clean_text(it)
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def phrase_to_token(phrase: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean_text(phrase)).strip("_")


def expand_symptom_tokens(tokens: list[str]) -> set[str]:
    """
    Expand a set of underscore symptom tokens using symptom_db related links.
    - tokens are like "eye_pain"
    - returns expanded tokens (includes originals)
    """
    base = {t for t in (tokens or []) if t}
    if not base:
        return set()

    db = load_symptom_db()
    # Build token -> entry mapping using name + aliases
    token_to_entry: dict[str, SymptomEntry] = {}
    for e in db:
        token_to_entry[phrase_to_token(e.name)] = e
        for a in e.aliases:
            token_to_entry[phrase_to_token(a)] = e

    expanded = set(base)
    for t in list(base):
        e = token_to_entry.get(t)
        if not e:
            continue
        for rel in e.related:
            rt = phrase_to_token(rel)
            if rt:
                expanded.add(rt)
    return expanded

