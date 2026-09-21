"""Source-shaped upper-lid experiment for the isolated CPU replay only.

The old full-iris guard blocks normal upper-lid occlusion; protect the pupil core
instead, keep the eye corners fixed and confine motion to the upper-lid strip.
The caller must re-evaluate/re-lock source-relative gaze after changing eyelids.
No new eye, source pixels or identity signal is synthesized by this warp.
"""
from __future__ import annotations

import cv2
import numpy as np


def source_shaped_upper_lid(rgb, points, source_points, unused_old_iris_guard):
    from flux2_klein9b_attractiveness import _UPPER_LIDS, _EYE_CONTOURS, _IRISES
    h,w=rgb.shape[:2]
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    dx_field=np.zeros((h,w),np.float32)
    dy_field=np.zeros((h,w),np.float32)
    weight_sum=np.zeros((h,w),np.float32)
    pupil_guard=np.zeros((h,w),np.float32)
    corner_guard=np.zeros((h,w),np.float32)
    reports=[]
    for ids,contour,iris_ids in zip(_UPPER_LIDS,_EYE_CONTOURS,_IRISES):
        p0,p1=points[ids[0]],points[ids[-1]]
        s0,s1=source_points[ids[0]],source_points[ids[-1]]
        axis=p1-p0; source_axis=s1-s0
        width=max(float(np.linalg.norm(axis)),1.)
        source_width=max(float(np.linalg.norm(source_axis)),1.)
        unit=axis/width; source_unit=source_axis/source_width
        normal=np.array([-unit[1],unit[0]],np.float32)
        source_normal=np.array([-source_unit[1],source_unit[0]],np.float32)
        if np.dot(points[list(contour[9:])].mean(axis=0)-(p0+p1)/2,normal)<0: normal*=-1
        if np.dot(source_points[list(contour[9:])].mean(axis=0)-(s0+s1)/2,source_normal)<0: source_normal*=-1
        shifts=[]
        for index in ids[1:-1]:
            target_v=float(np.dot(source_points[index]-s0,source_normal)/source_width)
            current_v=float(np.dot(points[index]-p0,normal)/width)
            requested=(target_v-current_v)*width
            shift=float(np.clip(requested,-.075*width,.075*width))
            center=points[index]+normal*shift*.5
            dx,dy=xx-center[0],yy-center[1]
            u=dx*unit[0]+dy*unit[1]; v=dx*normal[0]+dy*normal[1]
            weight=np.exp(-.5*((u/max(1,width*.115))**2+(v/max(1,width*.07))**2))
            weight[weight<.012]=0
            dx_field+=normal[0]*shift*weight
            dy_field+=normal[1]*shift*weight
            weight_sum+=weight
            shifts.append({'landmark':index,'requested':round(requested,4),'bounded':round(shift,4)})
        center=points[iris_ids[0]]
        ring=points[list(iris_ids[1:])]
        rx,ry=np.maximum(np.ptp(ring,axis=0)/2,1.)
        radius=np.sqrt(((xx-center[0])/rx)**2+((yy-center[1])/ry)**2)
        pupil_guard=np.maximum(pupil_guard,np.clip((.55-radius)/.2,0,1))
        for corner in (p0,p1):
            distance=np.hypot(xx-corner[0],yy-corner[1])/max(width*.06,1)
            corner_guard=np.maximum(corner_guard,np.clip(2-distance,0,1))
        reports.append({'maximum_shift_eye_width_fraction':.075,'shifts':shifts,
                        'normal_lid_occlusion_of_outer_iris_allowed':True,
                        'pupil_core_and_eye_corners_protected':True})
    divisor=np.maximum(weight_sum,1)
    gate=(1-pupil_guard)*(1-corner_guard)
    dx_field=dx_field/divisor*gate; dy_field=dy_field/divisor*gate
    active=(np.hypot(dx_field,dy_field)>.001).astype(np.float32)
    warped=cv2.remap(rgb.astype(np.float32),xx-dx_field,yy-dy_field,
                     cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    warped[active==0]=rgb[active==0]
    return np.clip(warped,0,1),active,reports
