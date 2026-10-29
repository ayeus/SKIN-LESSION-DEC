"""Real annotation-type classification and case-report clustering/retrieval.

Annotation labels are never relabeled as confirmed diagnoses or relevance gold.
"""

import hashlib
import json
from collections import Counter
import pandas as pd
from sqlalchemy import select
from uuid import uuid4
from backend.app.db import ROOT, Session, Dataset, Audit
from backend.app.main import execute
from backend.app.services.text import analyze
from backend.app.services.tabular import profile
from scripts.acquire_public_clinical import SOURCE, LICENSE

TYPES = {
    "Disease_disorder",
    "Sign_symptom",
    "Medication",
    "Diagnostic_procedure",
    "Therapeutic_procedure",
}


def verify():
    root = ROOT / "processed/public/maccrobat2020"
    corpus = json.loads((root / "corpus.json").read_text())
    source = json.loads((root / "source-validation.json").read_text())
    mentions = []
    for document in corpus:
        for entity in document["entities"]:
            if entity["label"] not in TYPES or len(entity["spans"]) != 1:
                continue
            start, end = entity["spans"][0]
            # Observed mention plus unlabelled local context; no gold entity type enters predictors.
            context = document["text"][
                max(0, start - 160) : min(len(document["text"]), end + 160)
            ]
            mentions.append(
                {
                    "document_id": document["document_id"],
                    "text": entity["text"] + " [context] " + context,
                    "label": entity["label"],
                }
            )
    frame = pd.DataFrame(mentions)
    path = root / "mention_semantic_types.csv"
    frame.to_csv(path, index=False)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    scope = {
        "source": SOURCE,
        "license": LICENSE,
        "limitations": "Classification predicts author-annotated mention semantic type on gold mention boundaries, not document diagnosis, entity detection or patient risk. Local context includes the observed mention but never the gold type. Case reports are document-grouped; same-patient cross-publication independence is unknown. Only five prespecified types; discontinuous mentions excluded.",
    }
    with Session() as session:
        row = session.scalar(select(Dataset).where(Dataset.sha256 == digest))
        if row is None:
            row = Dataset(
                id=str(uuid4()),
                name="MACCROBAT2020: gold mention semantic-type contexts",
                modality="clinical_text",
                source=SOURCE,
                license=LICENSE,
                sha256=digest,
                path=str(path),
                profile=profile(frame),
            )
            session.add(row)
            session.add(
                Audit(
                    id=str(uuid4()), action="public_dataset_import", resource_id=row.id
                )
            )
        row.profile = {**row.profile, "research_scope": scope}
        session.commit()
        identifier = row.id
    provenance = {
        "id": identifier,
        "source": SOURCE,
        "license": LICENSE,
        "sha256": digest,
        "modality": "clinical_text",
    }
    p = {
        "task": "classify",
        "text_column": "text",
        "label_column": "label",
        "group_column": "document_id",
    }

    def classify(run_id):
        result = analyze(frame, p)
        result["data_scope"] = scope
        result["dataset_provenance"] = provenance
        return result

    run = execute("text", p, classify, identifier)
    documents = pd.DataFrame(
        [{"text": d["text"], "document_id": d["document_id"]} for d in corpus]
    )
    runs = [
        {
            "id": run["id"],
            "task": "gold mention semantic-type classification",
            "rows": len(frame),
            "label_distribution": dict(Counter(frame.label)),
            "evaluation": run["result"]["evaluation"],
            "train_rows": run["result"]["train_rows"],
            "test_rows": len(run["result"]["test_indices"]),
        }
    ]
    for p in [
        {"task": "cluster", "clusters": 5, "method": "kmeans"},
        {"task": "search", "query": "myocardial infarction", "method": "bm25"},
        {"task": "search", "query": "myocardial infarction", "method": "tfidf"},
    ]:

        def work(run_id):
            result = analyze(documents, p)
            result["data_scope"] = {
                "limitations": source["limitations"]
                + " Retrieval scores measure lexical relevance; no expert query relevance judgments supplied."
            }
            result["dataset_provenance"] = {
                "id": source["dataset_id"],
                "source": SOURCE,
                "license": LICENSE,
            }
            return result

        r = execute("text", p, work, source["dataset_id"])
        runs.append(
            {
                "id": r["id"],
                "task": p["task"],
                "method": p["method"],
                **(
                    {"silhouette_cosine": r["result"]["silhouette_cosine"]}
                    if p["task"] == "cluster"
                    else {
                        "returned_documents": len(r["result"]["results"]),
                        "relevance_evaluation": "NOT VERIFIED: no expert query judgments",
                    }
                ),
            }
        )
    report = {
        "source": SOURCE,
        "dataset_id": source["dataset_id"],
        "mention_dataset_id": identifier,
        "runs": runs,
        "limitation": scope["limitations"],
    }
    (root / "verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
