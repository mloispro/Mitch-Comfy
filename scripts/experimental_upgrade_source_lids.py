"""Bounded source upper-lid curvature, with visible pupil-core protection.

CPU cosmetic remapping of candidate pixels. No source RGB, identity conditioning,
iris reconstruction, new eye width/corner angle, mouth or full-face deformation.
"""
import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator


def upper_lid_targets(points, source_points, ids):
    current=points[list(ids)]
    source=source_points[list(ids)]
    axis=current[-1]-current[0];width=float(np.linalg.norm(axis))
    source_axis=source[-1]-source[0];source_width=float(np.linalg.norm(source_axis))
    if min(width,source_width)<8: raise ValueError('Eyes must be at least eight pixels wide.')
    axis/=width;source_axis/=source_width
    normal=np.array([-axis[1],axis[0]],np.float32)
    source_normal=np.array([-source_axis[1],source_axis[0]],np.float32)
    if normal[1]<0: normal=-normal
    if source_normal[1]<0: source_normal=-source_normal
    current_height=(current-current[0])@normal/width
    source_height=(source-source[0])@source_normal/source_width
    targets=current+((source_height-current_height)*width)[:,None]*normal
    targets[[0,-1]]=current[[0,-1]]
    return targets,width,axis,normal


def apply_source_lids(rgb, points, source_points, hair, strength=.9):
    from flux2_klein9b_attractiveness import _UPPER_LIDS,_EYE_CONTOURS,_IRISES,_BROWS,_OVAL,_LIPS
    original=np.asarray(rgb,np.float32);points=np.asarray(points,np.float32)
    source_points=np.asarray(source_points,np.float32)
    if (original.ndim!=3 or original.shape[2]!=3 or points.shape!=(478,2)
        or source_points.shape!=(478,2) or np.asarray(hair).shape!=original.shape[:2]
        or not all(np.isfinite(a).all() for a in (original,points,source_points))
        or not np.isfinite(strength) or not 0<=strength<=1):
        raise ValueError('Expected finite RGB,478 source/current landmarks,matching hair and strength0..1.')
    h,w=original.shape[:2];zero=np.zeros((h,w),np.float32)
    if strength==0 or np.array_equal(points,source_points):
        return original.copy(),zero,{'status':'disabled','source_pixels_copied':False}
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    field=np.zeros((h,w,2),np.float32);guard=np.zeros((h,w),np.uint8)
    for ids in (*_BROWS,_LIPS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    cv2.circle(guard,tuple(np.rint(points[1]).astype(int)),12,255,-1)
    guard=cv2.dilate(guard,np.ones((5,5),np.uint8))
    face=np.zeros_like(guard)
    cv2.fillPoly(face,[np.rint(points[list(_OVAL)]).astype(np.int32)],255)
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))
    guard[(face==0)|(np.asarray(hair)>0)]=255
    eyes=[]
    for upper,contour,iris in zip(_UPPER_LIDS,_EYE_CONTOURS,_IRISES):
        desired,width,axis,normal=upper_lid_targets(points,source_points,upper)
        current=points[list(upper)]
        shifts=(desired-current)*strength
        lengths=np.linalg.norm(shifts,axis=1)
        shifts*=np.minimum(1.,width*.10/np.maximum(lengths,1e-8))[:,None]
        center=points[iris[0]]
        radius=float(np.linalg.norm(points[list(iris[1:])]-center,axis=1).mean())
        core_radius=max(1.,radius*.32)
        guard[(xx-center[0])**2+(yy-center[1])**2<=core_radius**2]=255
        theta=np.arange(24)*2*np.pi/24
        basis=np.stack((axis,normal),axis=1)
        boundary=center+np.column_stack((np.cos(theta)*width,np.sin(theta)*width*.62))@basis.T
        theta=np.arange(8)*2*np.pi/8
        core=center+np.column_stack((np.cos(theta),np.sin(theta)))*core_radius
        fixed=np.concatenate((points[list(contour[8:])],current[:1],center[None],core,boundary))
        moving=current[1:-1]+shifts[1:-1]
        controls=np.concatenate((fixed,moving))
        vectors=np.concatenate((np.zeros_like(fixed),shifts[1:-1]))
        kept=[]
        for index,p in enumerate(controls):
            if not kept or np.linalg.norm(controls[kept]-p,axis=1).min()>.25: kept.append(index)
        mapper=RBFInterpolator((controls[kept]-center)/width,vectors[kept]/width,
                              kernel='thin_plate_spline',smoothing=1e-6)
        x0=max(0,int(center[0]-width*1.2));x1=min(w,int(center[0]+width*1.2)+1)
        y0=max(0,int(center[1]-width*1.2));y1=min(h,int(center[1]+width*1.2)+1)
        coordinates=np.column_stack((xx[y0:y1,x0:x1].ravel(),yy[y0:y1,x0:x1].ravel()))
        local_field=(mapper((coordinates-center)/width)*width).reshape(y1-y0,x1-x0,2)
        uv=(coordinates-center)@basis
        distance=np.sqrt((uv[:,0]/width)**2+(uv[:,1]/(width*.62))**2).reshape(y1-y0,x1-x0)
        local_field*=np.clip((1-distance)/.18,0,1)[...,None]
        magnitude=np.linalg.norm(local_field,axis=2)
        local_field*=np.minimum(1.,width*.10/np.maximum(magnitude,1e-8))[...,None]
        field[y0:y1,x0:x1]+=local_field
        eyes.append({'upper_ids':list(upper),'width_pixels':width,
                     'before':current.tolist(),'source_target':desired.tolist(),
                     'requested_bounded_target':(current+shifts).tolist(),
                     'pupil_core_radius_pixels':core_radius})
    protection=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
    field*=np.clip(protection/2.,0,1)[...,None]
    active=np.linalg.norm(field,axis=2)>.001
    field[~active]=0
    dy_x,dx_x=np.gradient(field[:,:,0]);dy_y,dx_y=np.gradient(field[:,:,1])
    fraction=1.
    for _ in range(5):
        jacobian=(1-fraction*dx_x)*(1-fraction*dy_y)-fraction*fraction*dy_x*dx_y
        minimum=float(jacobian[active].min(initial=1.))
        maximum=float(jacobian[active].max(initial=1.))
        if minimum>=.25 and maximum<=3: break
        fraction*=.85
    if minimum<.25 or maximum>3 or fraction<.6:
        raise RuntimeError('Source lid request cannot retain a safe, useful deformation field.')
    field*=fraction
    output=cv2.remap(original,xx-field[:,:,0],yy-field[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    output=np.clip(output,0,1);output[~active]=original[~active]
    if not np.array_equal(output[guard>0],original[guard>0]):
        raise RuntimeError('Protected feature pixels changed.')
    # Solve q = p + displacement(q): report achieved map geometry, not just requests.
    for eye in eyes:
        before=np.array(eye['before'],np.float32);mapped=before.copy()
        for _ in range(30):
            sampled=cv2.remap(field,mapped[:,0][None],mapped[:,1][None],cv2.INTER_LINEAR)[0]
            next_mapped=before+sampled
            if np.linalg.norm(next_mapped-mapped,axis=1).max()<.001:
                mapped=next_mapped;break
            mapped=next_mapped
        target=np.array(eye['source_target'])
        eye['mapped_upper_lid_points']=mapped.tolist()
        eye['mean_source_target_error_before_pixels']=float(np.linalg.norm(before[1:-1]-target[1:-1],axis=1).mean())
        eye['mean_source_target_error_after_map_pixels']=float(np.linalg.norm(mapped[1:-1]-target[1:-1],axis=1).mean())
        eye['achieved_max_displacement_pixels']=float(np.linalg.norm(mapped-before,axis=1).max())
        eye['fixed_corner_max_displacement_pixels']=float(np.linalg.norm((mapped-before)[[0,-1]],axis=1).max())
    return output,active.astype(np.float32),{
        'status':'experimental_not_promoted','profile':'source_upper_lid_pupil_core_tps_v1',
        'strength':strength,'eyes':eyes,'safety_fraction':fraction,
        'minimum_inverse_jacobian':minimum,'maximum_inverse_jacobian':maximum,
        'maximum_field_pixels':float(np.linalg.norm(field,axis=2).max()),
        'pupil_core_brows_lips_nose_hair_outline_exact_before_gaze':True,
        'source_pixels_copied':False,'identity_conditioning':False,
        'limitation':'Existing iris-edge pixels can stretch; no missing iris content is reconstructed. Rendered appearance and redetected geometry require separate review.',
    }
