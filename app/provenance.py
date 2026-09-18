"""The citation check. Deterministic code, no model call.

Retrieval returning ids is not provenance. The model authors the `passage` and
`source_ref` strings itself, and what it was shown proves nothing about what it
then wrote down. This module establishes the property: the cited source must be
one of the documents this run actually loaded, and the quoted text must appear
verbatim - whitespace-normalised - inside it.

A row that fails is DEMOTED, never dropped. Deleting it is how a run ends up
looking better evidenced than it was.

This is also most of the answer to prompt injection. A poisoned submission can
mislead the model; it cannot manufacture a citation that does not exist.
"""
from __future__ import annotations

import re

from .schema import Evidence

_WS = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def check_evidence(items: list[Evidence], sources: dict[str, str]) -> list[Evidence]:
    """Return the rows with `supported` set honestly.

    `sources` maps a source_ref to the full text it names - the submission, the
    assignment prompt, the lecture notes. Anything not in here was never loaded
    by this run, so a reference to it is unverifiable by definition.
    """
    checked: list[Evidence] = []
    for item in items:
        if item.source_ref not in sources:
            checked.append(item.model_copy(update={
                "supported": False,
                "note": f"could not establish: {item.source_ref} was not loaded by this run",
            }))
            continue
        if _normalise(item.passage) not in _normalise(sources[item.source_ref]):
            checked.append(item.model_copy(update={
                "supported": False,
                "note": f"could not establish: passage not found verbatim in {item.source_ref}",
            }))
            continue
        checked.append(item.model_copy(update={"supported": True, "note": None}))
    return checked


def unsupported(items: list[Evidence]) -> list[Evidence]:
    return [i for i in items if not i.supported]
