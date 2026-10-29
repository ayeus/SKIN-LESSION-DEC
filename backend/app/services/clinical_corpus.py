"""Strict BRAT entity ingestion and exact-span research evaluation.

Relations, events and attributes are counted but not silently interpreted as facts.
Discontinuous mentions remain intact in the gold record; contiguous-only NER
training/evaluation explicitly reports its narrower scope.
"""

import re
from collections import Counter


def parse_brat(text, annotations):
    entities = []
    seen = set()
    other = Counter()
    for line in annotations.splitlines():
        if not line:
            continue
        if not line.startswith("T"):
            other[line[0]] += 1
            continue
        fields = line.split("\t", 2)
        if len(fields) != 3 or fields[0] in seen:
            raise ValueError("Malformed or duplicate BRAT entity ID")
        identifier, description, surface = fields
        seen.add(identifier)
        label, separator, offsets = description.partition(" ")
        if not separator or not label:
            raise ValueError("BRAT entity requires a type and character offsets")
        spans = []
        for segment in offsets.split(";"):
            bounds = segment.split()
            if len(bounds) != 2:
                raise ValueError("Each BRAT segment requires start/end offsets")
            start, end = map(int, bounds)
            if not 0 <= start < end <= len(text) or (spans and start < spans[-1][1]):
                raise ValueError(
                    "Invalid, overlapping or unordered BRAT segment offsets"
                )
            spans.append([start, end])
        actual = " ".join(text[start:end] for start, end in spans)
        normalize = lambda value: re.sub(r"\s+", " ", value).strip()
        if normalize(actual) != normalize(surface):
            raise ValueError("BRAT annotation surface does not match source offsets")
        entities.append(
            {"id": identifier, "label": label, "spans": spans, "text": surface}
        )
    if not entities:
        raise ValueError("Document has no genuine entity annotations")
    return {"entities": entities, "uninterpreted_record_counts": dict(other)}


def span_metrics(gold_documents, predicted_documents):
    """Exact contiguous (start,end,type), including overlap in the gold denominator."""
    if len(gold_documents) != len(predicted_documents):
        raise ValueError("Prediction and gold document counts differ")
    counts = Counter()
    per_label = {}
    discontinuous = 0
    for gold, predicted in zip(gold_documents, predicted_documents):
        expected = set()
        for entity in gold:
            if len(entity["spans"]) != 1:
                discontinuous += 1
                continue
            start, end = entity["spans"][0]
            expected.add((start, end, entity["label"]))
        actual = {(e["start"], e["end"], e["label"]) for e in predicted}
        for label in {v[2] for v in expected | actual}:
            label_counts = per_label.setdefault(label, Counter())
            a = {v for v in actual if v[2] == label}
            b = {v for v in expected if v[2] == label}
            for counter in [counts, label_counts]:
                counter["true_positive"] += len(a & b)
                counter["false_positive"] += len(a - b)
                counter["false_negative"] += len(b - a)

    def metrics(c):
        tp, fp, fn = (
            c[key] for key in ["true_positive", "false_positive", "false_negative"]
        )
        return {
            **dict(c),
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "gold_mentions": tp + fn,
        }

    return {
        "micro": metrics(counts),
        "per_label": {k: metrics(v) for k, v in sorted(per_label.items())},
        "excluded_discontinuous_mentions": discontinuous,
        "scope": "Exact contiguous spans and types; overlapping contiguous gold mentions retained in recall denominator. Discontinuous mentions excluded and counted; not full BRAT/event/relation evaluation.",
    }
