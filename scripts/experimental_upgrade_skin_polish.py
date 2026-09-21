"""Local, deterministic High skin experiment; not production or identity conditioning."""
from __future__ import annotations
import cv2
import numpy as np


def skin_regions(rgb,points,hair=None,warmth_feather=False):
    from flux2_klein9b_attractiveness import _OVAL,_EYE_CONTOURS,_BROWS,_LIPS
    image=np.asarray(rgb,np.float32);points=np.asarray(points,np.float32)
    if (image.ndim!=3 or image.shape[-1]!=3 or points.shape!=(478,2)
            or not np.isfinite(image).all() or not np.isfinite(points).all()
            or (hair is not None and np.asarray(hair).shape!=image.shape[:2])):
        raise ValueError('Expected finite RGB,478 landmarks and matching optional hair mask.')
    h,w=image.shape[:2]
    tangent=points[263]-points[33];span=float(np.linalg.norm(tangent))
    if span<2: raise ValueError('Degenerate face geometry.')
    tangent/=span;normal=np.array([-tangent[1],tangent[0]],np.float32)
    if np.dot(points[152]-points[1],normal)<0: normal=-normal
    basis=np.stack((tangent,normal),axis=1)
    oval=points[list(_OVAL)];local=oval@basis
    face_width=float(np.ptp(local[:,0]));scale=face_width/320
    face=np.zeros((h,w),np.uint8)
    cv2.fillPoly(face,[np.rint(oval).astype(np.int32)],255)
    radius=max(2,round(face_width*.02))
    face=cv2.erode(face,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,)*2))
    guard=np.zeros_like(face)
    for ids in (*_EYE_CONTOURS,*_BROWS,_LIPS):
        cv2.fillPoly(guard,[np.rint(points[list(ids)]).astype(np.int32)],255)
    kernel=3 if warmth_feather else max(3,round(face_width*.018))*2+1
    guard=cv2.dilate(guard,np.ones((kernel,)*2,np.uint8))
    if hair is not None: guard[np.asarray(hair)>0]=255
    ycrcb=cv2.cvtColor(np.rint(np.clip(image,0,1)*255).astype(np.uint8),cv2.COLOR_RGB2YCrCb)
    color=cv2.inRange(ycrcb,np.array([20,118,72],np.uint8),np.array([250,185,145],np.uint8))
    valid=(face>0)&(guard==0)&(color>0)
    distance=cv2.distanceTransform(valid.astype(np.uint8),cv2.DIST_L2,5)
    alpha=np.clip(distance/max(3.,face_width*.04),0,1)
    if warmth_feather:
        exterior=(face>0)&(color>0)
        if hair is not None: exterior&=np.asarray(hair)==0
        edge_distance=cv2.distanceTransform(exterior.astype(np.uint8),cv2.DIST_L2,5)
        feature_distance=cv2.distanceTransform((guard==0).astype(np.uint8),cv2.DIST_L2,5)
        alpha=np.clip(edge_distance/max(3.,face_width*.04),0,1)*np.clip(feature_distance/max(1.5,face_width*.006),0,1)
        alpha[~valid]=0
    alpha[alpha<.005]=0
    eye_origin=(points[33]+points[263])/2
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    v=(xx-eye_origin[0])*normal[0]+(yy-eye_origin[1])*normal[1]
    mouth_v=float(np.dot((points[13]+points[14])/2-eye_origin,normal))
    spot_valid=valid&(v<mouth_v*.72)
    # Keep nasal openings/shadows out of compact-spot selection.
    nose_guard=np.zeros_like(face)
    cv2.circle(nose_guard,tuple(np.rint(points[1]).astype(int)),max(4,round(face_width*.055)),255,-1)
    spot_valid[nose_guard>0]=False
    return alpha.astype(np.float32),spot_valid,{'face_width':face_width,'scale':scale,'anatomical_frame':True}


def polish_skin(rgb,points,source_rgb,source_points,hair,mode='warmth',spot_kind='dark_compact',warmth_mask='shared'):
    if mode not in ('warmth','spots','both'): raise ValueError('Unsupported skin experiment mode.')
    if spot_kind not in ('dark_compact','chromatic_compact') or warmth_mask not in ('shared','separate_feather'):
        raise ValueError('Unsupported isolated skin refinement.')
    original=np.asarray(rgb,np.float32)
    alpha,valid,geometry=skin_regions(original,points,hair)
    source_alpha,_,_=skin_regions(source_rgb,source_points)
    result=original.copy();selected=np.zeros(original.shape[:2],np.float32)
    report={'mode':mode,'source_pixels_copied':False,'geometry_changed':False,'production':False}
    if mode in ('spots','both'):
        scale=geometry['scale'];sigma=max(1.2,2.1*scale)
        lab=cv2.cvtColor(original,cv2.COLOR_RGB2LAB)
        light=lab[:,:,0]/100
        residual=np.maximum(cv2.GaussianBlur(light,(0,0),sigma)-light,0)
        candidate=(valid&(residual>.009)).astype(np.uint8)
        count,labels,stats,_=cv2.connectedComponentsWithStats(candidate,8)
        accepted=np.zeros_like(candidate);components=0
        chroma_residual=lab[:,:,1:]-cv2.GaussianBlur(lab[:,:,1:],(0,0),sigma)
        for index in range(1,count):
            area=int(stats[index,cv2.CC_STAT_AREA]);cw=int(stats[index,cv2.CC_STAT_WIDTH]);ch=int(stats[index,cv2.CC_STAT_HEIGHT])
            if (max(2,round(2*scale*scale))<=area<=max(12,round(80*scale*scale))
                    and max(cw,ch)<=max(5,round(14*scale)) and max(cw,ch)/max(1,min(cw,ch))<=3):
                component=labels==index
                if spot_kind=='chromatic_compact' and np.max(chroma_residual[component].mean(axis=0))<=.5:
                    continue
                accepted[component]=255;components+=1
        radius=max(1,round(scale))
        spot=cv2.dilate(accepted,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(radius*2+1,)*2))
        spot[~valid]=0
        coverage=float((spot>0).sum()/max(1,valid.sum()))
        if coverage>.18:
            core=accepted>0
            local_chroma=cv2.GaussianBlur(lab[:,:,1:],(0,0),sigma)
            difference=(lab[:,:,1:]-local_chroma)[core]
            report['spots']={'status':'rejected_broad_selection','selection_guard_passed':False,
                'spot_kind':spot_kind,'components':components,'selected_core_pixels':int(core.sum()),'region_coverage':coverage,
                'maximum_region_coverage':.18,'repair_applied':False,
                'core_Lab_chroma_residual_p10_p50_p90':np.percentile(difference,[10,50,90],axis=0).tolist()}
            report['spot_mask']=spot.astype(np.float32)/255
            return original.copy(),selected,report
        uint8=np.rint(np.clip(original,0,1)*255).astype(np.uint8)
        healed=cv2.inpaint(uint8,spot,max(2.,scale*3),cv2.INPAINT_TELEA).astype(np.float32)/255
        spot_alpha=cv2.GaussianBlur(spot.astype(np.float32)/255,(0,0),max(.5,scale*.55))
        spot_alpha[~valid]=0;spot_alpha[spot_alpha<.01]=0
        result=original+(healed-original)*spot_alpha[...,None]*.95
        selected=np.maximum(selected,(spot_alpha>0).astype(np.float32))
        after_luma=cv2.cvtColor(result,cv2.COLOR_RGB2LAB)[:,:,0]/100
        after_residual=np.maximum(cv2.GaussianBlur(after_luma,(0,0),sigma)-after_luma,0)
        core=accepted>0
        before_response=float(residual[core].mean()) if core.any() else 0.
        after_response=float(after_residual[core].mean()) if core.any() else 0.
        report['spots']={'status':'applied','selection_guard_passed':True,'repair_applied':True,
            'spot_kind':spot_kind,'components':components,'selected_core_pixels':int(core.sum()),'region_coverage':coverage,
            'response_before':before_response,'response_after':after_response,
            'response_reduction':1-after_response/max(before_response,1e-8) if core.any() else 0.,
            'replacement':'Telea interpolation inside selected compact spots, not whole-face blur',
            'stubble_lower_face_excluded':True,'unselected_pixels_exact':True,
            'limitation':'Healed spot interiors necessarily replace their texture. Compact pores may be selected; review mask and remaining skin.'}
        report['spot_mask']=spot_alpha
    if mode in ('warmth','both'):
        source_lab=cv2.cvtColor(np.asarray(source_rgb,np.float32),cv2.COLOR_RGB2LAB)
        target_lab=cv2.cvtColor(result,cv2.COLOR_RGB2LAB)
        if np.count_nonzero(source_alpha>.6)<100 or np.count_nonzero(alpha>.6)<100:
            raise ValueError('Insufficient skin for a stable color comparison.')
        source_chroma=np.median(source_lab[source_alpha>.6,1:],axis=0)
        target_chroma=np.median(target_lab[alpha>.6,1:],axis=0)
        shift=np.minimum(np.maximum((source_chroma-target_chroma)*.35,0),[3.,5.]).astype(np.float32)
        warm_alpha=skin_regions(original,points,hair,True)[0] if warmth_mask=='separate_feather' else alpha
        changed=target_lab.copy();changed[:,:,1:]+=warm_alpha[...,None]*shift
        warmed=cv2.cvtColor(changed,cv2.COLOR_LAB2RGB)
        warmed[warm_alpha==0]=result[warm_alpha==0]
        result=warmed
        if np.any(shift): selected=np.maximum(selected,(warm_alpha>0).astype(np.float32))
        report['warmth']={'source_median_Lab_ab':source_chroma.tolist(),'before_median_Lab_ab':target_chroma.tolist(),
            'maximum_applied_Lab_ab_shift':shift.tolist(),'lightness_channel_changed':False,
            'source_difference_fraction':.35,'positive_shift_limits':[3.,5.],'warmth_mask':warmth_mask,
            'limitation':'Bounded face-local chroma adjustment, not a lighting estimate or full-body tan. Inspect face/neck transition.'}
    result=np.clip(result,0,1);result[selected==0]=original[selected==0]
    report['geometry']=geometry
    return result.astype(np.float32),selected,report
