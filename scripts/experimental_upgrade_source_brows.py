"""Offline source-relative brow deformation; no source pixels or generation.

The existing accepted-identity image supplies every output pixel. Only a bounded
brow neighborhood is remapped; the entire eye, nose, lips, hair and face outline
are fixed. This is cosmetic geometry, not an identity-conditioning mechanism.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def brow_frames(points):
    from flux2_klein9b_attractiveness import _BROWS, _EYE_CONTOURS
    tangent=points[263]-points[33]
    span=float(np.linalg.norm(tangent))
    if span<1: raise ValueError('Degenerate eye span.')
    tangent=tangent/span
    normal=np.array([-tangent[1],tangent[0]],np.float32)
    if np.dot(points[152]-points[1],normal)<0: normal=-normal
    basis=np.stack((tangent,normal),axis=1)
    result=[]
    for brow,eye in zip(_BROWS,_EYE_CONTOURS):
        center=(points[eye[0]]+points[eye[8]])/2
        width=float(np.linalg.norm(points[eye[8]]-points[eye[0]]))
        if width<2: raise ValueError('Degenerate eye width.')
        relative=(points[list(brow)]-center)@basis/width
        result.append(dict(center=center,width=width,basis=basis,relative=relative))
    return result


def soften_glabellar_band(rgb,points,hair,fine_cutoff_scale=1.):
    """One bounded, symmetric frequency correction above/between the brows.

    Not the rejected dark-trough filler: both light and dark mid-band deviations
    are attenuated. Fine residual and broad base are retained algebraically.
    """
    from flux2_klein9b_attractiveness import _BROWS, _EYE_CONTOURS, _OVAL, _LIPS
    original=np.asarray(rgb,np.float32);points=np.asarray(points,np.float32)
    if (original.ndim!=3 or original.shape[-1]!=3 or points.shape!=(478,2)
            or np.asarray(hair).shape!=original.shape[:2]
            or not np.isfinite(original).all() or not np.isfinite(points).all()
            or fine_cutoff_scale not in (1.,2.)):
        raise ValueError('Expected finite RGB,478 landmarks and matching hair mask.')
    h,w=original.shape[:2];frames=brow_frames(points)
    eye_center=(frames[0]['center']+frames[1]['center'])/2
    span=float(np.linalg.norm(frames[1]['center']-frames[0]['center']))
    if span<2: raise ValueError('Degenerate eye-center span.')
    basis=frames[0]['basis']
    inner=[]
    for ids in _BROWS:
        brow=points[list(ids)];inner.append(brow[np.linalg.norm(brow-eye_center,axis=1).argmin()])
    center=np.mean(inner,axis=0)-basis[:,1]*span*.14
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    uv=np.stack((xx-center[0],yy-center[1]),axis=-1)@basis
    alpha=np.exp(-.5*((uv[...,0]/(span*.16))**2+(uv[...,1]/(span*.36))**2))
    guard=np.zeros((h,w),np.uint8)
    for ids in (*_BROWS,*_EYE_CONTOURS,_LIPS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((9,9),np.uint8))
    face=np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    v=(xx-eye_center[0])*basis[0,1]+(yy-eye_center[1])*basis[1,1]
    guard[(face==0)|(np.asarray(hair)>0)|(v>-span*.12)]=255
    distance=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
    alpha*=np.clip(distance/max(3.,span*.05),0,1)
    alpha[alpha<.005]=0
    measurement_sigma=max(.7,span*.006)
    fine_sigma=measurement_sigma*fine_cutoff_scale;broad_sigma=max(3.,span*.065)
    fine=cv2.GaussianBlur(original,(0,0),fine_sigma)
    broad=cv2.GaussianBlur(original,(0,0),broad_sigma)
    correction=np.clip(-(fine-broad)*alpha[...,None]*.85,-15/255,15/255)
    result=np.clip(original+correction,0,1);result[alpha==0]=original[alpha==0]
    region=alpha>.3
    def contrast_bands(photo):
        if not region.any(): return 0.,0.
        # Keep evaluation frequencies fixed across the cutoff refinement.
        small=cv2.GaussianBlur(photo,(0,0),measurement_sigma)
        large=cv2.GaussianBlur(photo,(0,0),broad_sigma)
        return float((photo-small)[region].std()),float((small-large)[region].std())
    before=contrast_bands(original);after=contrast_bands(result)
    fine_retention=after[0]/before[0] if before[0]>1e-8 else (1. if after[0]<=1e-8 else 0.)
    mean_shift=float(np.mean(result[region]-original[region])*255) if region.any() else 0.
    guard_passed=bool(region.any() and fine_retention>=.90 and abs(mean_shift)<=4)
    return result,(alpha>0).astype(np.float32),{
        'profile':'experimental_glabellar_symmetric_mid_band_v1','fine_sigma':fine_sigma,'broad_sigma':broad_sigma,
        'fine_cutoff_scale':fine_cutoff_scale,'measurement_sigma_unchanged':measurement_sigma,
        'fine_band_std_before':before[0],'fine_band_std_after':after[0],'fine_band_retention':fine_retention,
        'mid_band_std_before':before[1],'mid_band_std_after':after[1],
        'region_mean_rgb_shift_0_to_255':mean_shift,'max_channel_change_limit_0_to_255':15,
        'texture_exposure_guard_passed':guard_passed,'minimum_fine_band_retention':.90,'maximum_abs_mean_shift_0_to_255':4,
        'feature_guard_pixel_max_error_0_to_255':float(np.abs(result-original)[guard>0].max(initial=0)*255),
        'source_pixels_copied':False,'geometric_warp':False,
        'limitation':'Local contrast attenuation, not proof of a relaxed/attractive expression. Fine residual retained algebraically; resampled-band measurement is diagnostic.'}


def apply_source_brows(rgb,points,source_points,hair,strength=.8):
    from flux2_klein9b_attractiveness import _BROWS, _EYE_CONTOURS, _OVAL, _LIPS
    original=np.asarray(rgb,np.float32)
    points=np.asarray(points,np.float32); source_points=np.asarray(source_points,np.float32)
    if (original.ndim!=3 or original.shape[-1]!=3 or points.shape!=(478,2)
            or source_points.shape!=(478,2) or np.asarray(hair).shape!=original.shape[:2]
            or not np.isfinite(strength) or not 0<=strength<=1
            or not all(np.isfinite(a).all() for a in (original,points,source_points))):
        raise ValueError('Expected finite RGB, matching hair mask,478-point landmarks and strength0..1.')
    h,w=original.shape[:2]; empty=np.zeros((h,w),np.float32)
    if strength==0:
        return original.copy(),empty,{'status':'disabled','source_pixels_copied':False}
    frames=brow_frames(points); source_frames=brow_frames(source_points)
    guard=np.zeros((h,w),np.uint8)
    for ids in (*_EYE_CONTOURS,_LIPS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((5,5),np.uint8))
    face=np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    guard[(face==0)|(np.asarray(hair)>0)]=255
    distance=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    dx=empty.copy(); dy=empty.copy(); reports=[]
    for ids,eye,frame,source_frame in zip(_BROWS,_EYE_CONTOURS,frames,source_frames):
        width=frame['width']; basis=frame['basis']; brow=points[list(ids)]
        desired=frame['center']+(source_frame['relative']*width)@basis.T
        shift=(desired-brow)*strength
        lengths=np.linalg.norm(shift,axis=1)
        shift*=np.minimum(1.,width*.10/np.maximum(lengths,1e-8))[:,None]
        center=brow.mean(axis=0)
        angle=np.arange(24)*2*np.pi/24
        boundary=center+np.column_stack((np.cos(angle)*width*.95,np.sin(angle)*width*.55))@basis.T
        fixed=np.concatenate((points[list(eye)],boundary))
        targets=np.concatenate((fixed,brow+shift))
        vectors=np.concatenate((np.zeros_like(fixed),shift))
        kept=[]
        for i,point in enumerate(targets):
            if not kept or np.linalg.norm(targets[kept]-point,axis=1).min()>.4: kept.append(i)
        mapping=RBFInterpolator((targets[kept]-center)/width,vectors[kept]/width,
                                kernel='thin_plate_spline',smoothing=1e-5)
        x0=max(0,int(center[0]-width*1.2)); x1=min(w,int(center[0]+width*1.2)+1)
        y0=max(0,int(center[1]-width*1.2)); y1=min(h,int(center[1]+width*1.2)+1)
        coordinates=np.column_stack((xx[y0:y1,x0:x1].ravel(),yy[y0:y1,x0:x1].ravel()))
        field=(mapping((coordinates-center)/width)*width).reshape(y1-y0,x1-x0,2)
        local=(coordinates-center)@basis
        radius=np.sqrt((local[:,0]/(width*.95))**2+(local[:,1]/(width*.55))**2).reshape(y1-y0,x1-x0)
        field*=np.clip((1-radius)/.30,0,1)[...,None]
        field*=np.clip(distance[y0:y1,x0:x1]/max(3.,width*.30),0,1)[...,None]
        length=np.linalg.norm(field,axis=2)
        field*=np.minimum(1.,width*.10/np.maximum(length,1e-8))[...,None]
        dx[y0:y1,x0:x1]+=field[...,0]; dy[y0:y1,x0:x1]+=field[...,1]
        reports.append({'eye_width_pixels':width,'requested_max_shift_pixels':float(np.linalg.norm(shift,axis=1).max()),
                        'source_relative_brow_error_before':float(np.linalg.norm(frame['relative']-source_frame['relative'],axis=1).mean())})
    dx[guard>0]=0;dy[guard>0]=0
    dx_y,dx_x=np.gradient(dx);dy_y,dy_x=np.gradient(dy)
    active=np.hypot(dx,dy)>.001; fraction=1.
    for _ in range(5):
        jac=(1-fraction*dx_x)*(1-fraction*dy_y)-fraction*fraction*dx_y*dy_x
        minimum=float(jac[active].min(initial=1.))
        if minimum>=.30: break
        fraction*=.85
    if minimum<.30 or fraction<.60: raise RuntimeError('Brow deformation cannot safely retain enough of the requested edit.')
    dx*=fraction;dy*=fraction
    result=cv2.remap(original,xx-dx,yy-dy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    result=np.clip(result,0,1);result[~active]=original[~active]
    protected_error=float(np.abs(result-original)[guard>0].max(initial=0)*255)
    if protected_error>1e-5: raise RuntimeError('Brow-only edit changed protected pixels.')
    return result,active.astype(np.float32),{
        'status':'applied','profile':'experimental_source_relative_brows_v1','strength':float(strength),
        'brows':reports,'minimum_inverse_jacobian':minimum,'safety_retained_fraction':fraction,
        'maximum_field_shift_pixels':float(np.hypot(dx,dy).max()),
        'protected_pixel_max_error_0_to_255':protected_error,'source_pixels_copied':False,
        'identity_conditioning':False,'entire_eye_pixels_exact':True,'nose_lips_hair_outline_exact':True,
        'limitation':'Brow-shape geometry only; does not synthesize hairs or remove glabellar creases. Visual expression/identity and resampling quality need review.'}
