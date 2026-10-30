# Local presentation demo

This guide uses the real, locally acquired public research datasets already in `data/`. It does not create patient records or example predictions. All sample images are public research images and remain on this machine.

## Open the app

The local API and web app are currently running at:

- Web app: <http://127.0.0.1:3000>
- API: <http://127.0.0.1:8000>

If either service has stopped, open two terminals in the project root and run:

```sh
.venv/bin/python -m scripts.serve
```

```sh
cd frontend && npm run dev
```

In the app, enter the local administrator access token from the `DERMA_API_TOKEN` line in the ignored root `.env` file. Copy only the value after `=`. Keep the token private; do not put it in slides, screenshots, chat, or source control. The app keeps it in browser memory and clears it when the page closes.

## Suggested presentation flow

1. **Research overview:** point out that dataset and run counts come from the local database. The availability badges mean data is present; they do not mean that a module is clinically validated.
2. **Image processing lab:** upload `data/raw/isic2018-task3/images/ISIC_0024309.jpg`, select **Learned segmentation**, and run it. The selected model is a Tiny U-Net trained on 70, validation-selected on 15, and test-evaluated on 15 images from the official 100-image ISIC 2018 Task 1 validation cohort. On that small image-disjoint test split, Dice was 0.8905 and IoU was 0.8154. The fixed 256-pixel representation, small split, and lack of patient-independent or clinical validation limit what this result means.
3. **Lesion detection:** upload the same image, select **Compute actual Grad-CAM explanation**, leave score retention unchecked, and run the research inference. The app executes the selected EfficientNet-B0 artifact and shows its seven uncalibrated class scores, its top-ranked label, and a gradient-derived heatmap. The image and scores are not retained for this ephemeral request. This example image is part of the classifier's held-out test set, so this demo call is not an additional independent evaluation.
4. **CNN training & evaluation:** show the saved training runs and test report. The selected EfficientNet-B0 used a frozen ImageNet backbone and trained its classification head for three epochs. On 2,014 held-out lesion-grouped images its accuracy was 0.6212, balanced accuracy 0.5131, and macro F1 0.4172. Performance varies substantially by class; the displayed metrics are research results, not clinical effectiveness.
5. **Clinical text analytics / healthcare planning:** show the available public corpus and the real forecast evidence. Explain that hospital-specific records, expert relevance labels, and staffing policies were not provided, so those features do not claim local clinical validity or staffing recommendations.

The image is from the ISIC 2018/HAM10000 research dataset (CC BY-NC 4.0). The dataset citation, license notes, acquisition provenance, split details, and fuller limitations are in [DATA_ACQUISITION.md](DATA_ACQUISITION.md), [IMAGE_EXPERIMENT_PROTOCOL.md](IMAGE_EXPERIMENT_PROTOCOL.md), and [CLINICAL_NLP.md](CLINICAL_NLP.md).

## Presentation safety notes

- This is an academic research and education application, not a diagnostic device. Do not use predictions to make care decisions.
- Class scores have not been calibrated. Grad-CAM is a coarse visualization of model activations and gradients, not a clinically validated explanation.
- The classifier's groups are lesion identifiers; they do not establish patient-independent splits. Skin-tone, external-site, prospective, and clinical validation remain outstanding.
- Do not upload identifiable patient information. Use only authorized, appropriately de-identified data.
- Some tutorials intentionally show waiting states because no hospital operations data, staffing policies, expert labels, or approved clinical records are available.

## Screenshots

The `docs/screenshots/local-demo-*.png` captures were taken from the live application using the acquired public data. The dataset image in the lesion workflow is explicitly identified above; screenshots are research demonstrations and must not be presented as clinical validation.
