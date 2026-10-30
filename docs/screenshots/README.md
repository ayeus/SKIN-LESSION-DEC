# Genuine working-page screenshots

## Live public research data captures

- `local-demo-dashboard.png`: live local database counts and real data-readiness states.
- `local-demo-inference.png`: actual selected EfficientNet-B0 output and gradient-based Grad-CAM for public image `ISIC_0024309.jpg`; score retention was off. The image belongs to the model's held-out test split and this UI call is not independent evaluation.
- `local-demo-segmentation.png`: actual selected Tiny U-Net V2 output, overlay, mask and pixel histogram for the same public image.

These are local academic research demonstrations with documented dataset/model limitations, not clinical evidence. Run the demo from [LOCAL_DEMO.md](../LOCAL_DEMO.md).

## Isolated test-fixture captures

Captured by actual headless Chromium against the real Next.js frontend, API, migrated disposable database and persistent artifact/export routes. No API responses are mocked. These three screenshots contain **explicitly synthetic mathematical algorithm fixtures only** and must never be presented as real healthcare observations or model results.

- `isolated-image-lab-desktop.png`: identity gamma transform on a synthetic geometric image, actual histogram/table and persisted export. The synthetic filename is visible.
- `isolated-3d-pca-mobile.png`: actual three-component PCA on five synthetic numeric rows, rotation and row inspection. This verifies UI geometry, not meaningful clinical clustering.
- `isolated-model-blocked-desktop.png`: honest missing-model state in a disposable environment. Production research storage/model selection is never mounted into these tests.

Screenshots were inspected visually. Full-page captures show a viewport-height fixed sidebar; a blank lower-left region below that captured viewport is expected. The Next.js development indicator is visible because these checks run the development server. No patient records, real credentials or invented medical scores appear. Native Chrome screen capture remains unavailable; these images come from the separate headless test browser.
