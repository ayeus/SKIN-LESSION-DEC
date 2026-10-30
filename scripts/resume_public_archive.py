"""Verified bounded HTTP-range resume for the two official public ISIC archives.

Stop other writers first. Source ETag/size, exact byte ranges, per-chunk local
checksums and ZIP CRCs are checked. ETags/local hashes are not publisher SHA256.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import time
from zipfile import ZipFile
import requests
from scripts.acquire_public_data import ROOT

SOURCES = {
    "lesions": (
        "isic2018-task3",
        "ISIC2018_Task3_Training_Input.zip",
        "CC-BY-NC 4.0; ViDIR/HAM10000 and ISIC2018 contributor attribution required",
    ),
    "segmentation": (
        "isic2018-task1-validation",
        "ISIC2018_Task1-2_Validation_Input.zip",
        "CC0; cite Codella et al. ISIC2018",
    ),
}


def fetch_range(url, path, start, end, total, etag):
    expected = end - start + 1
    receipt = path.with_suffix(".json")
    if path.is_file() and receipt.is_file():
        prior = json.loads(receipt.read_text())
        if (
            prior.get("url") == url
            and prior.get("etag") == etag
            and prior.get("start") == start
            and prior.get("end") == end
            and path.stat().st_size == expected
            and hashlib.sha256(path.read_bytes()).hexdigest() == prior.get("sha256")
        ):
            return path
        raise ValueError("Cached range changed or belongs to another source version")
    temporary = path.with_suffix(".partial")
    for attempt in range(3):
        try:
            with requests.get(
                url,
                headers={
                    "Range": f"bytes={start}-{end}",
                    "If-Match": etag,
                    "Accept-Encoding": "identity",
                },
                stream=True,
                timeout=(15, 60),
            ) as response:
                response.raise_for_status()
                if (
                    response.status_code != 206
                    or response.headers.get("Content-Range")
                    != f"bytes {start}-{end}/{total}"
                    or response.headers.get("ETag") != etag
                    or response.headers.get("Content-Encoding")
                ):
                    raise ValueError(
                        "Source returned inconsistent range, encoding or version"
                    )
                count = 0
                digest = hashlib.sha256()
                with temporary.open("wb") as stream:
                    for chunk in response.iter_content(256 * 1024):
                        count += len(chunk)
                        if count > expected:
                            raise ValueError("Oversized range response")
                        digest.update(chunk)
                        stream.write(chunk)
                if count != expected:
                    raise ValueError("Incomplete range response")
            temporary.replace(path)
            receipt.write_text(
                json.dumps(
                    {
                        "url": url,
                        "etag": etag,
                        "start": start,
                        "end": end,
                        "sha256": digest.hexdigest(),
                    }
                )
            )
            return path
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError("Range acquisition did not complete")


def download(url, destination, license, workers=6, chunk_bytes=4 * 1024**2):
    if not 1 <= workers <= 8:
        raise ValueError("Use 1–8 concurrent public object requests")
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        raise ValueError(
            "Archive already exists; validate/reuse its provenance instead"
        )
    response = requests.head(url, timeout=30)
    response.raise_for_status()
    total = int(response.headers["Content-Length"])
    etag = response.headers["ETag"]
    if not 0 < total <= 12 * 1024**3:
        raise ValueError("Archive exceeds configured size limit")
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.is_file() else 0
    if offset > total:
        raise ValueError("Partial archive exceeds source length")
    resource = destination.parent / "archive-resource.json"
    if offset:
        if not resource.is_file():
            raise ValueError(
                "Existing partial archive needs its original ETag/size receipt before resume"
            )
        previous = json.loads(resource.read_text())
        if (
            previous.get("url") != url
            or previous.get("etag") != etag
            or previous.get("expected_bytes") != total
        ):
            raise ValueError("Source version differs from original partial archive")
    metadata = {"url": url, "etag": etag, "expected_bytes": total}
    resource.write_text(json.dumps(metadata, indent=2))
    ranges = destination.with_suffix(destination.suffix + ".ranges")
    ranges.mkdir(exist_ok=True)
    plans = [
        (start, min(start + chunk_bytes, total) - 1)
        for start in range(offset, total, chunk_bytes)
    ]
    completed = offset
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                fetch_range, url, ranges / f"{start}-{end}.bin", start, end, total, etag
            ): (start, end)
            for start, end in plans
        }
        for future in as_completed(futures):
            future.result()
            start, end = futures[future]
            completed += end - start + 1
            print(
                json.dumps(
                    {
                        "archive": destination.name,
                        "validated_bytes_in_prefix_and_chunks": completed,
                        "expected_bytes": total,
                    }
                ),
                flush=True,
            )
    # Only append after every chunk is validated. Interrupted assembly requires
    # explicit review, rather than silently reusing a shifted chunk partition.
    assembly = destination.with_suffix(destination.suffix + ".assembly")
    if assembly.exists():
        raise ValueError("Interrupted assembly exists; review before retry")
    import shutil

    with assembly.open("xb") as output:
        if partial.is_file():
            with partial.open("rb") as source:
                shutil.copyfileobj(source, output)
        for start, end in plans:
            with (ranges / f"{start}-{end}.bin").open("rb") as source:
                shutil.copyfileobj(source, output)
    if assembly.stat().st_size != total:
        raise ValueError("Assembled archive size mismatch")
    with ZipFile(assembly) as archive:
        failed = archive.testzip()
        if failed is not None:
            raise ValueError("Archive CRC failure; do not extract")
    with assembly.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assembly.replace(destination)
    destination.with_suffix(destination.suffix + ".provenance.json").write_text(
        json.dumps(
            {
                "url": url,
                "source": "https://challenge.isic-archive.com/data/",
                "license": license,
                "sha256": digest,
                "bytes": total,
                "publisher_checksum_verified": False,
                "source_etag": etag,
                "zip_crc_verified": True,
            },
            indent=2,
        )
    )
    # Remove only validated temporary copies created for this archive.
    partial.unlink(missing_ok=True)
    shutil.rmtree(ranges)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=list(SOURCES), required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    folder, name, license = SOURCES[args.source]
    print(
        download(
            "https://isic-archive.s3.amazonaws.com/challenges/2018/" + name,
            ROOT / "raw" / folder / name,
            license,
            args.workers,
        )
    )
