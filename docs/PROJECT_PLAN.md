# DermaInsight AI implementation plan

Research software, never a diagnostic device. HER is provisionally interpreted as EHR.

## Discovery (2026-10-29)
Supplied source: https://github.com/ayeus/SKIN-LESSION-DEC, main, initial commit c65ff2c. Only README exists. The parent workspace is an unrelated brain-tumor checkout with pre-existing deletions; it is not modified. No datasets, labels, notebooks, models or services supplied. Python 3.13.5, Node 22.17.0; FastAPI, SQLAlchemy, OpenCV SIFT, torch, torchvision, sklearn, scipy, pandas installed. scikit-image and UMAP absent. Apple M4 / 16GB, CUDA and MPS unavailable to this Python process. Docker CLI present; daemon not yet verified.

## Execution
1. Infrastructure: FastAPI, SQLAlchemy, migrations, authenticated local research access, immutable uploads, audit and run artifacts; Next.js UI.
2. Image algorithms: enhancement/restoration, masks, compression, SIFT correspondence and RANSAC registration with failure handling.
3. CNN: grouped split validation, actual training/evaluation/checkpoints, disabled inference until valid artifact.
4. EHR: explicit schema transformations, quality/missingness/duplicates, immutable output and reports.
5. NLP: TF-IDF classification/clustering, BM25 and TF-IDF retrieval; clinical NER gated on documented model.
6. Analytics: chronological forecast baselines, explicit capacity scenarios, numeric research PCA/t-SNE/regression.
7. UI integration, algorithm and API tests, browser review, documentation and security limits.

Milestones are committed and pushed to supplied repository main after verification. A passing synthetic unit test establishes algorithm behavior only, never clinical validity. All real-data validations remain incomplete until approved inputs arrive.
