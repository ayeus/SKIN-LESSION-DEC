import base64
import io
import cv2
import numpy as np
import pytest
from PIL import Image
from backend.app.services.images import process,decode,register,mask_metrics,ssim

def synthetic_image():
    a=np.zeros((128,128,3),dtype=np.uint8); a[:]=180; cv2.circle(a,(64,64),25,(30,40,50),-1); return a

def output_rgb(result): return decode(base64.b64decode(result['image'].split(',')[1]))

def test_gamma_identity_and_monotonicity():
    a=synthetic_image(); np.testing.assert_array_equal(output_rgb(process(a,'gamma',{'gamma':1})),a)
    assert (output_rgb(process(a,'gamma',{'gamma':2}))<=a).all()

def test_lossless_png_metrics():
    a=synthetic_image(); r=process(a,'png',{})
    np.testing.assert_array_equal(output_rgb(r),a)
    assert r['metrics']['ssim']==pytest.approx(1)
    assert r['metrics']['lossless'] and r['metrics']['psnr_db'] is None

def test_mask_matches_known_dark_disk():
    a=synthetic_image(); r=process(a,'threshold',{'threshold':100})
    mask=decode(base64.b64decode(r['mask'].split(',')[1]))[:,:,0]
    expected=np.zeros((128,128),dtype=np.uint8); cv2.circle(expected,(64,64),25,255,-1)
    assert mask_metrics(mask,expected)=={'dice':1.,'iou':1.}
    assert mask_metrics(mask,np.zeros_like(mask))=={'dice':0.,'iou':0.}

def test_noise_reduction_constant_and_variance():
    a=np.full((64,64,3),100,np.uint8); np.testing.assert_array_equal(output_rgb(process(a,'gaussian',{})),a)
    noisy=np.random.default_rng(42).integers(0,256,(64,64,3),dtype=np.uint8)
    assert output_rgb(process(noisy,'gaussian',{})).var()<noisy.var()

@pytest.mark.parametrize('method',['contrast','equalize','clahe','median','bilateral','denoise','gray_world','otsu','edges','morphology','grabcut','jpeg','webp'])
def test_algorithms_produce_input_sized_pixels(method):
    a=synthetic_image(); assert output_rgb(process(a,method,{})).shape==a.shape

def test_invalid_and_unsuitable_images():
    with pytest.raises(ValueError): decode(b'not an image')
    with pytest.raises(ValueError): process(synthetic_image(),'gamma',{'gamma':0})
    with pytest.raises(ValueError): register(np.zeros((64,64,3),np.uint8),np.zeros((64,64,3),np.uint8))

def test_sift_ransac_recovers_known_translation():
    rng=np.random.default_rng(12); a=rng.integers(0,256,(240,240,3),dtype=np.uint8)
    H=np.float64([[1,0,8],[0,1,12],[0,0,1]]); b=cv2.warpPerspective(a,H,(240,240))
    r=register(a,b); assert r['inliers']>=10
    np.testing.assert_allclose(np.array(r['homography'])[:2,2],[8,12],atol=1)
