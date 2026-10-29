# Latest data checkpoint

Public MIMIC-IV demo EHR, UKHSA historical national admissions and NHANES adult data have now been acquired and exercised. ISIC2018 labels/groups validated; image archive downloading; CNN training not performed. See [DATA_ACQUISITION.md](DATA_ACQUISITION.md). Earlier no-data statements below describe the initial implementation checkpoint, not current acquisition status.

# Tutorial coverage matrix

**No tutorial is declared complete.** Fixtures below validate algorithms only. Real public-data evidence is separately recorded in DATA_ACQUISITION.md; clinical effectiveness remains NOT VERIFIED.

| Tutorial | Implemented feature / algorithm | Source | UI | Evidence | Remaining |
|---|---|---|---|---|---|
| T1 | Authorized CSV/XLSX/FHIR-subset imports, filtered browsing, key relationships, provenance, local accounts/roles/ownership/grants/audit | backend/app/main.py, db.py, services/tabular.py | EHR & datasets | test_api.py, test_fhir.py, test_relationships.py; real MIMIC verification | Public MIMIC EHR relationships verified; full FHIR and production/SSO controls remain incomplete; local identity/grants tested |
| T2 | Names/types/dates/units/categories/ranges/text, immutable transform | services/tabular.py | Preprocessing | test_tabular_analytics.py conversion/source tests | Real dictionaries and validation |
| T3 | Exact duplicate removal, repeated-key and fuzzy candidate review, missingness/imputation/history | services/tabular.py | Preprocessing | encounter preservation and near-duplicate tests | Context-aware real EHR review |
| T4 | Enhancement/restoration, masks/contours, JPEG/PNG/WebP, SSIM/PSNR/Dice/IoU | services/images.py | Image lab | test_images.py known disk, identity, noise properties | Expert masks and diagnostic-detail assessment |
| T5 | SIFT/RANSAC; real CNN CLI/web training, explicit selection, evaluation/inference/reporting | services/images.py, ml.py; scripts/train.py | SIFT & RANSAC, Training, Lesion detection | known translation; group splits; synthetic training/checkpoint/API selection/opt-in retention round-trip | Licensed lesion data, real experiments/final model |
| T6 | Comparisons/histograms/masks/matches, training curves/confusion/ROC/PR, actual Grad-CAM; embeddings artifact | images.py, ml.py; frontend/app/page.tsx | Visualization, Training, Results | algorithm output and gradient test; frontend build/components | Real model visual review, broader galleries/3D exploration |
| T7 | Last/weekly/mean/ridge; chronological validation-only selection and separate test; explicit shift workload scenario | services/forecasting.py; scripts/acquire_public_demand.py | Patient demand | test_forecast_protocol.py, test_demand_acquisition.py; actual UKHSA 120-day case and retrospective seven-day check | Local hospital arrivals, staffing policies, operational review and calibrated multi-step intervals |
| T8 | Explicit column mappings, date filtering, observed distributions/monthly counts, quality | services/analytics.py strategic | Historical healthcare indicators | explicit aggregate test | Real EHR/operations, definitions/demographics |
| T9 | Dimensioned staff-shifts/day, explicit shift fractions/hours, assumption-labeled exports | forecasting.py; main.py exports | Healthcare planning, Reports | explicit scenario and API export tests | Real policies, resource/skill/coverage bottleneck modeling |
| T10 | TF-IDF logistic baseline, genuine labels, optional group split, k-means/hierarchical | services/text.py | Clinical text | classification/clustering tests | Real notes and labels, meaningful held-out clinical evaluation |
| T11 | Owner-configured local clinical spaCy adapter/model card, entity offsets/JSON, optional actual negex extension | services/text.py clinical_entities | Clinical text NER | missing-model rejection | Licensed clinical model, gold entities, uncertainty/normalization validation |
| T12 | BM25/TF-IDF ranking, genuine context-labeled sense ranking, explicit uncertainty | services/text.py | Clinical text search/sense task | BM25 known relevance, sense-ranking fixture | Real relevance judgments, clinical contexts/senses and calibration |
| T13 | Scaled PCA/t-SNE, variance/loadings, 2/3 components; real test CNN embeddings export | services/analytics.py reduce; ml.py | Dimensionality reduction | PCA rank property | Real modality-specific data; 3D UI and optional UMAP |
| T14 | Numeric schema/descriptive/correlation/histograms, explicit preprocessing | tabular.py; analytics.py | Adult weight research, Datasets | descriptive/model fixtures | Real adult behaviors, units/inclusion/study design |
| T15 | Held-out ridge and nonlinear RF, permutation importance, residual/confounding/sensitivity output | services/analytics.py research | Adult weight research | held-out association and leakage rejection tests | Real study, subject review, validated statistical interpretation |

Test paths: `backend/tests/`; component fixtures `frontend/tests/workspace.test.tsx`. Data source for all tests: explicitly synthetic, local test-only. Application datasets: genuine public MIMIC-IV demo, NHANES and UKHSA locally acquired; lesion image acquisition incomplete. Test fixtures are never presented as genuine observations.
