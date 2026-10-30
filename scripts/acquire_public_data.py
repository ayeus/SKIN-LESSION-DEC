"""Official-source acquisition for owner-authorized public academic research.
No synthetic observations; keeps licensing, original bytes and SHA256 provenance.
Run: .venv/bin/python -m scripts.acquire_public_data [--lesion-images]
"""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
import pandas as pd
import requests

ROOT = Path("data").resolve()


def acquire(url, destination, license, source, expected=None):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT):
        raise ValueError(
            "Acquisition destination must be within configured data storage"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt = destination.with_suffix(destination.suffix + ".provenance.json")
    if destination.exists():
        if not receipt.is_file():
            raise ValueError(
                "Existing raw file has no source receipt; review/move it before a fresh download"
            )
        prior = json.loads(receipt.read_text())
        if prior.get("url") != url:
            raise ValueError(
                "Existing raw file belongs to a different source URL; refuse relabeling"
            )
        with destination.open("rb") as stream:
            current = hashlib.file_digest(stream, "sha256").hexdigest()
        if current != prior.get("sha256"):
            raise ValueError(
                "Existing raw file changed since acquisition; review before reuse"
            )
    if not destination.exists():
        part = destination.with_suffix(destination.suffix + ".part")
        offset = part.stat().st_size if part.exists() else 0
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
            resource = destination.parent / "archive-resource.json"
            if resource.is_file():
                metadata = json.loads(resource.read_text())
                if metadata.get("url") == url and metadata.get("etag"):
                    headers["If-Range"] = metadata["etag"]
        with requests.get(
            url, stream=True, timeout=(15, 90), headers=headers
        ) as response:
            response.raise_for_status()
            append = response.status_code == 206 and offset > 0
            if response.status_code == 206 and not response.headers.get(
                "Content-Range", ""
            ).startswith(f"bytes {offset}-"):
                raise ValueError("Server returned inconsistent byte range")
            if not append:
                offset = 0
            total = int(response.headers.get("Content-Length", 0))
            transferred = 0
            milestone = 0
            with part.open("ab" if append else "wb") as output:
                for chunk in response.raw.stream(1024 * 1024, decode_content=False):
                    output.write(chunk)
                    transferred += len(chunk)
                    if offset + transferred > 12 * 1024**3:
                        raise ValueError("Download exceeds configured 12 GiB maximum")
                    if transferred // (64 * 1024**2) > milestone:
                        milestone = transferred // (64 * 1024**2)
                        print(
                            json.dumps(
                                {
                                    "downloading": destination.name,
                                    "bytes_on_disk": offset + transferred,
                                }
                            ),
                            flush=True,
                        )
            if total and transferred != total:
                raise ValueError("Incomplete download")
        part.rename(destination)
    with destination.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if expected and digest != expected:
        raise ValueError("Publisher checksum mismatch: " + str(destination))
    provenance = {
        "url": url,
        "source": source,
        "license": license,
        "sha256": digest,
        "bytes": destination.stat().st_size,
        "publisher_checksum_verified": bool(expected),
    }
    destination.with_suffix(destination.suffix + ".provenance.json").write_text(
        json.dumps(provenance, indent=2)
    )
    print(
        json.dumps({"file": str(destination.relative_to(ROOT)), **provenance}),
        flush=True,
    )
    return destination


def mimic():
    source = "https://physionet.org/content/mimic-iv-demo/2.2/"
    base = "https://physionet.org/files/mimic-iv-demo/2.2/"
    directory = ROOT / "raw/mimic-iv-demo-2.2"
    license = "Open Data Commons Open Database License v1.0"
    acquire(base + "LICENSE.txt", directory / "LICENSE.txt", license, source)
    sums = acquire(
        base + "SHA256SUMS.txt", directory / "SHA256SUMS.txt", license, source
    )
    checks = {
        line.split()[1].lstrip("*"): line.split()[0]
        for line in sums.read_text().splitlines()
        if len(line.split()) == 2
    }
    report = {}
    for table in ("patients", "admissions", "diagnoses_icd", "d_icd_diagnoses"):
        relative = f"hosp/{table}.csv.gz"
        if relative not in checks:
            raise ValueError("File absent from publisher checksums: " + relative)
        path = acquire(
            base + relative, directory / relative, license, source, checks[relative]
        )
        frame = pd.read_csv(path)
        out = ROOT / "processed/public/mimic" / f"{table}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        report[table] = {
            "rows": len(frame),
            "columns": list(frame.columns),
            "derived_csv": str(out.relative_to(ROOT)),
        }
    report["limitations"] = (
        "Real de-identified public subset. Excludes free-text notes. Shifted dates and selected patients cannot represent observed daily hospital demand. Do not infer actual birthdates from anchor fields."
    )
    (directory / "import-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


def nhanes():
    source = "https://wwwn.cdc.gov/Nchs/Nhanes/Search/DataPage.aspx?Cycle=2017-2018"
    directory = ROOT / "raw/nhanes-2017-2018"
    base = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/"
    tables = {}
    for name in ("DEMO_J", "BMX_J", "PAQ_J", "SLQ_J", "DBQ_J"):
        acquire(
            base + name + ".htm",
            directory / (name + ".htm"),
            "CDC public-use data; NHANES data-user restrictions apply",
            source,
        )
        path = acquire(
            base + name + ".xpt",
            directory / (name + ".xpt"),
            "CDC public-use data; NHANES data-user restrictions apply",
            source,
        )
        if not path.read_bytes().startswith(b"HEADER RECORD"):
            raise ValueError("Invalid SAS transport download")
        tables[name] = pd.read_sas(path, format="xport")
        if tables[name].SEQN.duplicated().any():
            raise ValueError("NHANES component has repeated participant keys")
    frame = tables["DEMO_J"]
    for name in ("BMX_J", "PAQ_J", "SLQ_J", "DBQ_J"):
        frame = frame.merge(tables[name], on="SEQN", how="left", validate="one_to_one")
    adults = frame.loc[frame.RIDAGEYR >= 20].copy()
    # Preserve original codes and missingness: variable-specific refusal/skip cleaning
    # must be derived from downloaded manuals before any behavioral modeling.
    out = ROOT / "processed/public/nhanes/adults_raw_codes.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    adults.to_csv(out, index=False)
    report = {
        "source_rows": len(frame),
        "adult_rows": len(adults),
        "adult_inclusion": "RIDAGEYR >= 20",
        "join": "one-to-one SEQN within 2017–2018 cycle",
        "columns": list(adults.columns),
        "status": "Downloaded and joined; behavioral sentinel-code cleaning NOT VERIFIED; no research model fitted",
        "limitations": "Retain survey weights, strata and PSU. Unweighted analysis is exploratory, not US population inference. Top-coded age and questionnaire skip/refusal codes require documentation.",
    }
    (directory / "import-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


def lesions(images=False):
    source = "https://challenge.isic-archive.com/data/"
    base = "https://isic-archive.s3.amazonaws.com/challenges/2018/"
    directory = ROOT / "raw/isic2018-task3"
    license = "CC-BY-NC 4.0; attribution: HAM10000 ViDIR Group and ISIC challenge contributors, see official source"
    for name in (
        "ISIC2018_Task3_Training_LesionGroupings.csv",
        "ISIC2018_Task3_Training_GroundTruth.zip",
    ):
        acquire(base + name, directory / name, license, source)
    if images:
        acquire(
            base + "ISIC2018_Task3_Training_Input.zip",
            directory / "ISIC2018_Task3_Training_Input.zip",
            license,
            source,
        )
    print(
        json.dumps(
            {
                "lesions": "Official training metadata acquired. Image archive "
                + ("acquired" if images else "not requested")
                + ". Never combine overlapping HAM10000/ISIC sources as independent train/test data."
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesion-images", action="store_true")
    parser.add_argument(
        "--source", choices=["all", "mimic", "nhanes", "lesions"], default="all"
    )
    args = parser.parse_args()
    failures = []
    for name, work in [
        ("mimic", mimic),
        ("nhanes", nhanes),
        ("lesions", lambda: lesions(args.lesion_images)),
    ]:
        if args.source in ("all", name):
            try:
                work()
            except Exception as error:
                failures.append({"source": name, "error": str(error)})
                print(json.dumps(failures[-1]), flush=True)
    if failures:
        raise SystemExit(1)
