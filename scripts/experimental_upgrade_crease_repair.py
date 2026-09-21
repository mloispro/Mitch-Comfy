"""Selective crease repair prototype, not production or identity conditioning.

Unlike broad frequency attenuation, repair only detected elongated dark ridges
inside the forehead. Keep the eyes, brows, mouth, nose, hair and outline exact.
No new model, face replacement, geometry warp or whole-skin smoothing.
"""
from __future__ import annotations

import cv2
import numpy as np


def apply_crease_repair(rgb, points, hair, strength=.75):
    from flux2_klein9b_attractiveness import _OVAL, _EYE_CONTOURS, _BROWS, _LIPS
    from mediapipe.python.solutions.face_mesh_connections import FACEMESH_NOSE
    original=np.asarray(rgb,np.float32)
    points=np.asarray(points,np.float32)
    if original.ndim!=3 or original.shape[-1]!=3 or points.shape!=(478,2):
        raise ValueError('Expected RGB and478 landmarks.')
    if not np.isfinite(original).all() or not np.isfinite(points).all() or not 0<=strength<=1:
        raise ValueError('Finite inputs and strength0..1 required.')
    h,w=original.shape[:2]
    if np.asarray(hair).shape!=(h,w): raise ValueError('Hair mask must match image.')
    def polygon(ids):
        mask=np.zeros((h,w),np.uint8)
        cv2.fillPoly(mask,[np.rint(points[list(ids)]).astype(np.int32)],255)
        return mask
    eyes=np.array([points[list(ids)].mean(axis=0) for ids in _EYE_CONTOURS])
    axis=eyes[1]-eyes[0]; span=max(float(np.linalg.norm(axis)),1.); axis/=span
    normal=np.array([-axis[1],axis[0]],np.float32)
    if np.dot(points[152]-points[1],normal)<0: normal*=-1
    scale=span/160.
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    dx,dy=xx-eyes.mean(axis=0)[0],yy-eyes.mean(axis=0)[1]
    u=dx*axis[0]+dy*axis[1]; v=dx*normal[0]+dy*normal[1]
    forehead=(np.abs(u)<span*.95)&(v < -span*.18)&(v > -span*1.25)
    interior=cv2.erode(polygon(_OVAL),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
    guard=np.maximum.reduce([polygon(ids) for ids in (*_EYE_CONTOURS,*_BROWS,_LIPS)])
    nose_ids=sorted({i for edge in FACEMESH_NOSE for i in edge})
    cv2.fillConvexPoly(guard,cv2.convexHull(np.rint(points[nose_ids]).astype(np.int32)),255)
    # Match the conservative replay guard exactly; no mixed ellipse/rectangle semantics.
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((13,13),np.uint8))
    valid=forehead&(interior>0)&(guard==0)&(np.asarray(hair)==0)
    gray=cv2.cvtColor(original,cv2.COLOR_RGB2GRAY)
    smooth=cv2.GaussianBlur(gray,(0,0),max(.7,scale*.75))
    dxx=cv2.Sobel(smooth,cv2.CV_32F,2,0,ksize=3)
    dyy=cv2.Sobel(smooth,cv2.CV_32F,0,2,ksize=3)
    dxy=cv2.Sobel(smooth,cv2.CV_32F,1,1,ksize=3)
    discriminant=np.sqrt((dxx-dyy)**2+4*dxy*dxy)
    eigen_max=(dxx+dyy+discriminant)*.5
    eigen_min=(dxx+dyy-discriminant)*.5
    local=cv2.GaussianBlur(gray,(0,0),max(2.,scale*3.5))
    # Elongated dark troughs, not round pores or every high-frequency skin pixel.
    ridges=valid&(eigen_max>.0035)&(eigen_max>np.abs(eigen_min)*2.8)&(local-gray>.007)
    connected=cv2.morphologyEx(ridges.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(connected,8)
    selected=np.zeros((h,w),np.uint8); accepted=0
    for index in range(1,count):
        area=int(stats[index,cv2.CC_STAT_AREA])
        coords=np.column_stack(np.where(labels==index)).astype(np.float32)
        if area<max(6,round(scale*7)) or area>max(250,round(span*span*.012)): continue
        lengths=np.linalg.eigvalsh(np.cov(coords.T))
        elongation=float(lengths[-1]/max(lengths[0],.25))
        if elongation<4.0: continue
        selected[labels==index]=255; accepted+=1
    radius=max(1,round(scale*1.2))
    selected=cv2.dilate(selected,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,)*2))
    selected[~valid]=0
    selection_fraction=float(np.count_nonzero(selected)/max(1,np.count_nonzero(valid)))
    if selection_fraction>.22: raise RuntimeError('Crease selection too broad; reject instead of smoothing the face.')
    image=np.rint(np.clip(original,0,1)*255).astype(np.uint8)
    repaired=cv2.inpaint(image,selected,max(2.,scale*3.),cv2.INPAINT_TELEA).astype(np.float32)/255.
    alpha=cv2.GaussianBlur(selected.astype(np.float32)/255,(0,0),max(.65,scale*.6))
    alpha[~valid]=0; alpha[alpha<.005]=0; alpha*=float(strength)
    output=np.clip(original+(repaired-original)*alpha[...,None],0,1)
    output[alpha==0]=original[alpha==0]
    delta=np.abs(output-original)
    report={
        'profile':'experimental_selected_forehead_ridge_repair_v1','strength':float(strength),
        'selected_components':accepted,'selected_forehead_fraction':selection_fraction,
        'changed_pixels':int(np.any(delta>0,axis=2).sum()),
        'protected_pixel_max_error_0_to_255':float(delta[alpha==0].max(initial=0)*255),
        'feature_guard_pixel_max_error_0_to_255':float(delta[guard>0].max(initial=0)*255),
        'geometric_warp':False,'source_pixels_copied':False,'new_model':False,
        'operation':'local Telea interpolation of selected elongated forehead creases only',
        'limitation':'Interpolated crease pixels do not preserve original microtexture; untouched skin is exact. Visual review required.'}
    return output.astype(np.float32),alpha.astype(np.float32),report
