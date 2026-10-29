"""Document-disjoint spaCy NER experiments on genuine annotated case reports."""

import hashlib
import json
from pathlib import Path
import random
from .clinical_corpus import span_metrics


def document_split(corpus, seed=42):
    if len(corpus) < 20:
        raise ValueError("At least 20 independently annotated documents required")
    identifiers = [d["document_id"] for d in corpus]
    hashes = [hashlib.sha256(d["text"].encode()).hexdigest() for d in corpus]
    if len(set(identifiers)) != len(corpus) or len(set(hashes)) != len(corpus):
        raise ValueError(
            "Duplicate document keys or identical text would leak across splits"
        )
    ordered = sorted(identifiers)
    random.Random(seed).shuffle(ordered)
    a, b = int(len(ordered) * 0.7), int(len(ordered) * 0.85)
    return {"train": ordered[:a], "validation": ordered[a:b], "test": ordered[b:]}


def train(corpus_path, output, epochs=20, seed=42, progress_callback=None):
    if not isinstance(epochs, int) or not 1 <= epochs <= 200:
        raise ValueError("NER epochs must be a whole number from 1 through 200")
    import spacy
    from spacy.training import Example
    from spacy.util import fix_random_seed, minibatch, filter_spans

    fix_random_seed(seed)
    rng = random.Random(seed)
    corpus_path, output = Path(corpus_path), Path(output)
    corpus = json.loads(corpus_path.read_text())
    split = document_split(corpus, seed)
    lookup = {d["document_id"]: d for d in corpus}
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")
    examples = []
    exclusions = {
        "discontinuous": 0,
        "token_alignment": 0,
        "overlap_or_duplicate": 0,
        "boundary_whitespace": 0,
    }
    for key in split["train"]:
        row = lookup[key]
        doc = nlp.make_doc(row["text"])
        spans = []
        for entity in row["entities"]:
            if len(entity["spans"]) != 1:
                exclusions["discontinuous"] += 1
                continue
            span = doc.char_span(
                *entity["spans"][0], label=entity["label"], alignment_mode="strict"
            )
            if span is None:
                exclusions["token_alignment"] += 1
                continue
            if span[0].is_space or span[-1].is_space:
                exclusions["boundary_whitespace"] = (
                    exclusions.get("boundary_whitespace", 0) + 1
                )
                continue
            spans.append(span)
        selected = filter_spans(
            spans
        )  # longest span then input order, spaCy's documented flat-NER constraint
        exclusions["overlap_or_duplicate"] += len(spans) - len(selected)
        for span in selected:
            ner.add_label(span.label_)
        examples.append(
            Example.from_dict(
                doc,
                {"entities": [(s.start_char, s.end_char, s.label_) for s in selected]},
            )
        )
    if not any(example.reference.ents for example in examples):
        raise ValueError("No trainable token-aligned contiguous annotations")
    output.mkdir(parents=True, exist_ok=False)
    pipeline = output / "pipeline"
    optimizer = nlp.initialize(lambda: examples)

    def evaluate(keys):
        documents = [lookup[key] for key in keys]
        predictions = [
            [
                {"start": e.start_char, "end": e.end_char, "label": e.label_}
                for e in doc.ents
            ]
            for doc in nlp.pipe([d["text"] for d in documents], batch_size=8)
        ]
        return span_metrics([d["entities"] for d in documents], predictions)

    history = []
    best = -1.0
    for epoch in range(epochs):
        rng.shuffle(examples)
        losses = {}
        for batch in minibatch(examples, size=4):
            nlp.update(batch, sgd=optimizer, drop=0.2, losses=losses)
        measured = evaluate(split["validation"])
        entry = {
            "epoch": epoch + 1,
            "loss": float(losses["ner"]),
            "validation": measured["micro"],
        }
        history.append(entry)
        if measured["micro"]["f1"] > best:
            best = measured["micro"]["f1"]
            nlp.to_disk(pipeline)
        (output / "history.json").write_text(json.dumps(history, indent=2))
        if progress_callback:
            progress_callback(entry)
    nlp = spacy.load(pipeline)
    test = evaluate(split["test"])  # only chosen checkpoint sees independent test
    labels = sorted(ner.labels)
    unseen = sorted(
        {e["label"] for key in split["test"] for e in lookup[key]["entities"]}
        - set(labels)
    )
    report = {
        "method": "spaCy blank-English tok2vec + clinical-corpus NER",
        "seed": seed,
        "epochs": epochs,
        "splits": split,
        "split_rows": {k: len(v) for k, v in split.items()},
        "training_exclusions": exclusions,
        "validation_selection": "Highest exact contiguous-span micro F1; first checkpoint wins ties. No test-based checkpoint selection.",
        "best_validation_f1": best,
        "test_metrics": test,
        "test_labels_unseen_in_training": unseen,
        "labels": labels,
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "limitation": "Research model trained on published MACCROBAT2020 case reports, not clinically validated. Flat NER cannot output overlapping/discontinuous entities. Test denominator retains overlapping contiguous gold entities. Relations, assertion/negation, terminology normalization and clinical fact verification are not modeled. Document-disjoint is not a patient-identity guarantee.",
    }
    files = {
        str(p.relative_to(pipeline)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(pipeline.rglob("*"))
        if p.is_file()
    }
    card = {
        "source": "https://doi.org/10.6084/m9.figshare.9764942.v2",
        "license": "CC BY 4.0; J. Harry Caufield; MACCROBAT2020 annotations/source corpus; trained weights produced locally",
        "intended_use": "Academic clinical case-report entity recognition only",
        "limitations": report["limitation"],
        "evaluation": test,
        "training_report": "../evaluation.json",
        "files_sha256": files,
    }
    (pipeline / "research-model-card.json").write_text(json.dumps(card, indent=2))
    (output / "evaluation.json").write_text(json.dumps(report, indent=2))
    return report
