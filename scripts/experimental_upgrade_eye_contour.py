"""Stronger eye-contour cosmetic experiment, never imported by production.

Unlike source-copy geometry, this proposes a defined, modestly narrower aperture
and raised outer corners. It preserves pupil-core pixels, not the full inferred
iris disk (which can overlap the eyelid). This is not identity conditioning.
"""
import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def contour_polish(rgb, points, hair, strength=1., aperture_scale=.82):
    from flux2_klein9b_attractiveness import _EYE_CONTOURS, _IRISES, _BROWS, _OVAL, _LIPS
    from experimental_upgrade_smile_balance import measure_smile
    original=np.asarray(rgb,np.float32);points=np.asarray(points,np.float32)
    if (original.ndim!=3 or original.shape[-1]!=3 or points.shape!=(478,2)
        or np.asarray(hair).shape!=original.shape[:2] or not np.isfinite(original).all()
        or not np.isfinite(points).all() or not np.isfinite(strength) or not 0<=strength<=1
        or aperture_scale not in (.82,1.)):
        raise ValueError('Expected finite RGB,478 landmarks,matching hair mask,strength0..1.')
    h,w=original.shape[:2];zero=np.zeros((h,w),np.float32)
    if strength==0: return original.copy(),zero,{'status':'disabled'}
    frame=measure_smile(points)
    normal=frame['normal']
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    field=np.zeros((h,w,2),np.float32)
    guard=np.zeros((h,w),np.uint8)
    for ids in (*_BROWS,_LIPS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((5,5),np.uint8))
    face=np.zeros_like(guard)
    cv2.fillPoly(face,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    guard[(face==0)|(np.asarray(hair)>0)]=255
    pupil_mask=np.zeros_like(guard);eyes=[]
    for contour,iris in zip(_EYE_CONTOURS,_IRISES):
        eye=points[list(contour)];outer,inner=eye[0],eye[8]
        width=float(np.linalg.norm(inner-outer))
        if width<8: raise ValueError('Eye is too small for controlled contour editing.')
        axis=(inner-outer)/width;vertical=np.array([-axis[1],axis[0]],np.float32)
        if vertical@normal<0: vertical=-vertical
        basis=np.stack((axis,vertical),axis=1)
        center=points[iris[0]]
        # Definition is relative to the present eye, not a fabricated reference face.
        local=(eye-(outer+inner)/2)@basis
        proposed=local.copy()
        proposed[:,0]*=1.035
        proposed[:,1]*=aperture_scale
        outer_weight=np.clip(.5-local[:,0]/width,0,1)**2
        proposed[:,1]-=width*.035*outer_weight
        shifts=((proposed-local)@basis.T)*strength
        length=np.linalg.norm(shifts,axis=1)
        shifts*=np.minimum(1.,width*.08/np.maximum(length,1e-8))[:,None]
        iris_radius=float(np.linalg.norm(points[list(iris[1:])]-center,axis=1).mean())
        core_radius=max(1.,iris_radius*.32)
        pupil_mask[((xx-center[0])**2+(yy-center[1])**2)<=core_radius**2]=255
        theta=np.arange(24)*2*np.pi/24
        boundary=center+np.column_stack((np.cos(theta)*width*.9,np.sin(theta)*width*.5))@basis.T
        angle=np.arange(8)*2*np.pi/8
        core=center+np.column_stack((np.cos(angle),np.sin(angle)))*core_radius
        fixed=np.concatenate((center[None],core,boundary))
        targets=np.concatenate((fixed,eye+shifts))
        vectors=np.concatenate((np.zeros_like(fixed),shifts))
        kept=[]
        for index,p in enumerate(targets):
            if not kept or np.linalg.norm(targets[kept]-p,axis=1).min()>.35: kept.append(index)
        mapper=RBFInterpolator((targets[kept]-center)/width,vectors[kept]/width,
                              kernel='thin_plate_spline',smoothing=1e-5)
        x0=max(0,int(center[0]-width));x1=min(w,int(center[0]+width)+1)
        y0=max(0,int(center[1]-width));y1=min(h,int(center[1]+width)+1)
        coordinates=np.column_stack((xx[y0:y1,x0:x1].ravel(),yy[y0:y1,x0:x1].ravel()))
        local_field=(mapper((coordinates-center)/width)*width).reshape(y1-y0,x1-x0,2)
        uv=(coordinates-center)@basis
        radius=np.sqrt((uv[:,0]/(width*.9))**2+(uv[:,1]/(width*.5))**2).reshape(y1-y0,x1-x0)
        local_field*=np.clip((1-radius)/.25,0,1)[...,None]
        lengths=np.linalg.norm(local_field,axis=2)
        local_field*=np.minimum(1.,width*.08/np.maximum(lengths,1e-8))[...,None]
        field[y0:y1,x0:x1]+=local_field
        eyes.append({'width_pixels':width,'requested_max_control_shift_pixels':float(np.linalg.norm(shifts,axis=1).max()),
                     'pupil_core_radius_pixels':core_radius})
    guard=np.maximum(guard,pupil_mask)
    distance=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
    field*=np.clip(distance/2.,0,1)[...,None]
    dy_x,dx_x=np.gradient(field[:,:,0]);dy_y,dx_y=np.gradient(field[:,:,1])
    active=np.linalg.norm(field,axis=2)>.001
    fraction=1.
    for _ in range(5):
        jacobian=(1-fraction*dx_x)*(1-fraction*dy_y)-fraction*fraction*dy_x*dx_y
        minimum=float(jacobian[active].min(initial=1.))
        if minimum>=.25: break
        fraction*=.85
    if minimum<.25 or fraction<.6: raise RuntimeError('Requested contour edit cannot retain a safe deformation field.')
    field*=fraction
    output=cv2.remap(original,xx-field[:,:,0],yy-field[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    output=np.clip(output,0,1);output[~active]=original[~active]
    if not np.array_equal(output[guard>0],original[guard>0]): raise RuntimeError('Protected feature changed.')
    return output,active.astype(np.float32),{'status':'experimental_not_promoted','eyes':eyes,
        'strength':strength,'aperture_scale_requested':aperture_scale,'width_scale_requested':1.035,
        'outer_corner_lift_eye_width_requested':.035,'minimum_inverse_jacobian':minimum,
        'safety_fraction':fraction,'maximum_field_pixels':float(np.linalg.norm(field,axis=2).max()),
        'pupil_core_pixels_exact_before_optional_gaze_correction':True,
        'brows_mouth_nose_hair_outline_exact':True,'source_pixels_copied':False,'identity_conditioning':False,
        'limitation':'2D remapping may distort iris edges or look squinted. Inspect before acceptance; requested aperture is not achieved-measurement proof.'}
