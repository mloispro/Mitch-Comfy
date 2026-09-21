"""Experimental eye/brow photometry; no production imports or identity claims."""
import cv2
import numpy as np


def feature_regions(shape, points):
    from flux2_klein9b_attractiveness import _EYE_CONTOURS,_IRISES,_BROWS,_UPPER_LIDS
    h,w=shape;points=np.asarray(points,np.float32)
    if points.shape!=(478,2) or not np.isfinite(points).all():
        raise ValueError('Expected478 finite landmarks.')
    yy,xx=np.mgrid[:h,:w].astype(np.float32);regions=[]
    for contour,iris,brow,upper in zip(_EYE_CONTOURS,_IRISES,_BROWS,_UPPER_LIDS):
        eye=np.zeros((h,w),np.uint8);brows=np.zeros_like(eye)
        cv2.fillPoly(eye,[np.rint(points[list(contour)]).astype(np.int32)],255)
        cv2.fillPoly(brows,[np.rint(points[list(brow)]).astype(np.int32)],255)
        width=float(np.linalg.norm(points[contour[8]]-points[contour[0]]))
        if width<8: raise ValueError('Eye is too small for this experiment.')
        center=points[iris[0]];ring=points[list(iris[1:])]
        rx,ry=np.maximum(np.ptp(ring,axis=0)/2,1.)
        radial=np.sqrt(((xx-center[0])/rx)**2+((yy-center[1])/ry)**2)
        inner_eye=cv2.erode(eye,np.ones((3,3),np.uint8))>0
        core=radial<=.4
        annulus=inner_eye&(radial>.42)&(radial<.82)
        limbal=inner_eye&(radial>=.82)&(radial<=1.05)
        sclera=inner_eye&(radial>1.15)
        regions.append({'eye':eye,'brow':brows,'inner_eye':inner_eye,'radial':radial,
                        'pupil_core':core,'annulus':annulus,'limbal':limbal,'sclera':sclera,
                        'width':width,'upper':points[list(upper)]})
    return regions


def definition_profile(rgb,points):
    rgb=np.asarray(rgb)
    if rgb.dtype!=np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise ValueError('Expected uint8 RGB.')
    photo=rgb.astype(np.float32)/255;gray=cv2.cvtColor(photo,cv2.COLOR_RGB2GRAY)
    saturation=cv2.cvtColor(photo,cv2.COLOR_RGB2HSV)[:,:,1]
    selected=np.zeros(rgb.shape[:2],np.uint8);rows=[]
    for region in feature_regions(rgb.shape[:2],points):
        # Existing bright catchlights are not iris pigment contrast.
        annulus=region['annulus']&(gray<.65)
        ring=region['limbal']&(gray<.65)
        sclera=region['sclera'];brow=region['brow']>0
        def percentiles(mask):
            if mask.sum()<3: return None
            return [float(v) for v in np.percentile(gray[mask],[10,50,90])]
        iris_values=percentiles(annulus);limbal_values=percentiles(ring)
        context=cv2.GaussianBlur(gray,(0,0),max(2.,region['width']*.1))
        rows.append({'eye_width_pixels':region['width'],
                     'sample_pixels':{'iris':int(annulus.sum()),'limbal':int(ring.sum()),'sclera':int(sclera.sum()),'brow':int(brow.sum())},
                     'iris_luma_p10_median_p90':iris_values,
                     'iris_contrast_span_over_median':(iris_values[2]-iris_values[0])/max(iris_values[1],1e-6) if iris_values else None,
                     'iris_median_saturation':float(np.median(saturation[annulus])) if annulus.any() else None,
                     'limbal_luma_p10_median_p90':limbal_values,
                     'sclera_luma_p10_median_p90':percentiles(sclera),
                     'brow_luma_p10_median_p90':percentiles(brow),
                     'brow_positive_local_dark_response_mean':float(np.maximum(context-gray,0)[brow].mean()) if brow.any() else None})
        selected[annulus|ring|sclera|brow]=255
        selected[region['pupil_core']]=0
    return selected,rows


def apply_eye_definition(rgb,points,hair,strength=1.):
    """Increase existing iris/brow luminance contrast; no geometry or hue target."""
    original=np.asarray(rgb,np.float32)
    if (original.ndim!=3 or original.shape[2]!=3 or np.asarray(hair).shape!=original.shape[:2]
        or not np.isfinite(original).all() or original.min()<0 or original.max()>1
        or not np.isfinite(strength) or not 0<=strength<=1):
        raise ValueError('Expected finite0..1 RGB, matching hair mask and strength0..1.')
    if strength==0: return original.copy(),np.zeros(original.shape[:2],np.float32),{'status':'disabled'}
    gray=cv2.cvtColor(original,cv2.COLOR_RGB2GRAY)
    delta=np.zeros(gray.shape,np.float32);protected=np.asarray(hair)>0
    regions=feature_regions(gray.shape,points);eye_reports=[]
    for region in regions:
        radial=region['radial']
        # No new eye white, pupil texture, catchlights, eye size or limbal ring.
        catchlight=(gray>=.45)&(region['eye']>0)&(radial<=1.1)
        protected|=region['pupil_core']|region['sclera']|catchlight
        sample=region['annulus']&~catchlight
        if sample.sum()<8: raise ValueError('Insufficient visible iris texture.')
        median=float(np.median(gray[sample]))
        disk=np.clip((1.05-radial)/.15,0,1)*np.clip((radial-.4)/.16,0,1)
        interior=cv2.distanceTransform((region['eye']>0).astype(np.uint8),cv2.DIST_L2,5)
        iris_alpha=disk*np.clip((interior-1)/1.5,0,1)
        iris_delta=np.clip(gray-median,-.08,.08)*float(strength)*iris_alpha
        iris_delta[np.abs(iris_delta)<.0001]=0
        context=cv2.GaussianBlur(gray,(0,0),max(2.,region['width']*.1))
        dark=np.maximum(context-gray,0)
        dark[dark<.002]=0
        brow_distance=cv2.distanceTransform((region['brow']>0).astype(np.uint8),cv2.DIST_L2,5)
        brow_alpha=np.clip(brow_distance/2,0,1)
        brow_delta=-np.minimum(dark*1.5,.075)*float(strength)*brow_alpha
        delta+=iris_delta+brow_delta
        eye_reports.append({'iris_median_luma_before':median,'iris_contrast_gain_requested':1+float(strength),
                            'brow_local_dark_gain_requested':1+1.5*float(strength),
                            'maximum_iris_luma_adjustment':.08*float(strength),
                            'maximum_brow_luma_adjustment':.075*float(strength)})
    delta[protected]=0
    target=np.maximum(gray+delta,.005)
    # RGB scaling retains per-pixel channel ratios, with a gamut-safe upper bound.
    gain=target/np.maximum(gray,1e-6)
    gain=np.minimum(gain,1/np.maximum(original.max(axis=2),1e-6))
    active=np.abs(delta)>.0001
    output=original*gain[:,:,None]
    output[~active]=original[~active];output[protected]=original[protected]
    active&=~protected
    if not np.array_equal(output[protected],original[protected]): raise RuntimeError('Protected pixels changed.')
    return output.astype(np.float32),active.astype(np.float32),{
        'status':'experimental_not_promoted','profile':'iris_brow_luminance_definition_v1','strength':float(strength),
        'eyes':eye_reports,'geometric_warp':False,'source_pixels_copied':False,'identity_conditioning':False,
        'pupil_core_sclera_catchlight_hair_pixels_exact':True,
        'changed_pixels':int(active.sum()),'maximum_rgb_change_0_to_255':float(np.abs(output-original).max()*255),
        'operation':'Bounded iris contrast about its existing median and existing brow-fiber dark contrast; gamut-safe RGB scaling.',
        'limitation':'Approximate iris masks and local contrast may look harsh or painted. No face/expression/skin improvement is implied.',
    }
