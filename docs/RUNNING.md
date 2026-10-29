# Installation and operation

Run all commands from the `dermainsight` checkout. Python 3.13 and Node >=20.9 required. No cloud credentials needed for local algorithms. No data included.

## Python environment

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements.lock
```

Full lock includes used optional torch/torchvision/spaCy and test tools. For image/tabular/text baselines without CNN/clinical NER use `backend/requirements-base.lock` instead; ML tests require full lock. Locks pin transitive packages and hashes. They are resolved for Python 3.13 across supported platforms; Linux GPU packaging may be large.

## Configure

Copy `.env.example` to `.env` and generate a unique local token:

```sh
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Set DERMA_API_TOKEN to that value. Never commit `.env`. Source it only after reviewing its contents (`set -a; source .env; set +a` in a shell). Alternatively export variables directly. SQLite is default; omit DATABASE_URL for storage-root default. DERMA_STORAGE selects a private local directory. No public network exposure is required.

## Migrate and run

```sh
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Visit http://127.0.0.1:3000 and enter the token. API proxy defaults to local port 8000. API_URL must be set before frontend build/dev if the backend differs; Next rewrites are build configuration. Token stays in browser memory. Locking/refreshing clears it. The health endpoint is public; dataset/results operations require bearer authentication.

## Workflows
- Image lab: authorized PNG/JPEG/WebP → choose real algorithm and parameters → execute → inspect result/mask/metrics → download image or JSON report. Generated original-pixel comparison and results are retained locally without EXIF. Optional mask computes Dice/IoU only when dimensions match.
- EHR: import source/license/attestation → inspect schema → preprocessing JSON using actual normalized names → queued transform → compare quality/history → CSV/JSON export. Keep ML imputation inside training folds.
- NLP: import clinical_text CSV → select text column/task → label column for classifier or contextual senses → query for retrieval/sense task → inspect true output. Configure DERMA_NER_MODEL with local spaCy model plus research-model-card.json containing source/license/intended_use/limitations. No network model download occurs.
- Demand: import demand CSV → map daily dates/counts → >=28 complete days → baseline temporal validation/forecast. Optional capacity input is an assumption, never observed staffing fact.
- Weight: import authorized adult numeric dataset → map features/outcome → held-out associations/diagnostics. Use explicit group_column in advanced parameters for repeated subjects. Population survey inference unsupported.
- PCA/t-SNE: select compatible numeric features and optional advanced method parameters; exploratory only. CNN `test_embeddings.csv` can be imported as tabular, with only feature columns selected.

## CNN

```sh
.venv/bin/python -m scripts.train --metadata data/raw/lesions/metadata.csv --images data/raw/lesions/images --output artifacts/run-01 --architecture small_cnn --epochs 5
```

Output path must not already exist. Requires genuine labels and groups; defaults documented in ALGORITHMS.md. Explicit `--pretrained` permits ImageNet backbone download for ResNet/EfficientNet. Compare on validation evidence, keep external test locked. Outputs: weights.pt, manifest.json, history.json, test_embeddings.csv. No artifact is automatically promoted. Set DERMA_MODEL_DIR to reviewed artifact directory and restart API to enable ephemeral research inference. Model scores remain uncalibrated even when calibration diagnostics are measured. No clinical deployment implied.

## Checks

```sh
.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run test
npm run typecheck
npm run build
```

Component tests use isolated synthetic HTTP fixtures; they are not browser end-to-end verification. TestClient checks real database and filesystem operations. All synthetic model artifacts use pytest temporary directories and are never installed as app models.

## Containers

Set nonempty POSTGRES_PASSWORD and DERMA_API_TOKEN in `.env`. Use a URI-safe password or supply appropriately escaped connection configuration. Then `docker compose up --build`. DB readiness → migrations → API → web. Ports bind loopback. Base API image excludes optional ML/NLP libraries; use full-lock installation/build extension before enabling these modules. The complete base Compose stack was built and exercised in an isolated project; migrations, authentication/account persistence, frontend proxy, real image processing/export and missing-ML-runtime gates passed. This does not verify optional CNN training inside the base image.

## Operations and limits

Run a single API worker for the in-process bounded queue (two running/four outstanding tabular jobs). Restart marks interrupted jobs failed; it does not retry silently. CLI training writes history after each epoch. Storage includes sensitive research results even with de-identification: restrict filesystem permissions and retain only as approved. Back up database and raw/processed directories together. Production requires institutional controls, users/RBAC, TLS, encrypted storage, resource quotas and a durable queue.

## Web CNN experiments

The training page now checks `/training/readiness` and submits real background jobs with architecture/epochs/batch size. Default manifest is `data/raw/isic2018-task3/metadata.csv`, images under `data/raw/isic2018-task3/images/`. Override server paths with DERMA_LESION_METADATA and DERMA_LESION_IMAGES; paths cannot be supplied by browser clients. Images must finish downloading and be extracted by `scripts.prepare_isic` before training can start.

One CNN experiment may run at a time. Epoch progress appears in the UI and persists in run metadata; history writes are atomic. Navigating away does not cancel training; inspect Reports to recover the run. Restart marks interrupted work failed. Completed experiments live under storage/models/<run-id>. Review actual validation/test artifacts before pressing Select this reviewed research artifact. That writes a local model pointer; no automatic selection occurs. DERMA_MODEL_DIR explicitly overrides selection and must be removed to use the browser selector. All scores remain research-only and uncalibrated.

To verify PostgreSQL independently: `.venv/bin/python -m scripts.check_postgres`. It creates a uniquely named disposable postgres:17-alpine container, runs migrations plus API/FHIR/training tests, and removes the container in finally. It does not touch existing databases. A working Docker engine is required.

## Read-only dataset explorer and relationships

In EHR & dataset management, select an imported dataset, choose an optional exact-value or literal-text filter and read a paginated table (25 rows per page; API allows at most 100). The source is never changed. For two EHR tables, expand relationship inspection, choose child/parent datasets and map foreign/primary keys explicitly. Parent keys must be unique/nonmissing; unmatched and missing child keys are reported; repeated encounters are retained. No hidden key coercion or identity inference occurs. Relationship reports persist in history.

Inference defaults to no score/image retention. Download research prediction report exports actual ephemeral output locally. The optional Save research scores checkbox persists only scores, model/input hashes and measured input shape. Image and Grad-CAM pixels are excluded from the saved server report. Retained score reports can be reviewed/exported through Reports.

## Named local accounts and access control

Run migration 002 before starting the updated API. Bootstrap with DERMA_API_TOKEN, then choose real usernames/passwords/roles through Settings. Local account sign-in returns expiring sessions, stored in browser memory only. Lock workspace attempts named-session revocation and clears cached data; environment tokens must be rotated/unset to revoke. Named researchers own newly created datasets/runs; viewers are read-only; legacy public imports remain admin-only until explicitly granted. Training source inspection/submission and global model selection require admin. See [LOCAL_IDENTITY.md](LOCAL_IDENTITY.md) for precise scope and limitations. No real accounts have been seeded.

The status page reports bytes on disk and actual ISIC manifest distribution to administrators. Expected archive size comes from the official HTTP response, not a fabricated progress percentage. The partial file does not prove an active transfer; use the acquisition script to resume after stopping any prior transfer. Complete archive, extraction, content checks and model training are separate states.

Full-stack smoke check: `.venv/bin/python -m scripts.check_compose`. Requires local ports 3000/8000 free. Uses a unique project, generated ephemeral credentials and synthetic isolated fixtures; builds real images and tests HTTP through the Next.js proxy. Finally removes only its own containers/volumes/network. It never binds the working project healthcare-data directory. Optional ML/NLP dependencies report explicit blockers rather than pretending a model is available.
