"""Registered blend of two generated variants, not trained identity conditioning.

Never imported by production. No genuine identity-photo pixels are used here.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def inverse_field(targets, samples, shape, support, scale):
    """Fit output-to-input displacements and reject folded/oversized maps."""
    targets=np.asarray(targets,np.float64);samples=np.asarray(samples,np.float64)
    kept=[]
    for i,point in enumerate(targets):
        if not kept or np.linalg.norm(targets[kept]-point,axis=1).min()>.45:
            kept.append(i)
    if len(kept)<6: raise ValueError('Insufficient distinct alignment controls.')
    center=targets.mean(axis=0)
    mapper=RBFInterpolator((targets[kept]-center)/scale,
        (samples[kept]-targets[kept])/scale,kernel='thin_plate_spline',smoothing=1e-5)
    h,w=shape
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    selected=support>0
    coordinates=np.column_stack((xx[selected],yy[selected]))
    field=np.zeros((h,w,2),np.float32)
    values=np.empty_like(coordinates)
    for start in range(0,len(coordinates),4096):
        values[start:start+4096]=mapper((coordinates[start:start+4096]-center)/scale)*scale
    field[selected]=values*support[selected,None]
    dy_x,dx_x=np.gradient(field[:,:,0]);dy_y,dx_y=np.gradient(field[:,:,1])
    jacobian=(1+dx_x)*(1+dy_y)-dy_x*dx_y
    minimum=float(jacobian[selected].min(initial=1))
    maximum=float(np.linalg.norm(field,axis=2).max(initial=0))
    if not np.isfinite(field).all() or minimum<.25 or maximum>scale*.20:
        raise ValueError(f'Unsafe inverse field: min Jacobian={minimum:.6f}, max shift={maximum:.3f}px')
    fit=targets[kept]+mapper((targets[kept]-center)/scale)*scale
    fit_error=np.linalg.norm(fit-samples[kept],axis=1)
    return field,{'control_count':len(kept),'minimum_inverse_jacobian':minimum,
        'maximum_displacement_pixels':maximum,'maximum_fitted_control_error_pixels':float(fit_error.max()),
        'note':'Fitted-control error is before the boundary taper; inspect effective alignment visually.'}


def registered_blend(base, beauty, base_points, beauty_points, hair, amount=.4):
    from flux2_klein9b_attractiveness import _OVAL
    base=np.asarray(base,np.float32);beauty=np.asarray(beauty,np.float32)
    bp=np.asarray(base_points,np.float32);pp=np.asarray(beauty_points,np.float32)
    if (base.ndim!=3 or base.shape[-1]!=3 or beauty.shape!=base.shape
            or bp.shape!=(478,2) or pp.shape!=(478,2) or np.asarray(hair).shape!=base.shape[:2]
            or not all(np.isfinite(a).all() for a in (base,beauty,bp,pp))
            or not np.isfinite(amount) or not 0<=amount<=1
            or base.min()<0 or base.max()>1 or beauty.min()<0 or beauty.max()>1):
        raise ValueError('Expected matched0..1 RGB images,478 landmarks,hair mask and amount0..1.')
    h,w=base.shape[:2]
    if amount==0 or (np.array_equal(base,beauty) and np.array_equal(bp,pp)):
        return base.copy(),np.zeros((h,w),np.float32),{'status':'no_op'},{}
    axis=bp[263]-bp[33];length=float(np.linalg.norm(axis))
    if length<8: raise ValueError('Degenerate facial alignment.')
    axis/=length
    scale=float(np.ptp(bp[list(_OVAL)]@axis))
    if scale<20: raise ValueError('Face is too small for this diagnostic.')
    desired=bp+float(amount)*(pp-bp)
    # Retain the base head outline/hairline. Internal eye, brow, cheek, nose and
    # lip controls share the same interpolation fraction rather than two faces
    # being dissolved at different feature locations.
    desired[list(_OVAL)]=bp[list(_OVAL)]
    face=np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(bp[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,np.ones((3,3),np.uint8))
    hair_guard=cv2.dilate((np.asarray(hair)>0).astype(np.uint8),np.ones((3,3),np.uint8))
    face[hair_guard>0]=0
    distance=cv2.distanceTransform((face>0).astype(np.uint8),cv2.DIST_L2,5)
    support=np.clip(distance/max(4.,scale*.065),0,1)
    support[support<.01]=0
    first,first_report=inverse_field(desired,bp,(h,w),support,scale)
    second,second_report=inverse_field(desired,pp,(h,w),support,scale)
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    def warp(rgb,field):
        return np.clip(cv2.remap(rgb,xx+field[:,:,0],yy+field[:,:,1],
            cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101),0,1)
    aligned_base=warp(base,first);aligned_beauty=warp(beauty,second)
    alpha=support*float(amount)
    result=aligned_base+(aligned_beauty-aligned_base)*alpha[...,None]
    result[support==0]=base[support==0]
    report={'status':'experimental_not_promoted','amount':float(amount),
        'base_alignment':first_report,'beauty_alignment':second_report,
        'face_width_pixels':scale,'boundary_taper_pixels':max(4.,scale*.065),
        'outside_mask_max_error_0_to_255':float(np.abs(result-base)[support==0].max(initial=0)*255),
        'hair_pixels_exact':bool(np.array_equal(result[hair_guard>0],base[hair_guard>0])),
        'identity_conditioning':False,'source_photo_pixels_copied':False,
        'generated_variant_pixels_blended':True,'outline_controls_fixed':True,
        'limitation':'Registered face-region composite, not native whole-frame output or a proven identity lock. Gaze, seams, double features and likeness require evaluation.'}
    return (result.astype(np.float32),support.astype(np.float32),report,
        {'aligned_base':aligned_base,'aligned_beauty':aligned_beauty})
