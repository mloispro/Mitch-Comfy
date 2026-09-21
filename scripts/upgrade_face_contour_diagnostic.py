"""Projected outline measurements, not an attractiveness or facial-volume score.

The ordered oval follows installed MediaPipe FACEMESH_FACE_OVAL. Measurements
remove in-plane translation, uniform scale and roll, but not yaw/pitch, lens
perspective, expression, landmark error or perceived fullness from shading.
"""
from __future__ import annotations

import math


FACE_OVAL = (10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,
             400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109)


def projected_contour(points) -> dict:
    if len(points) < 468 or any(len(p)!=2 or not all(math.isfinite(float(v)) for v in p) for p in points):
        raise ValueError('Expected finite two-dimensional MediaPipe landmarks.')
    points=[(float(p[0]),float(p[1])) for p in points]
    left,right=points[33],points[263]
    dx,dy=float(right[0]-left[0]),float(right[1]-left[1])
    scale=math.hypot(dx,dy)
    if scale <= 1e-8:
        raise ValueError('Degenerate outer-eye span.')
    origin=((left[0]+right[0])/2,(left[1]+right[1])/2)
    horizontal=(dx/scale,dy/scale)
    vertical=(-horizontal[1],horizontal[0])
    def project(point):
        delta=(point[0]-origin[0],point[1]-origin[1])
        return ((delta[0]*horizontal[0]+delta[1]*horizontal[1])/scale,
                (delta[0]*vertical[0]+delta[1]*vertical[1])/scale)
    if project(points[152])[1]<0:
        vertical=(-vertical[0],-vertical[1])
    chin=project(points[152])[1]
    if chin<=1e-8:
        raise ValueError('Degenerate eye-to-chin height.')
    polygon=[project(points[i]) for i in FACE_OVAL]
    widths={}
    for fraction in (.30,.50,.70):
        y=chin*fraction
        crossings=[]
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            if (p[1]<=y<q[1]) or (q[1]<=y<p[1]):
                crossings.append(p[0]+(y-p[1])*(q[0]-p[0])/(q[1]-p[1]))
        if len(crossings)!=2:
            raise ValueError('Expected a simple face outline at each measured height.')
        widths[f'{fraction:.2f}']=max(crossings)-min(crossings)
    return {'eye_to_chin_height_over_outer_eye_span':chin,
            'outline_width_over_outer_eye_span':widths,
            'measurement_levels':'Fractions of projected outer-eye-line to chin distance.',
            'limitation':'2D outline only: pose, eye spacing and detection changes affect ratios. Not cheek volume or beauty.'}


def relative_width_change(reference: dict, candidate: dict) -> dict:
    return {level:100*(candidate['outline_width_over_outer_eye_span'][level]/width-1)
            for level,width in reference['outline_width_over_outer_eye_span'].items()}
