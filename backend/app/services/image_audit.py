"""Complete encoded/pixel content audit before genuine image model fitting."""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from .images import MAX_PIXELS


def audit_images(frame, root):
    root = Path(root).resolve()
    encoded = defaultdict(list)
    pixels = defaultdict(list)
    errors = []
    formats = Counter()
    sizes = Counter()
    records = []
    for row in frame.itertuples(index=False):
        relative = str(row.image_path)
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Image path escapes configured dataset")
        try:
            if path.stat().st_size > 20 * 1024**2:
                raise ValueError("Encoded image exceeds 20 MiB limit")
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            with Image.open(path) as image:
                if (
                    image.format not in ["JPEG", "PNG", "WEBP"]
                    or min(image.size) < 8
                    or image.width * image.height > MAX_PIXELS
                ):
                    raise ValueError("Unsupported format or image dimensions")
                image.verify()
            with Image.open(path) as image:
                rgb = ImageOps.exif_transpose(image).convert("RGB")
                array = np.asarray(rgb)
                pixel_digest = hashlib.sha256(
                    str(rgb.size).encode() + array.tobytes()
                ).hexdigest()
                sizes[f"{rgb.width}x{rgb.height}"] += 1
                formats[image.format] += 1
            record = {
                "image_path": relative,
                "group_id": str(row.group_id),
                "label": str(row.label),
                "encoded_sha256": digest,
                "decoded_rgb_sha256": pixel_digest,
            }
            encoded[digest].append(record)
            pixels[pixel_digest].append(record)
            records.append(record)
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            errors.append({"image_path": relative, "reason": type(error).__name__})

    def duplicates(groups):
        return [
            values
            for values in groups.values()
            if len({v["group_id"] for v in values}) > 1
        ]

    cross_encoded = duplicates(encoded)
    cross_pixels = duplicates(pixels)
    ready = not errors and not cross_encoded and not cross_pixels
    return {
        "ready": ready,
        "manifest_rows": len(frame),
        "decoded_images": len(records),
        "invalid_images": errors,
        "cross_group_encoded_duplicates": cross_encoded,
        "cross_group_decoded_duplicates": cross_pixels,
        "formats": dict(formats),
        "dimensions": dict(sizes),
        "image_records": records,
        "image_content_sha256": hashlib.sha256(
            "".join(sorted(encoded)).encode()
        ).hexdigest(),
        "audit_record_sha256": hashlib.sha256(
            json.dumps(records, sort_keys=True).encode()
        ).hexdigest(),
        "limitation": "Exact encoded/pixel duplicate checks do not detect all near-duplicates or establish patient independence. Group/label conflicts require review; no labels or source groups are silently changed.",
    }
