"""Free-form query -> structured scan plan.

One LLM call (cached) turns a natural-language query into weighted terms with
hard-required qualifying adjectives, named entities to also search, and the
user's expressed stance (display only). Falls back to the deterministic
heuristic in lib/relevance when the LLM is unavailable or returns bad JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from .llm import chat_json
from .relevance import (
    Term,
    extract_core_subject,
    tokenize,
    is_generic_token,
    singularize,
)


@dataclass
class QueryPlan:
    subject: str
    terms: list[Term]
    entities: list[str] = field(default_factory=list)
    stance: str = ""


_SYSTEM = (
    "You are a query analyst for a social-media research agent. Read the user's "
    "free-form query and return a strict JSON plan. Assign each meaningful term a "
    "weight in [0,1] by how essential it is to the subject. A qualifying ADJECTIVE "
    "(wireless, budget, noise-cancelling) is REQUIRED (required=true). The head NOUN "
    "is high-weight but required=false. A bare year or number (2026) or generic word "
    "(best, latest, review) gets weight <= 0.1 and required=false. For each term give "
    "morphological + synonym variants (wireless -> [wireless, bluetooth, bt]). Extract "
    "named entities to also search (brands/products) and the user's stance/opinion "
    "(for display only, never used to bias search)."
)
_SCHEMA_HINT = (
    'Output JSON: {"subject": "...", "terms": [{"term": "...", "weight": 0.0-1.0, '
    '"required": true|false, "variants": ["..."]}], "entities": ["..."], "stance": "..."}'
)


def _heuristic_plan(raw: str) -> QueryPlan:
    subject = extract_core_subject(raw) or raw
    terms: list[Term] = []
    for tok in tokenize(subject):
        weight = 0.05 if is_generic_token(tok) else 1.0
        variants = [tok]
        sing = singularize(tok)
        if sing:
            variants.append(sing)
        terms.append(Term(tok, weight, required=False, variants=variants))
    return QueryPlan(subject=subject, terms=terms, entities=[], stance="")


@lru_cache(maxsize=256)
def parse_query(raw: str) -> QueryPlan:
    # Cached by raw string; callers MUST treat the returned QueryPlan as read-only
    # (mutating plan.terms/entities would poison the cache for the same query).
    raw = (raw or "").strip()
    if not raw:
        return QueryPlan(subject="", terms=[], entities=[], stance="")
    try:
        data = chat_json(_SYSTEM, f"{raw}\n\n{_SCHEMA_HINT}", max_tokens=600)
        terms = [
            Term(
                term=str(t["term"]),
                weight=float(t.get("weight", 0.5)),
                required=bool(t.get("required", False)),
                variants=[str(v) for v in t.get("variants", [])],
            )
            for t in data.get("terms", [])
            if t.get("term")
        ]
        if not terms:
            return _heuristic_plan(raw)
        return QueryPlan(
            subject=str(data.get("subject") or extract_core_subject(raw) or raw),
            terms=terms,
            entities=[str(e) for e in data.get("entities", [])],
            stance=str(data.get("stance") or ""),
        )
    except Exception:
        return _heuristic_plan(raw)
