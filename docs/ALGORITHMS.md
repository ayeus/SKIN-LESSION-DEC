# Algorithms and mathematical scope

## Images
Contrast stretch maps empirical 2nd–98th intensities to [0,255]. Equalization and CLAHE act on LAB luminance (CLAHE clip=2, tiles=8x8), not each RGB channel independently. Gamma uses 255(x/255)^gamma. Gray-world assumes average scene illumination is neutral and may distort biologically meaningful color. Gaussian/median/bilateral/non-local-means filters trade noise reduction against detail. None is automatically optimal for dermoscopy.

Threshold/Otsu use dark-foreground intensity segmentation, Canny fixed illustrative edge thresholds 50/150, morphology opening configured odd kernel, GrabCut initializes an inset rectangle. These are generic algorithms, not lesion models. Dice=2|A∩B|/(|A|+|B|); IoU=|A∩B|/|A∪B|. Empty/empty returns 1 by documented convention. Ground-truth masks must be paired and clinically annotated.

PSNR=10 log10(255²/MSE); exact identity has infinite PSNR, serialized as null plus lossless=true. SSIM uses grayscale local 11x11 Gaussian moments, sigma=1.5, C1=(.01*255)² and C2=(.03*255)² with OpenCV reflected borders. Compression ratio compares raw RGB bytes to encoded bytes; it is not the original uploaded compressed file size ratio. PNG is lossless; JPEG/WebP may remove clinical detail.

SIFT retains at most 2000 features; Lowe ratio=0.75, homography RANSAC residual=3 pixels. At least four inliers required; unrelated/featureless images fail. These parameters are configurable algorithm defaults, not clinical classification thresholds. Registration validity requires overlapping structure and expert review; a homography does not prove biologic equivalence.

## CNN
Small baseline, ResNet18 and EfficientNet-B0 are configurable, not ranked without experiments. Resize 224², RGB, ImageNet channel normalization, flips/15-degree rotations only in training. Five-fold StratifiedGroupKFold assigns independent test and validation folds, remaining folds train. Every split must have all labels; group overlap and identical image bytes across groups are rejected. Patient grouping is preferred. Lesion grouping cannot exclude same-patient leakage, and near-duplicate images still require review.

Seed 42, deterministic operations, Adam lr=.001, class-weighted cross-entropy. Best validation-loss state saved. Test classification report, balanced accuracy, confusion matrix, ROC-AUC, log loss and multiclass Brier score measured on held-out data. Scores are explicitly uncalibrated. Test-set reuse across architecture experiments biases final claims; reserve an external locked benchmark. No early experimental result establishes clinical effectiveness.

Grad-CAM weights final convolutional activations by mean target-logit gradients, sums channels and applies ReLU. Visualization is computed from actual gradients; zero activation remains an explicitly possible degenerate explanation. It is not segmentation or verified clinical reasoning.

## EHR
Column normalization rejects collisions. Conversions flag coercion failures. Dates require explicit formats. Linear unit conversions require owner-provided source/target, factor and offset. Range violations are flagged without silent deletion. Only exact entire-row duplicates can be removed; selected keys identify candidates for review. Mean/median numeric and mode categorical imputation are descriptive; ML pipelines fit transformations only inside training folds. No automatic assumption of MCAR/MAR/MNAR.

## Text
Whitespace normalization and Unicode word tokens; TF-IDF uni/bigrams with max 10,000 features. Negation words are not stripped. Classification fits vocabulary on training only, logistic regression max_iter=1000, optional patient-group split. K-means seed=42/n_init=10 or hierarchical clustering (≤1000 docs); cosine silhouette is exploratory. No clustering assignments are ground-truth diagnoses.
BM25 uses k1=1.5,b=.75 and log(1+(N-df+.5)/(df+.5)); TF-IDF retrieval uses cosine via L2 normalization. Scores are relevance, not medical truth. Unknown abbreviations remain unresolved unless a context-trained pipeline is supplied. Clinical NER loads only owner-provided local spaCy pipeline with source/license/model card; negation unknown unless actual configured extension exists.

## Forecast/research
Forecasts compare last value, weekly seasonal and trailing 7-day mean on rolling one-step chronological validation. Missing days are rejected; no zero imputation. Validation selects baseline, so its errors are not independent test estimates. Recursive multi-step output includes an empirical 90th-percentile absolute one-step residual band, not a calibrated multi-step interval. Capacity ceil(forecast / user-supplied patients-per-staff-per-shift) is an illustrative scenario, not a staffing recommendation.

PCA and t-SNE use median-imputed standardized features for exploratory geometry. PCA reports variance/loadings. Research ridge regression alpha=1 uses train-fitted median/scaling, 75/25 held-out split, optional group split; MAE/RMSE/R² and residuals are measured. Unweighted observational associations, no causal claims; complex survey estimates and adult inclusion require an appropriate study design.
