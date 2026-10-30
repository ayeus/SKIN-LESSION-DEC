"""Local context-sensitive descriptor ranking; never deterministic clinical truth."""

from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from ..db import ROOT


def inventory_path():
    return Path(
        os.getenv(
            "DERMA_MESH_INVENTORY",
            str(ROOT / "processed/public/mesh-2026/inventory.json"),
        )
    )


@lru_cache(maxsize=1)
def read_inventory(path, mtime, size):
    if size > 100 * 1024**2:
        raise ValueError("Terminology inventory exceeds 100 MiB local limit")
    content = Path(path).read_bytes()
    data = json.loads(content)
    if not all(key in data for key in ["metadata", "records", "index"]):
        raise ValueError("Invalid terminology inventory schema")
    return data, hashlib.sha256(content).hexdigest()


def contextual_candidates(term, context):
    path = inventory_path()
    if not path.is_file():
        raise ValueError(
            "BLOCKED: acquire and prepare the versioned public MeSH inventory first"
        )
    stat = path.stat()
    data, digest = read_inventory(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    term = " ".join(term.casefold().split())
    context = context.strip()
    if not term or not context:
        raise ValueError("Provide both an actual term and its local context")
    matcher = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)")
    matches = {}
    for entry, positions in data["index"].items():
        if entry == term or matcher.search(entry):
            for position in positions:
                matches.setdefault(position, []).append(entry)
    positions = sorted(matches)
    if len(positions) > 50:
        raise ValueError("More than 50 dictionary candidates; use a more specific term")
    candidates = [
        {**data["records"][i], "matched_entry_terms": matches[i]} for i in positions
    ]
    base = {
        "term": term,
        "inventory": data["metadata"],
        "inventory_sha256": digest,
        "candidate_count": len(candidates),
        "candidate_generation": "Exact or word-boundary phrase matches within genuine NLM entry terms. Broader matches can include related subtypes, not only distinct senses; definitions and context require review.",
        "limitation": data["metadata"]["limitations"],
        "context_sent_to_external_service": False,
    }
    if not candidates:
        return {
            **base,
            "status": "unresolved",
            "sense_candidates": [],
            "reason": "No matching entry term in this snapshot; no invented abbreviation expansion or fallback mapping.",
        }
    pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
    documents = [
        pattern.sub(" ", row["label"] + " " + row["definition"]) for row in candidates
    ]
    query = pattern.sub(" ", context)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    try:
        matrix = vectorizer.fit_transform(documents)
        query_vector = vectorizer.transform([query])
        scores = (matrix @ query_vector.T).toarray().ravel()
        terms = vectorizer.get_feature_names_out()
    except ValueError as error:
        if "empty vocabulary" not in str(error):
            raise
        scores = np.zeros(len(candidates))
        matrix = None
        terms = []
    ranking = []
    for i, row in enumerate(candidates):
        overlap = []
        if matrix is not None:
            products = matrix[i].multiply(query_vector).toarray().ravel()
            overlap = [
                str(terms[j]) for j in np.argsort(-products)[:10] if products[j] > 0
            ]
        ranking.append(
            {
                **row,
                "context_similarity": float(scores[i]),
                "shared_context_terms": overlap,
            }
        )
    ranking.sort(key=lambda row: (-row["context_similarity"], row["id"]))
    evidence = any(row["context_similarity"] > 0 for row in ranking)
    return {
        **base,
        "status": "ranked_for_human_review" if evidence else "unresolved",
        "sense_candidates": ranking,
        "method": "TF-IDF cosine over genuine MeSH descriptor labels/scope notes; target phrase removed to require contextual evidence. No score threshold is clinically validated.",
        "uncertainty": "Lexical ranking is not calibrated sense certainty. A single dictionary match, ties, missing concepts and domain mismatch require review. No diagnosis or abbreviation meaning is asserted as fact.",
    }
