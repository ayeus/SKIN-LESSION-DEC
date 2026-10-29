# DermaInsight AI

A working local research workspace for biomedical image processing, CNN experiments, EHR cleaning, clinical text and healthcare analytics. **Research only; not a diagnosis or treatment system.**

## Current state

Real FastAPI/SQLAlchemy services, integrated Next.js UI, persistent runs/audits, immutable imports, real image algorithms, SIFT/RANSAC, group-aware CNN CLI, actual Grad-CAM, EHR transformations, TF-IDF/BM25/contextual sense ranking, forecasting, historical indicators, PCA/t-SNE and observational regression diagnostics. Public MIMIC-IV demo EHR and NHANES adult research data have been acquired locally and exercised; data files remain excluded from Git. ISIC2018 labels/groups are validated and image acquisition is underway. No lesion-trained model is installed. See [acquisition evidence](docs/DATA_ACQUISITION.md). Dataset-dependent completion and clinical validation remain blocked.

- [Run locally and execute workflows](docs/RUNNING.md)
- [Required owner inputs](docs/USER_ACTION_REQUIRED.md)
- [Current implementation and remaining scope](docs/IMPLEMENTATION_STATUS.md)
- [Exact verification evidence](docs/TEST_RESULTS.md)
- [Tutorial coverage matrix](docs/TUTORIAL_COVERAGE.md)
- [Architecture](docs/ARCHITECTURE.md), [algorithms](docs/ALGORITHMS.md), [academic report and viva](docs/ACADEMIC_REPORT.md)

Python 3.13, Node 20.9+, `npm ci`, hash-locked Python dependencies, Alembic migrations and environment-based configuration. Local SQLite is supported; PostgreSQL Compose configuration awaits Docker engine verification. Do not commit datasets, patient records, model artifacts or `.env` secrets.
