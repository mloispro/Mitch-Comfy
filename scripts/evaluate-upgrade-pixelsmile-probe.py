"""Local genuine-reference and full-frame evaluation; no generation or face repair."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from runpy import run_path

ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT.parent/'ComfyUI'
runner = run_path(str(ROOT/'scripts/run-upgrade-pixelsmile-probe.py'))
sha, api = runner['sha'], runner['api']


def read(path):
    with Image.open(path) as image:return np.array(ImageOps.exif_transpose(image).convert('RGB'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to(ROOT/'work'):raise ValueError('Use a workspace experiment.')
    destination = run/'evaluation'
    if destination.exists():raise ValueError('Preserve previous evaluation.')
    manifest = json.loads((run/'experiment.json').read_text(encoding='utf-8'))
    submission = json.loads((run/'submission.json').read_text(encoding='utf-8'))
    prompt_id = submission['prompt_id']
    history = api(8188,'history/'+prompt_id).get(prompt_id)
    if not history or not history['status']['completed'] or history['status']['status_str']!='success':
        raise ValueError('Wait for this exact live job; no successful output yet.')
    expected = manifest['prompt']
    outputs = history['outputs']['14']['images']
    if len(outputs)!=1 or outputs[0]['type']!='output':raise ValueError('Unexpected outputs.')
    item = outputs[0]
    output = (COMFY/'output'/item['subfolder']/item['filename']).resolve()
    if not output.is_relative_to(COMFY/'output'):raise ValueError('Unsafe output path.')
    with Image.open(output) as image:
        executed = json.loads(image.info['prompt'])
    for node in executed.values():node.pop('is_changed',None)
    if executed!=expected:raise ValueError('Output does not match the submitted graph.')
    loras = [n['inputs']['lora_name'].replace('\\','/') for n in executed.values() if n['class_type']=='LoraLoaderModelOnly']
    if loras!=['pixelsmile/PixelSmile-preview.safetensors']:raise ValueError('Unexpected adapter lineage.')
    source = Path(manifest['source']['path'])
    if sha(source)!=manifest['source']['sha256']:raise ValueError('Source changed.')
    refs = [p for p in (ROOT/'datasets/mitch-identity-stills-v3/validation').glob('*.jpg') if sha(p)!=manifest['source']['sha256']]
    if len(refs)!=5:raise ValueError('Expected five genuine non-source photographs.')
    models = Path.home()/'.insightface/models/antelopev2'
    if not all((models/name).is_file() for name in ('scrfd_10g_bnkps.onnx','glintr100.onnx','1k3d68.onnx')):
        raise ValueError('Existing scoring models missing; no automatic downloads.')
    from insightface.app import FaceAnalysis
    sys.path.insert(0,str(ROOT/'custom_nodes/ComfyUI-AIToolkit-Training'))
    import flux2_klein9b_source_gaze_lock as gaze
    from experimental_upgrade_smile_balance import measure_smile
    cv2.setNumThreads(4)
    analyzer = FaceAnalysis(name='antelopev2',root=str(Path.home()/'.insightface'),
        providers=['CPUExecutionProvider'],allowed_modules=['detection','recognition','landmark_3d_68'])
    analyzer.prepare(ctx_id=-1,det_size=(640,640))
    def face(rgb):
        found = analyzer.get(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if not found:raise ValueError('No detected face.')
        return max(found,key=lambda f:(f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1])),len(found)
    vectors = [face(read(p))[0].normed_embedding for p in refs]
    centroid = np.mean(vectors,axis=0);centroid/=np.linalg.norm(centroid)
    photos = {'SOURCE':read(source),'PIXELSMILE':read(output)}
    results, detections = {},{}
    for name,rgb in photos.items():
        found,count = face(rgb);detections[name] = found
        points = gaze._detect_refined_landmarks(rgb)[0]
        results[name] = {'identity_centroid':float(found.normed_embedding@centroid),
            'per_reference_similarity':[float(found.normed_embedding@v) for v in vectors],
            'pose':found.pose.tolist(),'mouth_opening_ratio':float(measure_smile(points)['opening_ratio']),
            'eye_coordinates':[gaze._eye_measurement(points,e)['coordinate'].tolist() for e in gaze._EYES],
            'detected_faces':count,'primary_selection':'largest bounding-box area'}
    report = {'status':'evaluated_pending_visual_review_not_promoted','prompt_id':prompt_id,
        'source':manifest['source'],'output':{'path':str(output),'sha256':sha(output)},
        'manifest_sha256':sha(run/'experiment.json'),
        'references':[{'path':str(p),'sha256':sha(p)} for p in refs],
        'source_excluded':True,'character_lora':False,'upstream_character_lora':False,
        'results':results,'max_pose_delta':float(np.abs(np.array(results['SOURCE']['pose'])-results['PIXELSMILE']['pose']).max()),
        'max_eye_coordinate_delta':float(np.abs(np.array(results['SOURCE']['eye_coordinates'])-results['PIXELSMILE']['eye_coordinates']).max()),
        'conditioning_runtime':history['outputs'].get('7',{}),
        'history_messages':history['status']['messages'],
        'gaze_repair_applied':False,'production_promoted':False,
        'limitation':'A genuine-source expression pilot, not the finished three-photo beauty policy. No numerical score proves attractiveness.'}
    destination.mkdir()
    (destination/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
    for crop,filename,height in ((False,'source-candidate-full.jpg',1024),(True,'source-candidate-face.jpg',512),(False,'source-candidate-thumbnail.jpg',360)):
        panels = []
        for name,rgb in photos.items():
            image = Image.fromarray(rgb)
            if crop:
                box = detections[name].bbox;pad=(box[2]-box[0])*.15
                image=image.crop(tuple(np.rint(box+[-pad,-pad,pad,pad]).astype(int)))
            image=image.resize((round(image.width*height/image.height),height),Image.Resampling.LANCZOS)
            panels.append((name,image))
        sheet = Image.new('RGB',(sum(im.width for _,im in panels),height+32),(20,20,20))
        draw=ImageDraw.Draw(sheet);x=0
        for name,image in panels:sheet.paste(image,(x,32));draw.text((x+6,8),name,fill='white');x+=image.width
        sheet.save(destination/filename,quality=97)
    (destination/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
