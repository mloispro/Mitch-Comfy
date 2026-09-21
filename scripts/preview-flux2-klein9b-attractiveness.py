"""Compare cosmetic levels from ONE saved raw render; no diffusion or uploads."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from PIL import Image, ImageDraw, ImageFont, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smile-strength", type=float, default=0.0,
                        help="Experimental postprocess only; production High does not use it.")
    parser.add_argument("--baseline-low", type=Path)
    parser.add_argument("--baseline-high", type=Path)
    parser.add_argument("--native-high-manifest", type=Path,
                        help="Evaluate a verified native High render using only common safe polish.")
    parser.add_argument("--raw-manifest", type=Path,
                        help="Verify an ordinary native raw generation independently of this CPU replay.")
    parser.add_argument("--restful-retouch", type=float, default=0.0,
                        help="Isolated stronger crease-band retouch; not production.")
    parser.add_argument("--crease-repair", type=float, default=0.0,
                        help="Isolated selective forehead-ridge repair, not production.")
    parser.add_argument("--source-expression", type=float, default=0.0,
                        help="Isolated eye-contour/corner and closed-smile geometry, not production.")
    parser.add_argument("--final-source-gaze", action="store_true",
                        help="Validate existing source-gaze correction after experimental expression geometry.")
    parser.add_argument("--eye-expression", action="store_true",
                        help="Isolated source-shaped upper-lid experiment with final source gaze correction.")
    parser.add_argument("--no-forced-smile", action="store_true",
                        help="Isolated CPU experiment: disable the legacy unconditional corner lift.")
    parser.add_argument("--no-cheek-lift", action="store_true",
                        help="Isolated CPU experiment: disable the legacy cosmetic cheek brightening.")
    parser.add_argument("--exclude-reference", type=Path, action="append", default=[],
                        help="Exclude a source/conditioning photo from genuine-reference scoring.")
    parser.add_argument("--comfy-root", type=Path, default=Path(r"C:\projects\AI-Tools\ComfyUI"))
    args = parser.parse_args()
    if args.crease_repair and (args.restful_retouch or args.eye_expression or args.smile_strength or args.native_high_manifest):
        raise ValueError('Evaluate selective crease repair independently of other experimental treatments.')
    if args.source_expression and (args.crease_repair or args.restful_retouch or args.eye_expression or args.smile_strength or args.native_high_manifest):
        raise ValueError('Evaluate source-expression geometry independently of other experimental treatments.')
    if args.final_source_gaze and not args.source_expression:
        raise ValueError('This ordering test requires source-expression geometry.')
    if args.raw_manifest and args.native_high_manifest:
        raise ValueError('Choose ordinary raw provenance or native-High provenance, not both.')
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(args.comfy_root))
    sys.path.insert(0, str(root / "custom_nodes/ComfyUI-AIToolkit-Training"))
    from flux2_klein9b_attractiveness import apply_high_attractiveness
    if args.eye_expression:
        if args.native_high_manifest or args.restful_retouch or args.smile_strength:
            raise ValueError("Test eye-expression conditioning separately from other new treatments.")
        import flux2_klein9b_attractiveness as high_module
        from experimental_upgrade_eye_expression import source_shaped_upper_lid
        high_module._source_guided_upper_lid_warp = source_shaped_upper_lid
    from experimental_upgrade_smile_balance import apply_smile_balance, measure_smile
    from flux2_klein9b_deterministic_polish import apply_deterministic_face_polish, build_semantic_hair_mask
    import flux2_klein9b_deterministic_polish as legacy_polish
    # This script is a separate CPU process, never imported by the live worker.
    # Record isolated diagnostic overrides; production defaults remain unchanged.
    if args.no_forced_smile:
        legacy_polish.MOUTH_CORNER_LIFT_FACE_HEIGHT = 0.0
    if args.no_cheek_lift:
        legacy_polish.CHEEK_HIGHLIGHT_GAIN = 0.0
    from flux2_klein9b_source_gaze_lock import (
        _EYES as GAZE_EYES,
        _coordinate_in_fixed_eye_geometry,
        _detect_refined_landmarks,
        _eye_measurement,
        apply_source_gaze_lock,
    )

    def read(path):
        with Image.open(path) as image:
            return np.array(ImageOps.exif_transpose(image).convert("RGB"))

    def tensor(rgb):
        return torch.from_numpy(rgb.astype(np.float32) / 255).unsqueeze(0)

    def uint8(photo):
        return np.round(np.clip(photo[0].numpy(), 0, 1) * 255).astype(np.uint8)

    analyzer = FaceAnalysis(name="antelopev2", root=str(Path.home() / ".insightface"),
                            providers=["CPUExecutionProvider"],
                            allowed_modules=["detection", "recognition", "landmark_3d_68"])
    analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    recognizer = analyzer.models["recognition"]

    def fixed_alignment_embedding(rgb, keypoints):
        aligned = face_align.norm_crop(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                                      landmark=keypoints, image_size=recognizer.input_size[0])
        embedding = recognizer.get_feat(aligned).flatten()
        return embedding / np.linalg.norm(embedding)

    def face(rgb):
        faces = analyzer.get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if len(faces) != 1:
            raise RuntimeError(f"Expected one face, found {len(faces)}")
        return faces[0]

    source_rgb, raw_rgb = read(args.source), read(args.raw)
    if args.native_high_manifest and args.restful_retouch:
        raise ValueError("Do not combine native-generation and stronger-retouch experiments.")
    generation_manifest_path=args.raw_manifest or args.native_high_manifest
    if generation_manifest_path:
        manifest = json.loads(generation_manifest_path.read_text(encoding="utf-8-sig"))
        with Image.open(args.raw) as saved_raw:
            embedded_prompt = json.loads(saved_raw.info.get("prompt", "null"))
        # ComfyUI annotates executed LoadImage nodes with its input-content hash.
        # Validate that hash against recorded references before comparing graphs.
        reference_hashes = {ref["name"]: ref["sha256"].lower() for ref in manifest["references"]}
        for node in (embedded_prompt or {}).values():
            if node.get("class_type") == "LoadImage" and "is_changed" in node:
                expected = reference_hashes.get(node["inputs"]["image"])
                if not expected or node["is_changed"] != [expected]:
                    raise RuntimeError("Executed image cache hash does not match the recorded reference.")
                del node["is_changed"]
        if embedded_prompt != manifest.get('prompt'):
            raise RuntimeError('Executed PNG graph does not match the generation manifest.')
        if manifest.get('turbo') or not manifest.get('phone_camera_style'):
            raise RuntimeError('Expected phone-on, Turbo-off raw generation for this validation.')
        if args.native_high_manifest:
            from experimental_upgrade_high_prompt import HIGH_IDENTITY_ROLE
            if HIGH_IDENTITY_ROLE not in manifest.get('effective_prompt',''):
                raise RuntimeError('Native High requires the experimental High identity-role prompt.')
        if args.smile_strength and args.native_high_manifest:
            raise ValueError("Do not mix native High validation with another experimental mouth warp.")
    validation_errors = []
    source, raw = tensor(source_rgb), tensor(raw_rgb)
    detected = face(raw_rgb)
    source_face = face(source_rgb)
    hair = build_semantic_hair_mask(raw_rgb, detected.bbox)
    low, low_mask, low_report = apply_deterministic_face_polish(raw, detected.bbox, detected.kps, hair)
    low, low_gaze_mask, low_gaze = apply_source_gaze_lock(source, low)
    landmarks, _ = _detect_refined_landmarks(uint8(low))
    source_landmarks, _ = _detect_refined_landmarks(source_rgb)
    previous_high, previous_mask, high_report = apply_high_attractiveness(
        low, landmarks, hair, source_landmarks)
    if args.native_high_manifest:
        high, high_mask = low.clone(), torch.zeros_like(low)
        high_report = {"profile": "experimental_native_high_plus_common_polish",
                       "generation_manifest": str(args.native_high_manifest),
                       "executed_prompt_verified_from_png": True,
                       "extra_high_eye_warp": False,
                       "smile_balance": {"status": "not_selected"}}
    elif args.smile_strength:
        balanced, smile_mask, smile_report = apply_smile_balance(
            previous_high[0].numpy(),landmarks,source_landmarks,hair,args.smile_strength)
        high = torch.from_numpy(balanced).unsqueeze(0)
        high_mask = torch.maximum(previous_mask,torch.from_numpy(
            np.repeat(smile_mask[...,None],3,axis=2)).unsqueeze(0))
        high_report["smile_balance"] = smile_report
        high_report["production_smile_balance"] = False
    else:
        high,high_mask = previous_high,previous_mask
        high_report["smile_balance"] = {"status":"not_selected"}
    if args.restful_retouch:
        from experimental_upgrade_restful_retouch import apply_restful_retouch
        retouched, retouch_mask, retouch_report = apply_restful_retouch(
            high[0].numpy(),landmarks,hair,args.restful_retouch)
        high = torch.from_numpy(retouched).unsqueeze(0)
        high_mask = torch.maximum(high_mask,torch.from_numpy(
            np.repeat(retouch_mask[...,None],3,axis=2)).unsqueeze(0))
        high_report["restful_retouch"] = retouch_report
    if args.crease_repair:
        from experimental_upgrade_crease_repair import apply_crease_repair
        repaired,repair_mask,repair_report=apply_crease_repair(
            high[0].numpy(),landmarks,hair,args.crease_repair)
        high=torch.from_numpy(repaired).unsqueeze(0)
        high_mask=torch.maximum(high_mask,torch.from_numpy(
            np.repeat(repair_mask[...,None],3,axis=2)).unsqueeze(0))
        high_report['crease_repair']=repair_report
    if args.source_expression:
        from experimental_upgrade_source_expression import apply_source_expression
        previous_landmarks,_=_detect_refined_landmarks(uint8(high))
        deformed,expression_mask,expression_report=apply_source_expression(
            high[0].numpy(),previous_landmarks,source_landmarks,hair,args.source_expression)
        high=torch.from_numpy(deformed).unsqueeze(0)
        high_mask=torch.maximum(high_mask,torch.from_numpy(
            np.repeat(expression_mask[...,None],3,axis=2)).unsqueeze(0))
        high_report['source_expression_geometry']=expression_report
        high_report['profile']='experimental_source_contour_and_smile_geometry_plus_high_tones'
        high_report['geometric_warp_scope']='source-relative eye contours/corners and mouth contours; see source_expression_geometry'
        high_report['pupil_core_lip_pixels_exact']=False
        high_report['iris_geometry_changed']=False
        if args.final_source_gaze:
            high,final_source_gaze_mask,final_source_gaze_report=apply_source_gaze_lock(source,high)
            high_mask=torch.maximum(high_mask,final_source_gaze_mask)
            high_report['final_source_gaze']=final_source_gaze_report
            high_report['iris_geometry_changed']='source-fidelity iris correction after expression; eyelid shape unchanged by final correction'
    if args.eye_expression:
        high, final_gaze_mask, final_gaze_report = apply_source_gaze_lock(source, high)
        high_mask = torch.maximum(high_mask,final_gaze_mask)
        high_report["profile"] = "experimental_source_shaped_upper_lid_final_gaze"
        high_report["source_gaze_after_eye_shape"] = final_gaze_report
        high_report["pupil_core_lip_pixels_exact"] = False
        high_report["iris_geometry_changed"] = "upper-lid occlusion and final source-relative gaze correction"
    high_points, _ = _detect_refined_landmarks(uint8(high))
    previous_points, _ = _detect_refined_landmarks(uint8(previous_high))
    source_smile = measure_smile(source_landmarks)
    previous_smile = measure_smile(previous_points)
    after_smile = measure_smile(high_points)
    from upgrade_expression_acceptance import closed_lip_check
    raw_points, _ = _detect_refined_landmarks(raw_rgb)
    raw_closed_lips = closed_lip_check(source_smile['opening_ratio'], measure_smile(raw_points)['opening_ratio'])
    high_closed_lips = closed_lip_check(source_smile['opening_ratio'], after_smile['opening_ratio'])
    if not high_closed_lips['passed']:
        validation_errors.append('Final High fails the requested closed-lip limit, independently of the generated baseline.')
    before_expression_error = float(np.linalg.norm(source_smile["corner_coordinates"]-previous_smile["corner_coordinates"],axis=1).mean())
    after_expression_error = float(np.linalg.norm(source_smile["corner_coordinates"]-after_smile["corner_coordinates"],axis=1).mean())
    # Inspect unchanged eye/brow/nose pixels, not only noisy redetected landmarks.
    from flux2_klein9b_attractiveness import _EYE_CONTOURS, _BROWS
    expression_guard = np.zeros(raw_rgb.shape[:2],np.uint8)
    for ids in (*_EYE_CONTOURS,*_BROWS):
        cv2.fillPoly(expression_guard,[np.round(landmarks[list(ids)]).astype(np.int32)],255)
    cv2.circle(expression_guard,tuple(np.round(landmarks[1]).astype(int)),12,255,-1)
    expression_guard = cv2.dilate(expression_guard,np.ones((13,13),np.uint8))
    guarded_error = int(np.abs(uint8(high).astype(np.int16)-uint8(previous_high).astype(np.int16))[expression_guard>0].max(initial=0))
    expression_validation = {
        "source_corner_coordinates": source_smile["corner_coordinates"].round(6).tolist(),
        "previous_high_corner_coordinates": previous_smile["corner_coordinates"].round(6).tolist(),
        "new_high_corner_coordinates": after_smile["corner_coordinates"].round(6).tolist(),
        "mean_source_corner_error_before": round(before_expression_error,6),
        "mean_source_corner_error_after": round(after_expression_error,6),
        "expression_error_reduction_fraction": round(1-after_expression_error/max(before_expression_error,1e-8),6),
        "opening_ratio_before": round(previous_smile["opening_ratio"],6),
        "opening_ratio_after": round(after_smile["opening_ratio"],6),
        "raw_closed_lip_check": raw_closed_lips,
        "final_closed_lip_check": high_closed_lips,
        "eye_brow_nose_pixel_max_error_from_previous_high": guarded_error,
    }
    if guarded_error != 0 and not args.native_high_manifest and not args.source_expression:
        validation_errors.append("Smile balance altered protected eye/brow/nose pixels.")
    if high_report["smile_balance"]["status"] == "applied":
        if after_expression_error >= before_expression_error:
            validation_errors.append("Smile balance did not improve measured source-expression fidelity.")
        if after_smile["opening_ratio"] > max(previous_smile["opening_ratio"]+0.01,0.035):
            validation_errors.append("Smile balance increased detected mouth opening beyond acceptance limit.")
    if args.source_expression and after_smile['opening_ratio']>max(previous_smile['opening_ratio']+.01,.035):
        validation_errors.append('Source-expression geometry increased mouth opening beyond acceptance limit.')
    high_gaze_checks = []
    for definition in GAZE_EYES:
        fixed_eye = _eye_measurement(landmarks, definition)
        after_eye = _eye_measurement(high_points, definition)
        previous_eye = _eye_measurement(previous_points, definition)
        after_coordinate = _coordinate_in_fixed_eye_geometry(
            after_eye["iris_center"], fixed_eye)
        delta = after_coordinate - fixed_eye["coordinate"]
        previous_delta = _coordinate_in_fixed_eye_geometry(
            previous_eye["iris_center"],fixed_eye)-fixed_eye["coordinate"]
        high_gaze_checks.append({
            "name": definition["name"],
            "normalized_horizontal_delta_from_low": round(float(delta[0]), 6),
            "normalized_vertical_delta_from_low": round(float(delta[1]), 6),
            "previous_high_horizontal_delta_from_low": round(float(previous_delta[0]),6),
            "previous_high_vertical_delta_from_low": round(float(previous_delta[1]),6),
        })
    high_gaze_mask = low_gaze_mask
    maximum_gaze_delta = max(
        abs(value) for item in high_gaze_checks
        for key, value in item.items() if key.startswith("normalized_"))
    previous_gaze_delta = max(abs(value) for item in high_gaze_checks
                             for key,value in item.items() if key.startswith("previous_high_"))
    # Independent pixel evidence supplements the noisy whole-face redetection.
    # This does not waive any existing gate or prove the appearance is desirable.
    yy, xx = np.mgrid[:raw_rgb.shape[0], :raw_rgb.shape[1]]
    pupil_core = np.zeros(raw_rgb.shape[:2], bool)
    for iris_ids in ((468,469,470,471,472),(473,474,475,476,477)):
        center = landmarks[iris_ids[0]]
        ring = landmarks[list(iris_ids[1:])]
        rx = max(float(np.ptp(ring[:,0]))/2, 1.0)
        ry = max(float(np.ptp(ring[:,1]))/2, 1.0)
        pupil_core |= ((xx-center[0])/rx)**2 + ((yy-center[1])/ry)**2 <= 0.30**2
    pupil_core_error = int(np.abs(uint8(high).astype(np.int16)-uint8(low).astype(np.int16))[pupil_core].max(initial=0))
    acceptance_gaze_delta = maximum_gaze_delta if args.native_high_manifest else previous_gaze_delta
    if args.final_source_gaze:
        # Eye geometry intentionally differs from Low. Check source fidelity in
        # the final unchanged eyelid frame, not a noisy return to old Low shape.
        acceptance_gaze_delta=max(item['horizontal_error_after'] for item in final_source_gaze_report['eye_reports'])
    if acceptance_gaze_delta > 0.02:
        validation_errors.append(
            f"Selected High gaze acceptance error {acceptance_gaze_delta:.6f}; limit is 0.02.")
    high_gaze = {**low_gaze, "inherited_from_low_before_high": True,
                 "post_high_landmark_check": high_gaze_checks,
                 "maximum_absolute_normalized_delta": round(maximum_gaze_delta, 6),
                 "previous_high_maximum_absolute_normalized_delta": round(previous_gaze_delta,6),
                 "pupil_core_pixel_max_error_from_low": pupil_core_error,
                 "pupil_core_checked_pixels": int(pupil_core.sum()),
                 "previous_high_acceptance_limit": 0.02,
                 "post_expression_landmark_only_check": "diagnostic; expression can change redetection despite identical eye pixels",
                 "expression_gaze_acceptance": "eye/brow/nose pixels identical to accepted pre-expression High",
                 "acceptance_passed": acceptance_gaze_delta<=0.02 and (guarded_error==0 or bool(args.native_high_manifest)),
                 "native_high_no_extra_eye_edit": bool(args.native_high_manifest)}
    if args.native_high_manifest:
        high_gaze["expression_gaze_acceptance"] = "Native High output is byte-identical to common polish; no extra eye operation. Source-to-raw gaze is still measured separately."
    if args.source_expression:
        high_gaze['expression_gaze_acceptance']='Eye contours move; source-expression stage reports exact iris/pupil pixels. Existing High redetection gate is retained and is not waived.'
        high_gaze['post_expression_landmark_only_check']='Eye geometry and facial expression changed; inspect source-relative focus as well as exact pupil-pixel evidence.'
    if args.final_source_gaze:
        high_gaze['final_source_gaze']=final_source_gaze_report
        high_gaze['acceptance_reference']='source horizontal iris coordinate in final pixel-identical eyelid geometry'
        high_gaze['acceptance_max_horizontal_error']=acceptance_gaze_delta
        high_gaze['acceptance_passed']=acceptance_gaze_delta<=.02 and final_source_gaze_report['protected_pixel_max_error_0_to_255']==0
        high_gaze['expression_gaze_acceptance']='Geometry stage holds pupils fixed; final iris-only correction matches the source relative to final eyelids. Old Low-delta diagnostic is retained but not the target of this new ordering.'
    masks = {"off": torch.zeros_like(raw), "low": torch.maximum(low_mask, low_gaze_mask),
             "previous_high": torch.maximum(torch.maximum(low_mask,previous_mask),low_gaze_mask),
             "high": torch.maximum(torch.maximum(low_mask, high_mask), high_gaze_mask)}
    photos = {"off": raw_rgb, "low": uint8(low), "previous_high": uint8(previous_high), "high": uint8(high)}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    refs = sorted((root / "datasets/mitch-identity-stills-v3/validation").glob("val_*.jpg"))
    if len(refs) != 6:
        raise RuntimeError("Expected six genuine held-out references.")
    excluded_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in args.exclude_reference}
    excluded_hashes.add(hashlib.sha256(args.source.read_bytes()).hexdigest())
    refs = [path for path in refs if hashlib.sha256(path.read_bytes()).hexdigest() not in excluded_hashes]
    if len(refs) < 2:
        raise RuntimeError("At least two independent genuine scoring references are required.")
    reference_embeddings = [face(read(path)).normed_embedding for path in refs]
    centroid = np.mean(reference_embeddings, axis=0)
    centroid /= np.linalg.norm(centroid)
    floor = min(float(np.dot(a, b)) for a, b in itertools.combinations(reference_embeddings, 2))
    candidates = {}
    for level, rgb in photos.items():
        Image.fromarray(rgb).save(args.output_dir / f"{level}.png")
        selected_face = face(rgb)
        fixed_embedding = fixed_alignment_embedding(rgb, detected.kps)
        scores = [float(np.dot(selected_face.normed_embedding, ref)) for ref in reference_embeddings]
        active = masks[level][0, :, :, 0].numpy() > 0
        difference = np.abs(rgb.astype(np.int16) - raw_rgb.astype(np.int16))
        candidates[level] = {
            "centroid_similarity": round(float(np.dot(selected_face.normed_embedding, centroid)), 6),
            "raw_kps_fixed_alignment_centroid_similarity": round(float(np.dot(fixed_embedding,centroid)),6),
            "minimum_reference_similarity": round(min(scores), 6),
            "within_genuine_pairwise_floor": min(scores) >= floor,
            "per_reference_similarity": [round(v, 6) for v in scores],
            "pose_pitch_yaw_roll": [round(float(v), 4) for v in selected_face.pose],
            "maximum_pose_delta_from_source_degrees": round(float(np.max(np.abs(selected_face.pose-source_face.pose))), 4),
            "bbox_xyxy": [round(float(v), 3) for v in selected_face.bbox],
            "raw_output_embedding_similarity": round(float(np.dot(selected_face.normed_embedding, detected.normed_embedding)), 6),
            "protected_pixel_max_error_0_to_255": int(difference[~active].max(initial=0)),
        }
        Image.fromarray(np.round(active * 255).astype(np.uint8)).save(args.output_dir / f"{level}-mask.png")

    if candidates['high']['maximum_pose_delta_from_source_degrees'] > 3.0:
        validation_errors.append('Final High exceeds 3 degrees of source head-pose drift; a faithful polish of an already-drifted raw is not a source-preservation pass.')

    def sheet(items, path, crop=None, max_width=760):
        tiles = []
        for title, rgb in items:
            image = Image.fromarray(rgb)
            if crop:
                # Original source / public baseline can be larger than a native
                #1MP pilot. Match frame coordinates rather than clipping the
                #larger image with the smaller candidate's pixel coordinates.
                sx=image.width/raw_rgb.shape[1];sy=image.height/raw_rgb.shape[0]
                scaled=tuple(round(value*(sx if index%2==0 else sy))
                             for index,value in enumerate(crop))
                image = image.crop(scaled)
                # All face/eye/mouth comparisons use the candidate crop scale.
                target=(max(1,round(crop[2]-crop[0])),max(1,round(crop[3]-crop[1])))
                if image.size!=target:image=image.resize(target,Image.Resampling.LANCZOS)
            if image.width > max_width:
                image = image.resize((max_width, round(image.height * max_width / image.width)), Image.Resampling.LANCZOS)
            tiles.append((title, image))
        canvas = Image.new("RGB", (sum(image.width for _, image in tiles), max(image.height for _, image in tiles) + 48), (22, 22, 22))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default(size=20)
        left = 0
        for title, image in tiles:
            canvas.paste(image, (left, 48))
            draw.text((left + 14, 12), title, font=font, fill="white")
            left += image.width
        canvas.save(path, quality=96)

    high_label = ("HIGH - native treatment" if args.native_high_manifest else
                  "HIGH - final gaze" if args.final_source_gaze else
                  "HIGH - revised" if args.source_expression else
                  "HIGH - selected crease repair" if args.crease_repair else
                  "HIGH - source-shaped eyes" if args.eye_expression else
                  "HIGH - stronger retouch" if args.restful_retouch else
                  "HIGH - experimental expression" if args.smile_strength else "HIGH - eye/brow polish")
    raw_label = "HIGH - raw native edit" if args.native_high_manifest else "OFF - raw generation"
    low_label = ("HIGH - common finish" if args.native_high_manifest else
                 "LOW - expression-preserving" if args.no_forced_smile else "LOW - previous polish")
    items = [("SOURCE", source_rgb), (raw_label, photos["off"]),
             (low_label, photos["low"]), (high_label, photos["high"])]
    sheet(items, args.output_dir / "source-off-low-high.jpg")
    x1, y1, x2, y2 = detected.bbox
    crop = (max(0, int(x1 - 30)), max(0, int(y1 - 15)), min(raw_rgb.shape[1], int(x2 + 45)), min(raw_rgb.shape[0], int(y2 + 30)))
    sheet([items[0], items[2], items[3]], args.output_dir / "source-low-high-face.jpg", crop)
    eye_crop = (max(0, int(x1)), max(0, int(y1 + (y2-y1)*0.20)), min(raw_rgb.shape[1], int(x2)), int(y1+(y2-y1)*0.61))
    sheet([items[0], items[2], items[3]], args.output_dir / "source-low-high-eyes.jpg", eye_crop)
    expression_items = [items[0],("PREVIOUS HIGH",photos["previous_high"]),items[3]]
    sheet(expression_items,args.output_dir / "source-previous-high-new-high-face.jpg",crop)
    mouth_points = landmarks[[61,291,0,17]]
    mouth_crop = (max(0,int(mouth_points[:,0].min()-45)),max(0,int(mouth_points[:,1].min()-40)),
                  min(raw_rgb.shape[1],int(mouth_points[:,0].max()+45)),min(raw_rgb.shape[0],int(mouth_points[:,1].max()+55)))
    sheet(expression_items,args.output_dir / "source-previous-high-new-high-smile.jpg",mouth_crop)
    baseline_metrics = {}
    for name,path in (("low",args.baseline_low),("high",args.baseline_high)):
        if path:
            baseline_rgb = read(path)
            baseline_face = face(baseline_rgb)
            baseline_metrics[name] = {
                "path":str(path),
                "centroid_similarity":round(float(np.dot(baseline_face.normed_embedding,centroid)),6),
                "pose_pitch_yaw_roll":[round(float(v),4) for v in baseline_face.pose]}
            comparison = [items[0],(f"BASELINE {name.upper()}",baseline_rgb),("CANDIDATE HIGH",photos["high"])]
            sheet(comparison,args.output_dir / f"source-baseline-{name}-new-high-face.jpg",crop)
            sheet(comparison,args.output_dir / f"source-baseline-{name}-new-high-full.jpg")
    ref_tiles = []
    for path in refs:
        rgb = read(path)
        detected_ref = face(rgb)
        x0,y0,x3,y3 = detected_ref.bbox
        margin = (x3-x0)*0.12
        ref_crop = Image.fromarray(rgb).crop((max(0,int(x0-margin)),max(0,int(y0-margin)),
                                             min(rgb.shape[1],int(x3+margin)),min(rgb.shape[0],int(y3+margin))))
        ref_crop.thumbnail((240,280),Image.Resampling.LANCZOS)
        ref_tiles.append((path.stem[:18],np.array(ref_crop)))
    sheet(ref_tiles,args.output_dir / "genuine-reference-faces.jpg")
    report = {"source": str(args.source), "raw": str(args.raw), "local_only": True,
              "diffusion_runs": 0, "generation_prompt_changed_by_this_replay": False,
              "generation_scope": "This replay does not generate. Supplied raw and baseline paths may originate from different generation prompts; see the parent experiment manifest.",
              "native_high_manifest": str(args.native_high_manifest) if args.native_high_manifest else None,
              "raw_generation_manifest": str(args.raw_manifest) if args.raw_manifest else None,
              "executed_raw_graph_verified": bool(generation_manifest_path),
              "source_identity_diagnostic": round(float(np.dot(face(source_rgb).normed_embedding,centroid)),6),
              "source_identity_diagnostic_note": "Source is an edit target, not a scoring reference; this is not a genuineness judgment.",
              "source_pose_pitch_yaw_roll": [round(float(v), 4) for v in source_face.pose],
              "source_bbox_xyxy": [round(float(v), 3) for v in source_face.bbox],
              "expression_geometry_strength": args.source_expression,
              "final_source_gaze_selected": args.final_source_gaze,
              "replay_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "expression_module_sha256": hashlib.sha256((root/'scripts/experimental_upgrade_source_expression.py').read_bytes()).hexdigest() if args.source_expression else None,
              "native_high_comparison_note": ("off/low keys describe raw/common-finish stages of this High generation, NOT separately generated Off/Low settings. Use baseline_comparisons for true Low-versus-High comparison." if args.native_high_manifest else None),
              "experimental_polish_overrides": {"unconditional_smile_disabled": args.no_forced_smile,
                                                  "cheek_brightening_disabled": args.no_cheek_lift},
              "excluded_scoring_references": [str(path) for path in args.exclude_reference],
              "genuine_reference_count": len(refs), "genuine_pairwise_floor": round(floor, 6),
              "reference_orientation": "EXIF transpose before face analysis",
              "comparison_crop_coordinates": "Normalized from raw-frame crop into each image's dimensions; resampled to raw crop size for presentation only.",
              "references": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in refs],
              "candidates": candidates, "low_polish": low_report, "high_polish": high_report,
              "expression_validation": expression_validation,
              "baseline_comparisons":baseline_metrics,
              "validation_errors":validation_errors,
              "low_gaze": low_gaze, "high_gaze": high_gaze, "seconds": round(time.perf_counter()-started, 3)}
    (args.output_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("low_polish", "low_gaze", "high_gaze")}, indent=2))
    if validation_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
