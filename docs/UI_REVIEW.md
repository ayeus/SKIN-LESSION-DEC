# UI verification and guidelines review — 2026-10-30

Used the `web-design-guidelines` skill and its current upstream rules: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md . Findings addressed in this milestone:

- `frontend/app/globals.css`: marginal/insufficient text contrast on page descriptions, kicker, footer and research banner corrected after actual axe failures. Focus styles retained; tabular numbers and touch-action added.
- `frontend/app/page.tsx`: module navigation uses real bookmarkable links, supports back/forward, has a skip link/main target and exposes mobile drawer state. Model selection hides validation-only artifacts. Charts display legends and paginated actual-value tables; animation no longer shows transient flat curves before drawing measured results.
- `frontend/app/components/training-history.tsx`: separate actual CNN/NER history schemas, avoiding a report-render crash from nonexistent CNN fields on NER runs.
- `frontend/app/components/entity-document.tsx`: exact-span highlighting safely escapes source markup; invalid/overlapping offsets show source text without false highlighting.

Browser evidence: Playwright 1.64.1 Chromium headless shell, desktop 1440×1000 and Pixel 7 emulation. Real API/DB/proxy operations, zero mocked HTTP responses. Tests cover invalid authentication, missing-model gating, real processing/identity property, invalid-image rejection, exact histogram table values, report downloads, CSV import, three-component PCA, rotation and exact row inspection. Automated WCAG A/AA checks cover sign-in, dashboard, image form/results, dataset form and training form, without disabling contrast rules. All eight checks pass. See screenshots/README.md for visually inspected test-fixture screenshots.

Initial test failures involved wrong selectors/framework route-announcer ambiguity; corrected semantic selectors while preserving assertions. Subsequent real contrast failures were fixed in the application, not bypassed. Native screen-capture failure does not prevent the separate headless test browser.

Remaining manual scope: screen-reader usability, real iOS/Safari/Firefox behavior, touch devices, long clinical-note tables and production deployment review. These automated checks are not a full WCAG certification. Other guideline opportunities remain: preserving every filter/report in URLs, explicit image intrinsic dimensions for legacy artifacts and comprehensive unsaved-form protection. No browser test establishes medical validity.
