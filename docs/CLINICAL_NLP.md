# Clinical case-report NLP research pipeline

The application now has actual public-data NLP execution and a locally trained entity model. This is an academic benchmark, not a medically validated system or an institutional EHR-note model.

## Source and provenance
MACCROBAT2020, J. Harry Caufield, DOI https://doi.org/10.6084/m9.figshare.9764942.v2 . The versioned publisher API identifies CC BY 4.0 and supplies MD5 `9d090f3e0719e77e7a33c38750548bb8` for the 1,070,089-byte archive. Acquisition verifies that checksum and size, retains a separate local SHA-256 receipt and the versioned license metadata. The [NLM catalog](https://datasetcatalog.nlm.nih.gov/dataset?q=0002572717) independently describes the corpus and rights. Published case narratives differ from routine patient notes and do not establish representative clinical performance. No corpus text, annotations or weights are committed to Git.

All 200 paired BRAT/source documents were validated: unique document keys, exact offset/surface correspondence, valid ordered segments, no identical source documents. Actual counts: 25,189 entity mentions, 41 entity types, 44 discontinuous mentions. BRAT events, relations, attributes and coreferences are counted as uninterpreted records; no clinical facts or assertion values are invented from them.

## Real baseline execution
- Five prespecified author annotation types (disease/disorder, sign/symptom, medication, diagnostic procedure, therapeutic procedure) provide 11,441 contiguous gold mention contexts. TF-IDF bigrams + logistic regression predicts **mention semantic type given its gold boundary**, not disease diagnosis or entity detection. The observed mention and +/-160-character context are predictors; the gold type is never included in the input string. Case-report-group split gives 8,548 training / 2,893 held-out mentions. Accuracy=0.60801936, macro F1=0.51474274, weighted F1=0.58935750. Disease/disorder recall=0.22802198 is retained honestly.
- Five-cluster k-means on the 200 full narratives measured cosine silhouette=0.00602968, weak separation. Clusters are not patient diagnoses or validated clinical categories.
- BM25 and TF-IDF search executed on actual narratives and each returned 19 positive-score documents for the recorded query. Expert query relevance judgments are unavailable; no retrieval accuracy, clinical relevance or sense-disambiguation validation is claimed. Author entity semantic types are not silently treated as abbreviation-sense labels.

## Genuine NER training and evaluation
Blank English spaCy tok2vec + NER trained from the genuine clinical case-report annotations. Seed 42; sorted document IDs shuffled deterministically into **140 train / 30 validation / 30 test**. Duplicate document IDs/text are rejected. This is document-disjoint; patient identity across published reports cannot be guaranteed.

Twenty epochs, minibatches of four documents, dropout 0.2; checkpoint chosen by highest validation exact-span micro F1, first checkpoint wins ties. Training excludes 29 discontinuous, 132 token-misaligned, 341 overlapping/duplicate and two boundary-whitespace mentions. Source gold is never changed. Flat NER cannot represent every annotation. Validation/test scoring retains all overlapping contiguous gold mentions in the recall denominator; three discontinuous test mentions are separately counted/excluded. Relations, assertions, negation and terminology normalization are not evaluated or inferred.

Measured training run `86dcbeb7-d43a-4421-84d2-683e0fe8966d`, artifact `1b16e146-59d9-4fba-83b0-b87dc1d5081e`: best validation F1=0.53100542. Independent test: 3,525 contiguous gold mentions; TP=1,795, FP=1,413, FN=1,730; precision=0.55953865, recall=0.50921986, F1=0.53319471. Forty-one training types; no unseen test types. Full per-type errors, splits, exclusions and epoch history persist locally. No calibrated prediction certainty or clinical effectiveness is established.

The first real run failed with spaCy E024 on a boundary-whitespace annotation and remains a failed run in history. Training was corrected to count/exclude that unsupported supervision rather than alter gold evaluation or conceal the failure.

## Selection and end-to-end verification
Training never selects itself for inference. An administrator reviews a completed clinical training report, then explicitly selects it in Clinical text → Clinical entity model and evidence. Pipeline files are checked against SHA-256 hashes from its research model card before inference. `DERMA_NER_MODEL` is an explicit external local-model override and prevents UI selection until removed. No arbitrary uploaded model is accepted through the API.

Actual authenticated localhost HTTP verification selected the reviewed model, processed all 200 published narratives and checked 22,952 predicted spans against their returned character offsets; JSON export exactly matched the persisted result. Run `d259d35c-80d5-41db-875a-74875e05f2a9`. Those smoke inputs include training documents, so **no smoke-test accuracy is claimed**; performance numbers above come only from the separate held-out protocol. Negation remains unknown. The disposable verification API was stopped; its ephemeral credential is never stored or printed.

## Reproduce
Run from the project root in the full locked Python environment after migrations:

```sh
.venv/bin/python -m scripts.acquire_public_clinical
.venv/bin/python -m scripts.verify_public_clinical
.venv/bin/python -m scripts.train_clinical_ner --epochs 20
```

Review the completed run report, then select through the authenticated UI. For an explicit HTTP verification after reviewing that run:

```sh
.venv/bin/python -m scripts.verify_public_ner --training-run COMPLETED_RUN_UUID
```

Raw data stays under `data/raw/maccrobat2020`; derivatives and verification under `data/processed/public/maccrobat2020`; trained pipelines under `data/nlp_models`. The base Docker image excludes optional spaCy and reports a runtime blocker. Institutional-note generalization, expert relevance/sense labels, negation/normalization, external validation and clinical review remain incomplete.
