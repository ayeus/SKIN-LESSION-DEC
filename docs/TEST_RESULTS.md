# Verification record

2026-10-29: inspected repository; supplied upstream has README only. Python imports verified torch 2.13.0, OpenCV 5.0.0 and SIFT availability; CUDA/MPS false in current process. No tests or model evaluations existed. No real-data verification performed. Clinical inference BLOCKED.

## First algorithm/API milestone
- `python3 -m pytest backend/tests -q`: failed before collection because shell selected Python 3.14 without pytest. Corrected by selecting installed interpreter explicitly; no assertions changed.
- `/usr/local/bin/python3.13 -m pytest backend/tests -q`: **32 passed**, 6.12s. Synthetic fixtures isolated in tests: PNG identity/SSIM, gamma identity, dark-disk segmentation Dice/IoU, variance reduction, real SIFT/RANSAC translation recovery, every image algorithm, immutable tabular transformations, exact duplicates vs encounters, unit conversion, missing dates, temporal leakage, PCA rank, held-out regression, BM25, NLP label requirement, group-disjoint CNN splits, tensor shape/eval determinism, authenticated API import→transform→persist→export and failure persistence.
- `npm run typecheck`: passed.
- `npm run build`: passed, Next.js 16.4.3, route `/` prerendered.
- `npm install next@latest react@latest react-dom@latest`: completed; audit reported 0 vulnerabilities. Exact dependency graph in package-lock.json.
- Joblib emitted physical-core detection warning; it fell back to logical cores. Not suppressed.
- Actual lesion training, inference, clinical performance and all real healthcare analytics: BLOCKED / NOT VERIFIED (inputs missing). Unit tests do not establish medical validity.
