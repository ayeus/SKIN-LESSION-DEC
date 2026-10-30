"""Versioned local NLM MeSH descriptor inventory; no clinical notes sent to NLM."""

import gzip
import hashlib
import json
from collections import defaultdict
import xml.etree.ElementTree as ET
from backend.app.db import ROOT


def normalize(value):
    return " ".join(value.casefold().split())


def prepare():
    path = ROOT / "raw/mesh-2026/desc2026.gz"
    with path.open("rb") as stream:
        if stream.read(2) != b"\x1f\x8b":
            raise ValueError(
                "Expected original gzip bytes, not automatically decoded XML under a gzip filename"
            )
    records = []
    index = defaultdict(list)
    with gzip.open(path, "rb") as stream:
        for event, element in ET.iterparse(stream, events=["end"]):
            if element.tag != "DescriptorRecord":
                continue
            identifier = element.findtext("DescriptorUI")
            label = element.findtext("DescriptorName/String")
            if not identifier or not label:
                raise ValueError("MeSH descriptor missing identifier/name")
            preferred = element.find("./ConceptList/Concept[@PreferredConceptYN='Y']")
            scope = preferred.findtext("ScopeNote") if preferred is not None else None
            aliases = sorted(
                {
                    node.text
                    for node in element.findall(
                        "./ConceptList/Concept/TermList/Term/String"
                    )
                    if node.text
                }
                | {label}
            )
            row = {
                "id": identifier,
                "label": label,
                "definition": scope or "",
                "entry_terms": aliases,
            }
            position = len(records)
            records.append(row)
            for term in {normalize(term) for term in aliases}:
                index[term].append(position)
            element.clear()
    if not records:
        raise ValueError("No actual descriptors parsed")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata = {
        "source": "https://www.nlm.nih.gov/databases/download/mesh.html",
        "source_url": "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz",
        "source_sha256": digest,
        "version": "2026 descriptor snapshot",
        "attribution": "Courtesy of the U.S. National Library of Medicine",
        "terms": "https://www.nlm.nih.gov/databases/download/terms_and_conditions.html",
        "limitations": "Fixed snapshot, not guaranteed the most current/accurate NLM data. NLM does not endorse this application. Dictionary candidates and lexical context scores are not verified clinical senses, calibrated confidence or clinical fact verification.",
    }
    output = ROOT / "processed/public/mesh-2026"
    output.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": metadata, "records": records, "index": dict(index)}
    (output / "inventory.json").write_text(json.dumps(payload, ensure_ascii=False))
    summary = {
        **metadata,
        "descriptor_records": len(records),
        "indexed_entry_terms": len(index),
        "ambiguous_entry_terms": sum(len(v) > 1 for v in index.values()),
    }
    (output / "verification.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(
        "Actual ambiguous examples",
        [
            (term, [records[i]["label"] for i in positions])
            for term, positions in index.items()
            if term in ["cold", "mole", "ms", "depression", "mass", "pt"]
        ],
    )
    return summary


if __name__ == "__main__":
    prepare()
