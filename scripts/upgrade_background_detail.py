"""Experimental background-only repair of a source-faithful native image.

Not a beauty model, identity adapter, compositing stage or production default.
"""
import cv2
import numpy as np

from upgrade_local_inpaint import build_graph as build_inpaint_graph

PROMPT = (
    'casual snapshot. Picture 1 is the photograph to preserve. Change only its '
    'background, recovering believable photographic detail in the existing scene. '
    'Keep the entire man, his face, eyes, closed-lip expression, hair, skin, clothing, '
    'body and silhouette exactly as in Picture 1. Picture 2 is a genuine identity '
    'reference for the same m1tch_person, not a replacement pose or expression. '
    'The background must look like a real environment captured by a recent phone '
    'main camera in standard Photo mode, with deep natural depth of field, not '
    'Portrait mode. Retain the exact camera viewpoint, perspective, lighting, '
    'colors, scene arrangement, object boundaries and existing architecture or '
    'landscape. Resolve existing surfaces and objects into physically plausible '
    'detail: where present, straight siding seams and matte painted grain, tapered '
    'tree branches with bark and irregular small twigs, layered rock strata, '
    'individual vegetation and coherent water detail. Do not add new objects. '
    'Match the existing subject light and fine sensor texture. Keep realistic '
    'distance-dependent softness but make the environment structurally readable, '
    'without artificial sharpening, oversharpened noise, cutout edges or halos. '
    'The finished photograph must read as one natural casual phone capture.'
)

SCENE_REFERENCE_PROMPT = PROMPT.replace(
    'Picture 1 is the photograph to preserve.',
    'Picture 1 is the photograph whose person must be preserved. Picture 3 shows '
    'the exact original background of this photograph and is the authoritative '
    'reference for its scene, architecture, object layout, material detail and '
    'colors. Reconstruct only the background visible in Picture 3 around the '
    'unchanged person from Picture 1. Do not copy or regenerate the man from '
    'Picture 3; it supplies background composition and materials only.', 1)


def background_mask(person):
    """Conservative person protection; feather only into background, never face."""
    if person.ndim != 2 or person.dtype != np.uint8:
        raise ValueError('Expected full-frame uint8 human-segmentation probability.')
    support = (person >= 26).astype(np.uint8)
    fraction = float(support.mean())
    if not .10 < fraction < .85:
        raise ValueError('Human segmentation coverage is implausible.')
    # This model is not hair-accurate; retain a margin and review the hair edge.
    distance = cv2.distanceTransform(1-support, cv2.DIST_L2, 5)
    margin = max(6, round(min(person.shape)*.012))
    feather = max(8, round(min(person.shape)*.020))
    t = np.clip((distance-margin)/feather, 0, 1)
    edit = np.rint(255*t*t*(3-2*t)).astype(np.uint8)
    if np.any(edit[support > 0]):
        raise ValueError('Background mask must protect every segmented person pixel.')
    return edit, {'person_threshold':26, 'person_fraction':fraction,
                  'protection_margin_px':margin, 'outward_feather_px':feather,
                  'nonzero_fraction':float(np.mean(edit>0)),
                  'white_fraction':float(np.mean(edit==255)),
                  'white_means':'edit background', 'black_means':'preserve source latent',
                  'segmentation_limit':'Human silhouette, not strand-accurate alpha matting.'}


def build_graph(loaders, source_name, identity_name, mask_name, size, seed, prefix,
                background_name=None):
    graph = build_inpaint_graph(loaders, source_name, identity_name, mask_name,
                               size, seed, prefix, source_geometry_name=background_name)
    graph['6']['inputs']['text'] = SCENE_REFERENCE_PROMPT if background_name else PROMPT
    if background_name:
        # Observation only: these leaves do not feed sampling or image output.
        graph['32']={'class_type':'SaveLatent','inputs':{'samples':['11',0],
                    'filename_prefix':prefix+'/source-latent'}}
        graph['33']={'class_type':'SaveLatent','inputs':{'samples':['25',0],
                    'filename_prefix':prefix+'/sampled-latent'}}
    return graph


def validate_graph(manifest):
    refs=manifest['references']
    roles=['source_faithful_synthetic_edit_target','genuine_identity','background_edit_mask_not_identity']
    mode='source_first_genuine_second'
    if len(refs)==4:
        roles.append('synthetic_original_scene_background_not_identity')
        mode='source_first_genuine_second_background_third'
    if ([r['role'] for r in refs] != roles
        or manifest['stage']!='klein_base9b_background_detail_pilot'
        or manifest['reference_mode']!=mode
        or manifest['postprocess'] is not False or manifest['turbo'] is not False
        or manifest['phone_camera_style'] is not True):
        raise ValueError('Wrong stage, reference semantics, or output settings.')
    expected=build_graph(manifest['prompt'], *(r['name'] for r in refs[:3]),
                         manifest['dimensions'], manifest['seed'], manifest['output_prefix'],
                         background_name=refs[3]['name'] if len(refs)==4 else None)
    if expected != manifest['prompt'] or manifest['effective_prompt'] != expected['6']['inputs']['text']:
        raise ValueError('Graph deviates from the reviewed minimal background experiment.')
