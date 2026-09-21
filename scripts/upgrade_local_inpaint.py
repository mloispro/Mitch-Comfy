"""Experimental Base9B masked sampling; not a production High implementation."""
import copy

import cv2
import numpy as np


PROMPT = (
    'casual snapshot. Retouch only the man in Picture 1 into a visibly more handsome '
    'best-day version of m1tch_person. Picture 2 is a genuine identity reference for '
    'the same man, not a pose or expression to copy. Keep Picture 1\'s head direction, '
    'eye focus, forehead height, hairline, facial proportions and recognizable identity. '
    'Give him relaxed flattering eyes with clearly defined upper lids, well-groomed '
    'eyebrows, rested under-eyes, naturally lean cheeks and a defined jaw transition. '
    'His expression is warm and quietly confident: lips touching in a small asymmetric '
    'closed-lip smile with all teeth covered. His brow is relaxed and smooth. His skin '
    'is clear, even and lightly tanned, with greatly reduced wrinkles, no freckles or '
    'dark speckles, subtle natural pores and tidy fine stubble. Preserve the hairstyle '
    'but make its strands and small flyaways irregular and natural, with subtle highlights. '
    'Match the existing daylight and skin color on his neck and body. Keep the entire '
    'environment, clothing and framing unchanged. One realistic main-camera phone photo, '
    'with natural fine texture and consistent photographic detail throughout.'
)

# Only role-specific clauses differ: the unmodified original is a geometry and
# expression reference, never relabeled as a genuine identity photograph.
SOURCE_GEOMETRY_PROMPT = PROMPT.replace(
    "Keep Picture 1's head direction, eye focus, forehead height, hairline, facial proportions and recognizable identity.",
    "Picture 3 is the original scene: use its head direction, pupil focus, eye shape, "
    "forehead height, hairline and lean facial proportions, while keeping the same man's recognizable identity."
).replace(
    "His expression is warm and quietly confident: lips touching in a small asymmetric closed-lip smile with all teeth covered.",
    "Use Picture 3's understated, quietly confident expression and asymmetric closed-lip seam: "
    "lips touching in a small smile with all teeth covered, without inflating his cheeks."
)


def build_mask(face_hull, hair, face_width):
    """Head support with a small context margin and compact inward feather."""
    if face_hull.shape != hair.shape or face_hull.ndim != 2:
        raise ValueError('Face and hair masks must share full-frame geometry.')
    support = np.maximum(face_hull > 0, hair > 0).astype(np.uint8)
    yy, xx = np.nonzero(support)
    if len(xx) < 3:
        raise ValueError('No usable head support.')
    # FaceMesh ends below the hairline. A joint outer envelope includes the
    # otherwise unmasked forehead strip instead of creating an internal seam.
    cv2.fillConvexPoly(support, cv2.convexHull(np.column_stack((xx,yy)).astype(np.int32)), 1)
    radius = max(2, round(face_width * .035))
    support = cv2.dilate(support, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*radius+1,)*2))
    feather = max(4, round(face_width * .065))
    distance = cv2.distanceTransform(support, cv2.DIST_L2, 5)
    t = np.clip(distance / feather, 0, 1)
    mask = np.rint(255 * t*t*(3-2*t)).astype(np.uint8)
    fraction = float(np.mean(mask > 0))
    if not .03 < fraction < .35:
        raise ValueError('Unexpectedly small or broad head edit region.')
    return mask, {'context_margin_px': radius, 'inward_feather_px': feather,
                  'nonzero_fraction': fraction, 'white_fraction': float(np.mean(mask == 255)),
                  'forehead_gap': 'filled by joint face/hair outer envelope',
                  'white_means': 'denoise/edit', 'black_means': 'preserve source latent'}


def build_graph(loaders, source_name, identity_name, mask_name, size, seed, prefix,
                source_geometry_name=None):
    if (not prefix.startswith('upgrade-source-faithful/') or '..' in prefix
            or ':' in prefix or any(v % 16 for v in size)):
        raise ValueError('Unsafe destination or incompatible geometry.')
    graph = {str(i): copy.deepcopy(loaders[str(i)]) for i in range(1, 6)}
    if (graph['1']['inputs']['weight_dtype'] != 'default'
            or graph['2']['inputs']['strength_model'] != .9
            or graph['3']['inputs']['strength_model'] != .25):
        raise ValueError('Expected frozen BF16 Base9B / identity .9 / phone .25 loaders.')
    def node(key, kind, **inputs):
        graph[str(key)] = {'class_type': kind, 'inputs': inputs}
    node(6, 'CLIPTextEncode', clip=['4', 0],
         text=SOURCE_GEOMETRY_PROMPT if source_geometry_name else PROMPT)
    node(7, 'CLIPTextEncode', clip=['4', 0], text='')
    node(10, 'LoadImage', image=source_name)
    node(11, 'VAEEncode', pixels=['10', 0], vae=['5', 0])
    node(12, 'ReferenceLatent', conditioning=['6', 0], latent=['11', 0])
    node(13, 'ReferenceLatent', conditioning=['7', 0], latent=['11', 0])
    node(14, 'LoadImage', image=identity_name)
    node(15, 'ImageScaleToTotalPixels', image=['14', 0], megapixels=1.0,
         resolution_steps=16, upscale_method='bicubic')
    node(16, 'VAEEncode', pixels=['15', 0], vae=['5', 0])
    node(17, 'ReferenceLatent', conditioning=['12', 0], latent=['16', 0])
    node(18, 'ReferenceLatent', conditioning=['13', 0], latent=['16', 0])
    node(19, 'LoadImage', image=mask_name)
    node(20, 'RandomNoise', noise_seed=seed)
    node(21, 'CFGGuider', model=['3', 0], positive=['17', 0], negative=['18', 0], cfg=4.0)
    node(22, 'KSamplerSelect', sampler_name='euler')
    node(23, 'Flux2Scheduler', steps=50, width=size[0], height=size[1])
    node(24, 'ImageToMask', image=['19', 0], channel='red')
    node(28, 'SetLatentNoiseMask', samples=['11', 0], mask=['24', 0])
    node(25, 'SamplerCustomAdvanced', noise=['20', 0], guider=['21', 0],
         sampler=['22', 0], sigmas=['23', 0], latent_image=['28', 0])
    node(26, 'VAEDecode', samples=['25', 0], vae=['5', 0])
    node(27, 'SaveImage', images=['26', 0], filename_prefix=prefix+'/raw')
    # Same graph's source-codec control distinguishes VAE loss from mask leakage.
    node(30, 'VAEDecode', samples=['11', 0], vae=['5', 0])
    node(31, 'SaveImage', images=['30', 0], filename_prefix=prefix+'/codec-control')
    if source_geometry_name:
        node(40, 'LoadImage', image=source_geometry_name)
        node(41, 'ImageScaleToTotalPixels', image=['40', 0], megapixels=1.0,
             resolution_steps=16, upscale_method='bicubic')
        node(42, 'VAEEncode', pixels=['41', 0], vae=['5', 0])
        node(43, 'ReferenceLatent', conditioning=['17', 0], latent=['42', 0])
        node(44, 'ReferenceLatent', conditioning=['18', 0], latent=['42', 0])
        graph['21']['inputs'].update(positive=['43', 0], negative=['44', 0])
    return graph


def validate_graph(manifest):
    graph = manifest['prompt']
    refs = manifest['references']
    if (len(refs) not in (3, 4)
            or refs[0]['role'] != 'synthetic_phone_on_edit_source_not_identity'
            or refs[1]['role'] != 'genuine_identity' or refs[2]['role'] != 'edit_mask_not_identity'):
        raise ValueError('Expected source, genuine identity, and non-conditioning mask.')
    geometry = None
    mode = 'source_first_genuine_second'
    if len(refs) == 4:
        if refs[3]['role'] != 'original_source_geometry_expression_not_identity':
            raise ValueError('Third conditioning image is original geometry, not an identity anchor.')
        geometry = refs[3]['name']
        mode = 'raw_first_genuine_second_original_geometry_third'
    if manifest['reference_mode'] != mode:
        raise ValueError('Declared reference order differs from the actual layout.')
    expected = build_graph(graph, refs[0]['name'], refs[1]['name'], refs[2]['name'],
                           manifest['dimensions'], manifest['seed'], manifest['output_prefix'], geometry)
    if graph != expected or manifest['phone_camera_style'] is not True or manifest['turbo'] is not False:
        raise ValueError('Graph deviates from the frozen minimal masked experiment.')
    if manifest['postprocess'] is not False or manifest['identity_reference_count'] != 1:
        raise ValueError('Unexpected polish or identity layout.')
    if manifest['effective_prompt'] != expected['6']['inputs']['text']:
        raise ValueError('Prompt metadata differs from actual conditioning.')
