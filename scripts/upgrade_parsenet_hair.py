"""Verified ParseNet label mapping for experiments; production v4 is unchanged.

ParseNet uses13=hair and17=neck. BiSeNet's17=hair mapping is incompatible.
Source: xinntao/facexlib/inference/inference_parsing_parsenet.py.
"""
import cv2
import numpy as np
import torch

PARSENET_HAIR_CLASS = 13


def select_hair(labels):
    hair = np.where(np.asarray(labels) == PARSENET_HAIR_CLASS, 255, 0).astype(np.uint8)
    # Keep v4's existing cleanup unchanged so the proposed repair isolates
    # the ParseNet class mapping rather than also changing mask morphology.
    hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, np.ones((5,5),np.uint8))
    count, components, stats, _ = cv2.connectedComponentsWithStats(hair)
    if count <= 1:
        raise ValueError('ParseNet did not detect class13 hair.')
    selected = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(components == selected, 255, 0).astype(np.uint8)


def parsed_labels(rgb, bbox):
    # Reuse the already installed, hash-verified CPU parser. No restoration.
    from flux2_klein9b_deterministic_polish import _hair_parser, _HAIR_PARSER_LOCK
    height, width = rgb.shape[:2]
    x0,y0,x1,y1 = np.asarray(bbox, np.float32)
    face_height = max(float(y1-y0),1.)
    side = min(max(64, round(face_height*1.46)), height, width)
    cx = float(x0+x1)*.5; cy = float(y0+y1)*.5-face_height*.08
    left = max(0,min(round(cx-side*.5),width-side))
    top = max(0,min(round(cy-side*.5),height-side))
    resized = cv2.resize(rgb[top:top+side,left:left+side,:3],(512,512),interpolation=cv2.INTER_AREA)
    tensor = torch.from_numpy(resized.transpose(2,0,1).copy()).float().div_(255)
    tensor = tensor.sub_(.5).div_(.5).unsqueeze(0)
    model = _hair_parser()
    with _HAIR_PARSER_LOCK, torch.inference_mode():
        crop = model(tensor)[0].argmax(dim=1).squeeze(0).numpy().astype(np.uint8)
    labels = np.zeros((height,width),np.uint8)
    labels[top:top+side,left:left+side] = cv2.resize(crop,(side,side),interpolation=cv2.INTER_NEAREST)
    return labels


def corrected_parsenet_hair_mask(rgb, bbox):
    return select_hair(parsed_labels(rgb,bbox))
