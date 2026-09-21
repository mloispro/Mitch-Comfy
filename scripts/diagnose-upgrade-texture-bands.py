"""Read-only, face-scale-aware texture diagnosis of an audited native High and finish.

Frequency contrast is not a pore detector, realism score, or identity measurement.
Presentation sheets are diagnostics; no edited candidate is produced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def texture_bands(rgb, scale):
    rgb = np.asarray(rgb)
    if (rgb.ndim != 3 or rgb.shape[2] != 3 or not np.isfinite(rgb).all()
            or not np.isfinite(scale) or scale <= 0):
        raise ValueError('Expected finite RGB and a positive anatomical scale.')
    light = rgb.astype(np.float32) / 255 @ np.array([.2126, .7152, .0722], np.float32)
    sigmas = [max(.4, scale * n) for n in (.6, 1.5, 4., 12.)]
    levels = [light] + [cv2.GaussianBlur(light, (0, 0), s,
        borderType=cv2.BORDER_REFLECT_101) for s in sigmas]
    names = ('subpixel', 'fine', 'medium', 'broad')
    bands = {name: a-b for name, a, b in zip(names, levels, levels[1:])}
    return bands, sigmas


def profile(rgb, selected, scale):
    selected = np.asarray(selected)
    if selected.dtype != bool or selected.shape != np.asarray(rgb).shape[:2] or selected.sum() < 100:
        raise ValueError('Expected at least100 selected image pixels in a boolean mask.')
    bands, sigmas = texture_bands(rgb, scale)
    report = {'pixels': int(selected.sum()), 'sigma_pixels': sigmas, 'bands': {}}
    for name, band in bands.items():
        values = band[selected].astype(np.float64) * 255
        report['bands'][name] = {'std_0_to_255': float(values.std()),
            'rms_0_to_255': float(np.sqrt(np.mean(values**2))),
            'abs_p50_p90_p99_0_to_255': np.percentile(np.abs(values), [50, 90, 99]).tolist()}
    return report, bands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finish-audit', type=Path, required=True, action='append')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(root):
        raise ValueError('Use a new project-local diagnostic directory.')
    sys.path.insert(0, str(root/'custom_nodes/ComfyUI-AIToolkit-Training'))
    from flux2_klein9b_source_gaze_lock import _detect_refined_landmarks
    from experimental_upgrade_skin_polish import skin_regions

    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def read(path, expected=None):
        if expected is not None and digest(path) != expected:
            raise ValueError(f'Audited image changed: {path}')
        with Image.open(path) as image:
            return np.array(ImageOps.exif_transpose(image).convert('RGB'))

    prepared = []
    for audit_path in args.finish_audit:
        finish = json.loads(audit_path.read_text(encoding='utf-8-sig'))
        native_path = root/finish['native_audit']
        if digest(native_path) != finish['native_audit_sha256']:
            raise ValueError('Native audit changed.')
        native = json.loads(native_path.read_text(encoding='utf-8-sig'))
        if not native['executed_png_graph_verified'] or native['postprocess_applied']:
            raise ValueError('Expected previously verified raw native generation.')
        if not finish['common_polish_applied'] or finish['input_records'] != native['inputs']:
            raise ValueError('Expected a matched common-polish finish.')
        paths = {label: root/native['inputs'][key]['path'] for label, key in (
            ('BASE RAW', 'BASE RAW'), ('NATIVE HIGH', 'CANDIDATE HIGH'))}
        photos = {label: read(path, native['inputs'][key]['sha256']) for (label, path), key in
            zip(paths.items(), ('BASE RAW', 'CANDIDATE HIGH'))}
        paths['FINISHED HIGH'] = audit_path.parent/'high-source-gaze.png'
        with Image.open(paths['FINISHED HIGH']) as image:
            metadata = json.loads(image.info['postprocess'])
        if (metadata['input_sha256'] != native['inputs']['CANDIDATE HIGH']['sha256']
                or metadata['source_sha256'] != native['inputs']['SOURCE']['sha256']
                or metadata['common_polish_applied'] is not True):
            raise ValueError('Finished PNG metadata does not match audited native input.')
        photos['FINISHED HIGH'] = read(paths['FINISHED HIGH'])
        if photos['NATIVE HIGH'].shape != photos['FINISHED HIGH'].shape:
            raise ValueError('Finish changed image dimensions.')
        results, panels = {}, []
        native_geometry = None
        for label, rgb in photos.items():
            if label == 'FINISHED HIGH':
                selected, geometry, points = native_geometry
            else:
                points, _ = _detect_refined_landmarks(rgb)
                alpha, valid, geometry = skin_regions(rgb.astype(np.float32)/255, points)
                selected = valid & (alpha > .8)
                if label == 'NATIVE HIGH': native_geometry = (selected, geometry, points)
            results[label], bands = profile(rgb, selected, geometry['scale'])
            results[label]['anatomical_face_width'] = geometry['face_width']
            results[label]['mask_sha256'] = hashlib.sha256(selected.tobytes()).hexdigest()
            bounds = np.array([*points.min(axis=0), *points.max(axis=0)])
            margin = geometry['face_width']*.08
            box = tuple(np.rint(bounds+[-margin, -margin, margin, margin]).astype(int))
            overlay = rgb.copy()
            overlay[selected] = np.clip(overlay[selected]*.55 + [0,100,0], 0,255).astype(np.uint8)
            fine = np.repeat(np.clip(.5+bands['fine']*8,0,1)[...,None],3,axis=2)
            for variant, array in (('photo',rgb),('measured skin',overlay),
                    ('fine band x8', np.rint(fine*255).astype(np.uint8))):
                tile = Image.fromarray(array).crop(box)
                tile = tile.resize((round(tile.width*320/tile.height),320),Image.Resampling.LANCZOS)
                panels.append((label+' / '+variant,tile))
        ratios = {}
        for before, after in (('BASE RAW','NATIVE HIGH'),('NATIVE HIGH','FINISHED HIGH')):
            ratios[before+' -> '+after] = {band: results[after]['bands'][band]['std_0_to_255'] /
                max(results[before]['bands'][band]['std_0_to_255'],1e-8)
                for band in results[before]['bands']}
        report = {'finish_audit':str(audit_path),'finish_audit_sha256':digest(audit_path),
            'native_audit':str(native_path),'native_audit_sha256':digest(native_path),
            'images':{label:{'path':str(path),'sha256':digest(path)} for label,path in paths.items()},
            'profiles':results,'contrast_ratios':ratios,
            'native_failures_retained':native['failures'],
            'comparison_scope':'Raw/native use separate anatomical regions/scales; native/finish use the exact same native mask and scale.',
            'limitation':'Band contrast includes noise, pores, freckles, shading and synthesis artifacts. No component is identified as genuine pore detail. Changed anatomy can confound raw/native comparison. No candidate edited or promoted.'}
        prepared.append((audit_path.parent.parent.name, report, panels))
    args.output_dir.mkdir(parents=True)
    all_results = {}
    for name, report, panels in prepared:
        destination = args.output_dir/name
        destination.mkdir()
        font = ImageFont.load_default(size=13)
        widths = [max(panels[k+j][1].width for j in range(3)) for k in (0,3,6)]
        sheet = Image.new('RGB',(sum(widths),3*355),(22,22,22))
        draw = ImageDraw.Draw(sheet)
        x = 0
        for column,k in enumerate((0,3,6)):
            for row in range(3):
                label,tile=panels[k+row]
                draw.text((x+5,row*355+5),label,font=font,fill='white')
                sheet.paste(tile,(x,row*355+30))
            x+=widths[column]
        sheet.save(destination/'texture-diagnostic.jpg',quality=97)
        (destination/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        all_results[name]=report['contrast_ratios']
    print(json.dumps(all_results,indent=2))


if __name__ == '__main__': main()
