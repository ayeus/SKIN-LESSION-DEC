"""Classical image algorithms; output masks are not clinically validated lesions."""
import base64
import io
import math
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

def decode(data: bytes) -> np.ndarray:
    if len(data) > 20 * 1024 * 1024:
        raise ValueError('Image exceeds 20 MiB limit')
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > MAX_PIXELS or min(im.size) < 8:
                raise ValueError('Image must have each side at least 8 pixels and no more than 16 million pixels total')
            if im.format not in ('PNG', 'JPEG', 'WEBP'):
                raise ValueError('Only PNG, JPEG and WebP are accepted')
            return np.asarray(ImageOps.exif_transpose(im).convert('RGB')).copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ValueError('Invalid or oversized image') from e

def uri(rgb: np.ndarray) -> str:
    out = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(out, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()

def ssim(a, b):
    # Wang et al. local-window SSIM, grayscale, 11x11 Gaussian sigma 1.5.
    a = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY).astype(float)
    b = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY).astype(float)
    mean_a = cv2.GaussianBlur(a, (11, 11), 1.5)
    mean_b = cv2.GaussianBlur(b, (11, 11), 1.5)
    va = cv2.GaussianBlur(a*a, (11, 11), 1.5) - mean_a**2
    vb = cv2.GaussianBlur(b*b, (11, 11), 1.5) - mean_b**2
    cov = cv2.GaussianBlur(a*b, (11, 11), 1.5) - mean_a*mean_b
    return float(np.mean(((2*mean_a*mean_b+6.5025)*(2*cov+58.5225))/((mean_a**2+mean_b**2+6.5025)*(va+vb+58.5225))))

def mask_metrics(mask, truth):
    a, b = mask > 0, truth > 0
    if a.shape != b.shape:
        raise ValueError('Ground truth and mask shapes must match')
    intersection = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return {'dice': float(2*intersection/(a.sum()+b.sum())) if a.sum()+b.sum() else 1.0,
            'iou': float(intersection/union) if union else 1.0}

def process(rgb, method, p):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    out, mask, metrics = rgb.copy(), None, {}
    kernel = int(p.get('kernel', 5))
    if kernel < 1 or kernel > 31 or kernel % 2 == 0:
        raise ValueError('kernel must be an odd integer from 1 through 31')
    if method == 'contrast':
        lo, hi = np.percentile(rgb, (2, 98))
        out = np.clip((rgb.astype(float)-lo)*255/max(hi-lo, 1), 0, 255).astype('uint8')
    elif method in ('equalize', 'clahe'):
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        clip = float(p.get('clip', 2))
        if not 0 < clip <= 20:
            raise ValueError('clip must be in (0,20]')
        lab[:,:,0] = cv2.equalizeHist(lab[:,:,0]) if method == 'equalize' else cv2.createCLAHE(clipLimit=clip, tileGridSize=(8,8)).apply(lab[:,:,0])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    elif method == 'gamma':
        gamma = float(p.get('gamma', 1))
        if not .1 <= gamma <= 5:
            raise ValueError('gamma must be between 0.1 and 5')
        out = np.round(255*(rgb/255.)**gamma).astype('uint8')
    elif method == 'gaussian': out = cv2.GaussianBlur(rgb, (kernel,kernel), 0)
    elif method == 'median': out = cv2.medianBlur(rgb, kernel)
    elif method == 'bilateral': out = cv2.bilateralFilter(rgb, kernel, 75, 75)
    elif method == 'denoise': out = cv2.fastNlMeansDenoisingColored(rgb, None, 10,10,7,21)
    elif method == 'gray_world':
        means = rgb.mean(axis=(0,1))
        out = np.clip(rgb*means.mean()/np.maximum(means,1),0,255).astype('uint8')
    elif method in ('threshold', 'otsu', 'edges', 'morphology', 'grabcut'):
        threshold = int(p.get('threshold',128))
        if not 0 <= threshold <= 255: raise ValueError('threshold must be in [0,255]')
        if method == 'edges': mask = cv2.Canny(gray, 50,150)
        elif method == 'grabcut':
            h,w = gray.shape
            mask0 = np.zeros(gray.shape,np.uint8)
            cv2.grabCut(rgb, mask0, (1,1,w-2,h-2), np.zeros((1,65)),np.zeros((1,65)),5,cv2.GC_INIT_WITH_RECT)
            mask = np.where((mask0==1)|(mask0==3),255,0).astype('uint8')
        else:
            _,mask = cv2.threshold(gray, threshold,255,cv2.THRESH_BINARY_INV | (cv2.THRESH_OTSU if method in ('otsu','morphology') else 0))
            if method == 'morphology': mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((kernel,kernel),np.uint8))
        out = rgb.copy()
        out[mask>0] = (0.6*out[mask>0]+0.4*np.array([0,190,160])).astype('uint8')
        contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        metrics = {'foreground_fraction': float((mask>0).mean()),'contour_count':len(contours)}
    elif method in ('jpeg','png','webp'):
        quality = int(p.get('quality',80))
        if not 1 <= quality <= 100: raise ValueError('quality must be 1–100')
        stream = io.BytesIO()
        Image.fromarray(rgb).save(stream,format=method.upper(),**({'quality':quality} if method != 'png' else {'compress_level':9}))
        encoded = stream.getvalue()
        out = np.asarray(Image.open(io.BytesIO(encoded)).convert('RGB'))
        mse = float(np.mean((rgb.astype(float)-out.astype(float))**2))
        metrics = {'encoded_bytes':len(encoded),'raw_rgb_bytes':rgb.nbytes,'raw_to_encoded_ratio':rgb.nbytes/len(encoded),
                   'psnr_db':10*math.log10(255**2/mse) if mse else None,'lossless':mse==0,'ssim':ssim(rgb,out),
                   'download':'data:image/'+method+';base64,'+base64.b64encode(encoded).decode()}
    else: raise ValueError('Unsupported image method')
    hist = [np.histogram(out[:,:,i],bins=32,range=(0,256))[0].tolist() for i in range(3)]
    return {'original':uri(rgb),'image':uri(out),'mask':uri(mask) if mask is not None else None,
            'metrics':metrics,'histogram':hist,'parameters':p,'method':method,
            'limitation':'Classical image processing is not a validated lesion diagnosis. Compression may remove diagnostically relevant detail.'}

def register(a,b,ratio=.75,reprojection=3.):
    if not .1 <= ratio < 1 or not .1 <= reprojection <= 20:
        raise ValueError('Invalid matching or RANSAC parameters')
    sift = cv2.SIFT_create(nfeatures=2000)
    ka,da = sift.detectAndCompute(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY),None)
    kb,db = sift.detectAndCompute(cv2.cvtColor(b,cv2.COLOR_RGB2GRAY),None)
    result = {'keypoints_a':len(ka),'keypoints_b':len(kb),'descriptor_shape_a':list(da.shape) if da is not None else [0,128],
              'keypoint_image':uri(cv2.drawKeypoints(a,ka,None,flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS))}
    if da is None or db is None or len(db)<2: raise ValueError('Insufficient SIFT descriptors; choose overlapping textured images')
    pairs = cv2.BFMatcher().knnMatch(da,db,k=2)
    good = [pair[0] for pair in pairs if len(pair)==2 and pair[0].distance < ratio*pair[1].distance]
    if len(good)<4: raise ValueError('Fewer than four valid correspondences; registration is unsuitable')
    src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    H,inliers = cv2.findHomography(src,dst,cv2.RANSAC,reprojection)
    if H is None or not np.isfinite(H).all() or int(inliers.sum())<4:
        raise ValueError('No valid homography found')
    registered = cv2.warpPerspective(a,H,(b.shape[1],b.shape[0]))
    result.update(homography=H.tolist(),matches=len(good),inliers=int(inliers.sum()),outliers=len(good)-int(inliers.sum()),registered=uri(registered),
        matches_image=uri(cv2.drawMatches(a,ka,b,kb,good,None,matchesMask=inliers.ravel().tolist(),flags=2)))
    return result
