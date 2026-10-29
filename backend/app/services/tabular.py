import re
import pandas as pd
import numpy as np


def read_table(path):
    suffix = path.suffix.lower()
    if suffix == ".json":
        from .fhir import parse

        frame = parse(path.read_bytes())
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".xlsx":
        frame = pd.read_excel(path)
    else:
        raise ValueError(
            "Supported table formats are CSV, XLSX and the documented FHIR JSON subset"
        )
    if len(frame) > 100_000 or len(frame.columns) > 200:
        raise ValueError("Research import limit: 100,000 rows and 200 columns")
    if frame.empty or not frame.columns.is_unique:
        raise ValueError("Dataset must be nonempty with unique columns")
    return frame


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def profile(df):
    numeric = df.select_dtypes(include="number")
    return clean_json(
        {
            "rows": len(df),
            "columns": [
                {
                    "name": c,
                    "dtype": str(df[c].dtype),
                    "missing": int(df[c].isna().sum()),
                    "unique": int(df[c].nunique()),
                }
                for c in df
            ],
            "exact_duplicate_rows": int(df.duplicated().sum()),
            "preview": df.head(20).where(pd.notna(df), None).to_dict("records"),
            "histograms": {
                c: {
                    "counts": np.histogram(numeric[c].dropna().to_numpy(), bins=20)[
                        0
                    ].tolist(),
                    "edges": np.histogram(numeric[c].dropna().to_numpy(), bins=20)[
                        1
                    ].tolist(),
                }
                for c in numeric
                if len(numeric[c].dropna()) and np.isfinite(numeric[c].dropna()).all()
            },
            "statistics": numeric.describe().to_dict() if len(numeric.columns) else {},
            "correlation": numeric.corr().to_dict() if len(numeric.columns) else {},
        }
    )


def transform(df, p):
    out = df.copy(deep=True)
    log = []
    review = []
    if p.get("normalize_columns", True):
        names = [
            re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in out
        ]
        if len(set(names)) != len(names) or "" in names:
            raise ValueError(
                "Column normalization would create duplicate or empty names"
            )
        log.append(
            {"operation": "normalize_columns", "mapping": dict(zip(out.columns, names))}
        )
        out.columns = names

    def require(c):
        if c not in out:
            raise ValueError(f"Unknown column: {c}; mappings use normalized names")

    for c in out.select_dtypes(include=["object", "string"]).columns:
        before = out[c].copy()
        out[c] = out[c].map(
            lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v
        )
        log.append(
            {
                "operation": "trim_text",
                "column": c,
                "changed": int((before.fillna("") != out[c].fillna("")).sum()),
            }
        )
    for c, kind in p.get("types", {}).items():
        require(c)
        old = out[c]
        if kind == "numeric":
            converted = pd.to_numeric(old, errors="coerce")
        elif kind == "date":
            fmt = p.get("date_formats", {}).get(c)
            if not fmt:
                raise ValueError(f"Explicit date format required for {c}")
            converted = pd.to_datetime(old, format=fmt, errors="coerce", utc=True)
        else:
            raise ValueError("Supported conversions: numeric, date")
        invalid = old.notna() & converted.isna()
        review.append(
            {
                "column": c,
                "reason": "conversion_failed",
                "rows": np.flatnonzero(invalid).tolist(),
            }
        )
        out[c] = converted
    for c, mapping in p.get("categories", {}).items():
        require(c)
        out[c] = out[c].replace(mapping)
        log.append({"operation": "category_mapping", "column": c, "mapping": mapping})
    for c, spec in p.get("units", {}).items():
        require(c)
        if not all(k in spec for k in ("factor", "offset", "from", "to")):
            raise ValueError("Unit conversion needs factor, offset, from and to")
        out[c] = pd.to_numeric(out[c], errors="raise") * float(spec["factor"]) + float(
            spec["offset"]
        )
        log.append({"operation": "unit_conversion", "column": c, **spec})
    for c, bounds in p.get("ranges", {}).items():
        require(c)
        if len(bounds) != 2 or bounds[0] > bounds[1]:
            raise ValueError("Range requires ordered lower and upper bounds")
        values = pd.to_numeric(out[c], errors="raise")
        bad = values.notna() & ~values.between(*bounds)
        review.append(
            {
                "column": c,
                "reason": "outside_configured_range",
                "rows": np.flatnonzero(bad).tolist(),
            }
        )
    if p.get("drop_exact_duplicates"):
        n = len(out)
        out = out.drop_duplicates()
        log.append({"operation": "drop_exact_duplicates", "removed": n - len(out)})
    keys = p.get("duplicate_keys", [])
    if keys:
        for c in keys:
            require(c)
        review.append(
            {
                "reason": "potential_repeated_keys_not_removed",
                "rows": np.flatnonzero(
                    out.duplicated(subset=keys, keep=False)
                ).tolist(),
            }
        )
    near = p.get("near_duplicate_columns", [])
    if near:
        from difflib import SequenceMatcher

        if len(near) < 2:
            raise ValueError(
                "Near-duplicate review needs at least two fields, never patient identity alone"
            )
        for c in near:
            require(c)
        if len(out) > 1000:
            raise ValueError("Pairwise near-duplicate review limited to 1000 rows")
        threshold = float(p.get("near_duplicate_similarity", 0))
        if not 0 < threshold <= 1:
            raise ValueError("Supply explicit near_duplicate_similarity in (0,1]")
        rows = (
            out[near]
            .fillna("")
            .astype(str)
            .agg(" | ".join, axis=1)
            .str.lower()
            .tolist()
        )
        pairs = []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                similarity = SequenceMatcher(
                    None, rows[i], rows[j], autojunk=False
                ).ratio()
                if similarity >= threshold:
                    pairs.append({"row_a": i, "row_b": j, "similarity": similarity})
        review.append(
            {
                "reason": "near_duplicate_candidates_not_removed",
                "columns": near,
                "threshold": threshold,
                "pairs": pairs,
            }
        )
    for c, strategy in p.get("impute", {}).items():
        require(c)
        missing = int(out[c].isna().sum())
        if strategy in ("median", "mean"):
            if not pd.api.types.is_numeric_dtype(out[c]):
                raise ValueError("Mean/median require numeric column")
            value = out[c].median() if strategy == "median" else out[c].mean()
        elif strategy == "mode":
            modes = out[c].mode()
            if modes.empty:
                raise ValueError(f"Cannot impute all-missing column {c}")
            value = modes.iloc[0]
        else:
            raise ValueError(
                "Imputation supports mean, median, mode; choose based on context"
            )
        if pd.isna(value):
            raise ValueError(f"Cannot impute all-missing column {c}")
        out[c] = out[c].fillna(value)
        log.append(
            {
                "operation": "impute",
                "column": c,
                "strategy": strategy,
                "value": clean_json(value),
                "filled": missing,
            }
        )
    return out, clean_json(
        {
            "before": profile(df),
            "after": profile(out),
            "history": log,
            "manual_review": review,
            "limitation": "Descriptive preprocessing only. For ML, fit imputation/scaling on training folds, never use this full-dataset output to claim held-out performance.",
        }
    )
