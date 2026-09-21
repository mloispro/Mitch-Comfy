"""Release only this task's verified completed portrait-probe cache for its next test."""
import importlib.util
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=ROOT/'work/upgrade-source-faithful-20260903/portrait-detail-house-010'
NEXT=ROOT/'work/upgrade-source-faithful-20260903/background-detail-house-pilot'
JOB='ff61023b-21bd-4b3d-a02a-6d3b40ff7373'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('portrait_to_background','background_to_scene'),default='portrait_to_background')
    args=parser.parse_args()
    previous,next_run,job=PREVIOUS,NEXT,JOB
    if args.phase=='background_to_scene':
        previous=NEXT
        next_run=ROOT/'work/upgrade-source-faithful-20260903/background-detail-house-scene-reference'
        job='a604aade-2954-4a16-aba0-bfb07dc141a2'
    intent_path=next_run/'owned-cache-release-intent.json'
    if intent_path.exists() or (next_run/'submission-intent.json').exists():
        raise ValueError('Release/submission attempt already exists; inspect rather than repeat.')
    spec=importlib.util.spec_from_file_location('own_cache_guard',ROOT/'scripts/run-upgrade-dev-high.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    before=guard.idle_snapshot(previous)
    if before['owned_cache_prompt_id']!=job or any(w.get('running') or w.get('pending') for w in before['workers']):
        raise ValueError('Both GPUs must be idle, with exact owned terminal graph.')
    stats=guard.api(8188,'system_stats')
    expected=[str(ROOT.parent/'ComfyUI/main.py'),'--cuda-device',
              'GPU-c2ca4516-2c9f-e87b-3a20-f459947ddb17','--port','8188','--disable-auto-launch']
    if stats['system']['argv']!=expected:
        raise ValueError('Primary worker launch identity changed.')
    after_check=guard.idle_snapshot(previous)
    if any(w.get('running') or w.get('pending') for w in after_check['workers']):
        raise ValueError('A queue became active.')
    record={'purpose':'Free this completed task experiment cache for the same task next background test',
            'phase':args.phase,'next_run':str(next_run),
            'owned_prompt_id':job,'before':before,'second_check':after_check,
            'stats_before':stats,'endpoint':'http://127.0.0.1:8188/free',
            'body':{'unload_models':True,'free_memory':True},'secondary_mutated':False,
            'interrupt':False,'restart':False,'automatic_retry':False}
    intent_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    # /free returns empty HTTP200, unlike JSON-returning endpoints.
    import urllib.request
    request=urllib.request.Request(record['endpoint'],data=json.dumps(record['body']).encode(),
                                   headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:
        result={'http_status':response.status,'body':response.read().decode()}
    (next_run/'owned-cache-release-response.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
