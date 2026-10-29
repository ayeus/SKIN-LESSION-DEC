# Architecture

Next.js/React/TypeScript → same-origin /api proxy → FastAPI → validated services → SQLAlchemy → PostgreSQL (Compose) or SQLite (local development). Raw uploads and processed artifacts live outside version control. API token is supplied at runtime and held in browser memory; no patient records or secrets in source. All access except health requires token. This single-owner local access model is not production identity management.

Dataset metadata records source, license, modality, checksum and owner authorization. Transformations create a new artifact; source is never overwritten. Runs have pending/running/completed/failed state and persist parameters, artifact references and errors. Audit events record resource actions, never clinical note contents. Large files remain in filesystem volumes.

```mermaid
flowchart LR
 U[Research user] --> W[Next.js]
 W --> A[Authenticated FastAPI]
 A --> D[(SQL metadata)]
 A --> S[Image / EHR / NLP / Analytics / ML services]
 S --> R[Immutable raw files]
 S --> P[Versioned results and models]
```

Schema: datasets, runs, audit_events. Runs distinguish imports, transformations, image processing, registrations, inference, training, evaluation, text analytics, forecasting, research and reports. Domain-specific payloads are JSON with explicit run type; dedicated production user/encounter tables and multi-user RBAC remain future work. Do not import identifiable data into this local research version.

Web CNN jobs use configured server-side source paths, bounded execution and persisted epoch progress; complete artifacts live in storage/models/<run-id>. Explicit selection writes an atomic local pointer only after checksum/preprocessing validation. FHIR imports validate a strict research subset before saving raw bytes. Dataset browsing is read-only; explicit relationships validate keys without rewriting source tables. Inference score retention is opt-in, with no raw-image/Grad-CAM server persistence.
