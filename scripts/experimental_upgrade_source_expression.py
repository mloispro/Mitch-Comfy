"""Offline source-relative eye-contour and closed-smile geometry prototype.

Deforms candidate pixels, never copies source pixels. This is cosmetic geometry,
not identity conditioning. Iris/pupil pixels, nose, brows, hair and head outline
are explicitly protected. No production imports this module.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def apply_source_expression(rgb, points, source_points, hair, strength=.85):
    from flux2_klein9b_attractiveness import _EYE_CONTOURS, _IRISES, _BROWS, _OVAL
    from mediapipe.python.solutions.face_mesh_connections import FACEMESH_LIPS
    from experimental_upgrade_smile_balance import measure_smile
    import experimental_upgrade_smile_balance as smile
    original=np.asarray(rgb,np.float32)
    points=np.asarray(points,np.float32); source_points=np.asarray(source_points,np.float32)
    if original.ndim!=3 or original.shape[-1]!=3 or points.shape!=(478,2) or source_points.shape!=(478,2):
        raise ValueError('Expected RGB and478 source/candidate landmarks.')
    if not all(np.isfinite(a).all() for a in (original,points,source_points)) or not 0<=strength<=1:
        raise ValueError('Finite inputs and strength0..1 required.')
    h,w=original.shape[:2]
    if np.asarray(hair).shape!=(h,w): raise ValueError('Hair mask must match image.')
    empty=np.zeros((h,w),np.float32)
    if strength==0:
        return original.copy(),empty,{'status':'disabled','protected_pixel_max_error_0_to_255':0}
    frame=measure_smile(points); source_frame=measure_smile(source_points)
    candidate_basis=np.stack((frame['tangent'],frame['normal']),axis=1)
    source_basis=np.stack((source_frame['tangent'],source_frame['normal']),axis=1)
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    shift_x=empty.copy(); shift_y=empty.copy(); guard=np.zeros((h,w),np.uint8)
    for ids in _BROWS:
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((7,7),np.uint8))
    for ids in _IRISES:
        cv2.fillPoly(guard,[np.rint(points[list(ids[1:])]).astype(np.int32)],255)
    guard[np.asarray(hair)>0]=255
    face=np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    guard[face==0]=255
    eye_reports=[]
    for contour,iris in zip(_EYE_CONTOURS,_IRISES):
        eye=points[list(contour)]
        source_eye=source_points[list(contour)]
        width=max(float(np.linalg.norm(eye[8]-eye[0])),1.)
        source_width=max(float(np.linalg.norm(source_eye[8]-source_eye[0])),1.)
        center=points[iris[0]]; source_center=source_points[iris[0]]
        relative=(source_eye-source_center)@source_basis/source_width
        desired=center+(relative*width)@candidate_basis.T
        requested=(desired-eye)*float(strength)
        length=np.linalg.norm(requested,axis=1)
        shifts=requested*np.minimum(1.,width*.085/np.maximum(length,1e-8))[:,None]
        # Stable outer anchors confine the interpolation to this eye neighborhood.
        theta=np.arange(16)*2*np.pi/16
        boundary=center+np.column_stack((np.cos(theta)*width*.85,np.sin(theta)*width*.48))@candidate_basis.T
        moving=eye+shifts
        targets=np.concatenate((points[list(iris)],boundary,moving),axis=0)
        vectors=np.concatenate((np.zeros((len(iris)+len(boundary),2),np.float32),shifts),axis=0)
        # Near-coincident iris/lid controls prioritize the fixed iris anchor.
        kept=[]
        for index,p in enumerate(targets):
            if not kept or np.linalg.norm(targets[kept]-p,axis=1).min()>.4:
                kept.append(index)
        interpolator=RBFInterpolator((targets[kept]-center)/width,vectors[kept]/width,
                                    kernel='thin_plate_spline',smoothing=1e-5)
        x0=max(0,int(center[0]-width)); x1=min(w,int(center[0]+width)+1)
        y0=max(0,int(center[1]-width)); y1=min(h,int(center[1]+width)+1)
        coordinates=np.column_stack((xx[y0:y1,x0:x1].ravel(),yy[y0:y1,x0:x1].ravel()))
        field=(interpolator((coordinates-center)/width)*width).reshape(y1-y0,x1-x0,2)
        local=(coordinates-center)@candidate_basis
        radius=np.sqrt((local[:,0]/(width*.85))**2+(local[:,1]/(width*.48))**2).reshape(y1-y0,x1-x0)
        gate=np.clip((1-radius)/.18,0,1)
        field*=gate[...,None]
        length=np.linalg.norm(field,axis=2)
        field*=np.minimum(1.,width*.085/np.maximum(length,1e-8))[...,None]
        shift_x[y0:y1,x0:x1]+=field[...,0]
        shift_y[y0:y1,x0:x1]+=field[...,1]
        eye_reports.append({'source_relative_targets_include_corner_angle':True,
                            'maximum_control_shift_pixels':float(np.linalg.norm(shifts,axis=1).max()),
                            'maximum_control_shift_eye_width_fraction':.085})
    distance=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
    protection=np.clip(distance/3.,0,1)
    shift_x*=protection; shift_y*=protection
    dx_y,dx_x=np.gradient(shift_x); dy_y,dy_x=np.gradient(shift_y)
    jacobian=(1-dx_x)*(1-dy_y)-dx_y*dy_x
    active=np.hypot(shift_x,shift_y)>.001
    minimum_jacobian=float(jacobian[active].min(initial=1.))
    if minimum_jacobian<.20: raise RuntimeError(f'Eye deformation fold/compression risk: Jacobian {minimum_jacobian:.3f}')
    eye_output=cv2.remap(original,xx-shift_x,yy-shift_y,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    eye_output[~active]=original[~active]
    # The existing compact mouth-column transform moves both lips together. Use
    # a larger, explicit bound in this isolated module only; restore it reliably.
    old_bound=smile.MAX_CORNER_SHIFT_MOUTH_WIDTH
    try:
        smile.MAX_CORNER_SHIFT_MOUTH_WIDTH=.07
        _,_,mouth_report=smile.apply_smile_balance(
            eye_output,points,source_points,hair,float(strength))
    finally:
        smile.MAX_CORNER_SHIFT_MOUTH_WIDTH=old_bound
    # Refinement: the same requested corner offsets now drive a continuous TPS
    # over all lip-contour points and surrounding skin, with fixed nose/boundary
    # anchors. The previous compact displacement left a visible corner crease.
    output=eye_output.copy(); mouth_mask=empty.copy(); mouth_jacobian=1.
    if mouth_report['status']=='applied':
        width=frame['width']; center=frame['center']
        lip_ids=sorted({i for edge in FACEMESH_LIPS for i in edge})
        lips=points[lip_ids]
        local=(lips-center)@candidate_basis
        corners=frame['corner_coordinates']*width
        corner_shifts=np.array(mouth_report['applied_corner_shifts_local_pixels'],np.float32)
        vectors_local=np.zeros_like(local)
        for corner,shift in zip(corners,corner_shifts):
            d=np.abs(local[:,0]-corner[0])/max(width*.46,1.)
            weight=np.where(d<1,(1-d*d)**2,0)
            vectors_local+=weight[:,None]*shift
        lip_shifts=vectors_local@candidate_basis.T
        theta=np.arange(20)*2*np.pi/20
        boundary=center+np.column_stack((np.cos(theta)*width*.95,np.sin(theta)*width*.62))@candidate_basis.T
        nose_theta=np.arange(8)*2*np.pi/8
        nose_anchors=points[1]+np.column_stack((np.cos(nose_theta),np.sin(nose_theta)))*16.
        targets=np.concatenate((nose_anchors,boundary,lips+lip_shifts))
        vectors=np.concatenate((np.zeros((len(nose_anchors)+len(boundary),2)),lip_shifts))
        kept=[]
        for index,p in enumerate(targets):
            if not kept or np.linalg.norm(targets[kept]-p,axis=1).min()>.4: kept.append(index)
        mapping=RBFInterpolator((targets[kept]-center)/width,vectors[kept]/width,
                                kernel='thin_plate_spline',smoothing=1e-5)
        x0=max(0,int(center[0]-width*1.1)); x1=min(w,int(center[0]+width*1.1)+1)
        y0=max(0,int(center[1]-width*1.1)); y1=min(h,int(center[1]+width*1.1)+1)
        coordinates=np.column_stack((xx[y0:y1,x0:x1].ravel(),yy[y0:y1,x0:x1].ravel()))
        field=(mapping((coordinates-center)/width)*width).reshape(y1-y0,x1-x0,2)
        local=(coordinates-center)@candidate_basis
        radius=np.sqrt((local[:,0]/(width*.95))**2+(local[:,1]/(width*.62))**2).reshape(y1-y0,x1-x0)
        field*=np.clip((1-radius)/.18,0,1)[...,None]
        # Large mouth displacements need a proportionally wider approach to
        # fixed nose/outline pixels than the small eye field's three-pixel ramp.
        mouth_protection=np.clip(distance/max(3.,width*.07*3.),0,1)
        field*=mouth_protection[y0:y1,x0:x1,None]
        lengths=np.linalg.norm(field,axis=2)
        field*=np.minimum(1.,width*.07/np.maximum(lengths,1e-8))[...,None]
        mouth_x=empty.copy(); mouth_y=empty.copy()
        mouth_x[y0:y1,x0:x1]=field[...,0]; mouth_y[y0:y1,x0:x1]=field[...,1]
        mx_y,mx_x=np.gradient(mouth_x); my_y,my_x=np.gradient(mouth_y)
        mouth_active=np.hypot(mouth_x,mouth_y)>.001
        # Deterministic safety line search, not a user-visible strength sweep.
        # Never emit a folded field; reject if safety would remove most of the edit.
        safe_fraction=1.
        for _ in range(5):
            f=safe_fraction
            mouth_jacobian=float(((1-f*mx_x)*(1-f*my_y)-f*f*mx_y*my_x)[mouth_active].min(initial=1.))
            if mouth_jacobian>=.25: break
            safe_fraction*=.85
        if mouth_jacobian<.25 or safe_fraction<.60:
            raise RuntimeError(f'Mouth deformation cannot safely retain requested edit: Jacobian {mouth_jacobian:.3f}, fraction {safe_fraction:.3f}')
        mouth_x*=safe_fraction; mouth_y*=safe_fraction
        output=cv2.remap(eye_output,xx-mouth_x,yy-mouth_y,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
        output[~mouth_active]=eye_output[~mouth_active]
        mouth_mask=mouth_active.astype(np.float32)
        mouth_report['deformation_solver']='continuous_lip_contour_TPS_fixed_nose_and_boundary'
        mouth_report['safety_retained_displacement_fraction']=safe_fraction
        mouth_report['fixed_feature_transition_pixels']=max(3.,width*.07*3.)
        mouth_report['maximum_field_shift_pixels']=float(np.hypot(mouth_x,mouth_y).max())
        mouth_report['upper_and_lower_lips_share_same_displacement']='same target per column; interpolated field measured separately'
    output=np.clip(output,0,1)
    mask=np.maximum(active.astype(np.float32),mouth_mask)
    output[mask==0]=original[mask==0]
    protected_error=float(np.abs(output-original)[guard>0].max(initial=0)*255)
    if protected_error>1e-5: raise RuntimeError('Protected iris/brow/nose/hair pixels changed.')
    report={'status':'applied','profile':'experimental_source_contour_and_smile_geometry_v1',
            'strength':float(strength),'eyes':eye_reports,'smile':mouth_report,
            'minimum_eye_inverse_jacobian':minimum_jacobian,
            'minimum_mouth_inverse_jacobian':mouth_jacobian,
            'maximum_eye_field_shift_pixels':float(np.hypot(shift_x,shift_y).max()),
            'protected_pixel_max_error_0_to_255':protected_error,
            'source_pixels_copied':False,'identity_conditioning':False,
            'pupil_and_iris_pixels_exact':True,'head_pose_change_requested':False,
            'limitation':'2D expression deformation; visual likeness, gaze and interpolation quality still require evaluation.'}
    return output.astype(np.float32),mask.astype(np.float32),report
