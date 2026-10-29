"""Acquire licensed MACCROBAT case reports; never substitute hospital notes."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile
import pandas as pd
from sqlalchemy import select
from backend.app.db import ROOT, Session, Dataset, Audit
from backend.app.services.clinical_corpus import parse_brat
from backend.app.services.tabular import profile
from scripts.acquire_public_data import acquire

SOURCE = "https://doi.org/10.6084/m9.figshare.9764942.v2"
LICENSE = (
    "CC BY 4.0; J. Harry Caufield; MACCROBAT2020; DOI 10.6084/m9.figshare.9764942.v2"
)


def acquire_corpus():
    root = ROOT / "raw/maccrobat2020"
    metadata = json.loads(
        acquire(
            "https://api.figshare.com/v2/articles/9764942/versions/2",
            root / "article-v2.json",
            "CC BY 4.0",
            SOURCE,
        ).read_text()
    )
    if metadata["license"]["name"] != "CC BY 4.0":
        raise ValueError("Source license requires review")
    resource = next(v for v in metadata["files"] if v["name"] == "MACCROBAT2020.zip")
    archive_path = acquire(
        resource["download_url"], root / resource["name"], LICENSE, SOURCE
    )
    with archive_path.open("rb") as stream:
        md5 = hashlib.file_digest(stream, "md5").hexdigest()
    if (
        md5 != resource["computed_md5"]
        or archive_path.stat().st_size != resource["size"]
    ):
        raise ValueError("Archive does not match publisher MD5/size")
    corpus = []
    with ZipFile(archive_path) as archive:
        files = {}
        for item in archive.infolist():
            if "__MACOSX" in item.filename or item.is_dir():
                continue
            name = Path(item.filename).name
            if not name.endswith((".txt", ".ann")):
                continue
            if item.file_size > 2 * 1024**2 or name in files:
                raise ValueError("Oversized or duplicate corpus member")
            files[name] = item
        texts = {Path(v).stem for v in files if v.endswith(".txt")}
        annotations = {Path(v).stem for v in files if v.endswith(".ann")}
        if texts != annotations or len(texts) != 200:
            raise ValueError("Expected 200 one-to-one text/annotation pairs")
        for identifier in sorted(texts):
            if not identifier.isdigit():
                raise ValueError("Document key must be the source PMID")
            text = archive.read(files[identifier + ".txt"]).decode("utf-8")
            gold = parse_brat(
                text, archive.read(files[identifier + ".ann"]).decode("utf-8")
            )
            corpus.append({"document_id": identifier, "text": text, **gold})
    digests = [hashlib.sha256(d["text"].encode()).hexdigest() for d in corpus]
    if len(set(digests)) != len(digests):
        raise ValueError("Identical documents require grouping review before split")
    output = ROOT / "processed/public/maccrobat2020"
    output.mkdir(parents=True, exist_ok=True)
    (output / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False))
    path = output / "documents.csv"
    frame = pd.DataFrame(
        [{"document_id": d["document_id"], "text": d["text"]} for d in corpus]
    )
    frame.to_csv(path, index=False)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    scope = {
        "source": SOURCE,
        "license": LICENSE,
        "documents": len(corpus),
        "entities": sum(len(d["entities"]) for d in corpus),
        "entity_types": dict(
            Counter(e["label"] for d in corpus for e in d["entities"])
        ),
        "discontinuous_mentions": sum(
            len(e["spans"]) != 1 for d in corpus for e in d["entities"]
        ),
        "publisher_md5_verified": True,
        "limitations": "Published case-report narratives with manual annotations; not institutional EHR notes, representative clinical populations or validated clinical decision support. Document-disjoint splits cannot establish patient independence across publications. Relations/events/attributes remain uninterpreted unless explicitly implemented.",
    }
    with Session() as session:
        row = session.scalar(select(Dataset).where(Dataset.sha256 == digest))
        if row is None:
            row = Dataset(
                id=str(uuid4()),
                name="MACCROBAT2020: published clinical case reports",
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
        scope["dataset_id"] = row.id
    (output / "source-validation.json").write_text(json.dumps(scope, indent=2))
    print(json.dumps(scope, indent=2))
    return corpus, scope


if __name__ == "__main__":
    acquire_corpus()
