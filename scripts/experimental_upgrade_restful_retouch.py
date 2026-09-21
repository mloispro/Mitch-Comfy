"""Bounded CPU forehead/under-eye retouch experiment; no generation or face replacement.

Observed failure: existing High's narrow frequency band leaves broad frown/eye
creases almost unchanged. Separate broad lighting, crease bands and microtexture;
attenuate only crease bands within landmark-aligned regions. Feature boundaries,
hair, mouth, eyes, nose, face outline and the full background stay byte-exact.
"""
from __future__ import annotations

import cv2
import numpy as np


def apply_restful_retouch(rgb, points, hair, strength=1.0):
    from flux2_klein9b_attractiveness import _OVAL, _EYE_CONTOURS, _BROWS, _LIPS
    from mediapipe.python.solutions.face_mesh_connections import FACEMESH_NOSE
    original = np.asarray(rgb, np.float32)
    points = np.asarray(points, np.float32)
    if original.ndim != 3 or original.shape[2] != 3 or points.shape != (478,2):
        raise ValueError('Expected RGB and478landmarks.')
    if not np.isfinite(original).all() or not np.isfinite(points).all() or not 0 <= strength <= 1:
        raise ValueError('Finite input and strength0..1 required.')
    h,w = original.shape[:2]
    if np.asarray(hair).shape != (h,w):
        raise ValueError('Hair mask must match image.')
    def polygon(ids):
        mask = np.zeros((h,w),np.uint8)
        cv2.fillPoly(mask,[np.rint(points[list(ids)]).astype(np.int32)],255)
        return mask
    eye_centers = np.array([points[list(ids)].mean(axis=0) for ids in _EYE_CONTOURS])
    axis = eye_centers[1]-eye_centers[0]
    span = max(float(np.linalg.norm(axis)),1)
    axis /= span
    normal = np.array([-axis[1],axis[0]],np.float32)
    if np.dot(points[152]-points[1],normal) < 0:
        normal *= -1
    scale = span/160
    interior = cv2.erode(polygon(_OVAL),cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,(max(5,round(12*scale)|1),)*2))
    guards = np.maximum.reduce([polygon(ids) for ids in (*_EYE_CONTOURS,*_BROWS,_LIPS)])
    nose_ids = sorted(set(index for pair in FACEMESH_NOSE for index in pair))
    nose_hull = cv2.convexHull(np.rint(points[nose_ids]).astype(np.int32))
    cv2.fillConvexPoly(guards,nose_hull,255)
    cv2.circle(guards,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guards = cv2.dilate(guards,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                            (max(13,round(13*scale)|1),)*2))
    valid = (interior>0)&(guards==0)&(np.asarray(hair)==0)
    yy,xx = np.mgrid[:h,:w].astype(np.float32)
    def gaussian(center,sx,sy):
        delta_x,delta_y=xx-center[0],yy-center[1]
        u=delta_x*axis[0]+delta_y*axis[1]
        v=delta_x*normal[0]+delta_y*normal[1]
        return np.exp(-.5*((u/max(sx,1))**2+(v/max(sy,1))**2))
    forehead=gaussian(eye_centers.mean(axis=0)-normal*span*.65,span*.9,span*.52)
    below_eyes=np.zeros((h,w),np.float32)
    for ids in _EYE_CONTOURS:
        eye_points=points[list(ids)]
        eye_width=float(np.linalg.norm(eye_points[8]-eye_points[0]))
        center=eye_points[9:].mean(axis=0)+normal*eye_width*.21
        below_eyes=np.maximum(below_eyes,gaussian(center,eye_width*.57,eye_width*.24))
    # Soft approach to all protected features without leaking across their edges.
    distance=cv2.distanceTransform(valid.astype(np.uint8),cv2.DIST_L2,5)
    feather=np.clip(distance/max(3,scale*5),0,1)
    forehead*=feather
    below_eyes*=feather
    alpha=np.clip((.92*forehead+.70*below_eyes)*strength,0,.94)
    alpha[alpha<.008]=0
    alpha[~valid]=0
    fine_base=cv2.GaussianBlur(original,(0,0),max(.7,scale*.85))
    broad_base=cv2.GaussianBlur(original,(0,0),max(5,scale*13))
    crease_band=fine_base-broad_base
    result=original-crease_band*alpha[...,None]
    result=np.clip(result,0,1)
    result[alpha==0]=original[alpha==0]
    region=alpha>.40
    report={
        'profile':'experimental_broad_crease_band_retouch_v1','strength':float(strength),
        'geometric_warp':False,'source_pixels_copied':False,'new_detail_synthesized':False,
        'fine_scale_pixels':max(.7,scale*.85),'broad_scale_pixels':max(5,scale*13),
        'changed_pixels':int(np.any(result!=original,axis=2).sum()),
        'protected_pixel_max_error_0_to_255':float(np.abs(result[alpha==0]-original[alpha==0]).max(initial=0)*255),
        'crease_band_std_before':float(crease_band[region].std()) if region.any() else 0.,
        'crease_band_std_after_target':float((crease_band*(1-alpha[...,None]))[region].std()) if region.any() else 0.,
        'microtexture_component_retained':True,
        'notes':'Measured band attenuation is not proof of realism; inspect wrinkles, patches and identity.'}
    return result.astype(np.float32),alpha.astype(np.float32),report
