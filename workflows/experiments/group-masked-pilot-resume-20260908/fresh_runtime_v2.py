"""Fresh watcher desktop admission supplement; original native registration is unchanged."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import fresh_runtime as original

HERE=Path(__file__).resolve().parent


def verify():
    result=original.verify()  # All original18 fresh +193 historical checks remain.
    for filename,expected in [('fresh_runtime.py','2D7C80392E35F7D5CB657121980742207ED1B2391ACA7230375A0A4ACC74A02D'),('fresh.ps1','F4902FF8338C4F772BC0009CB063578698B888307C709D08BC2687F394C13560')]:
        original.require(original.sha(HERE/filename)==expected,'Frozen fresh facade changed')
    manifest=original.read(HERE/'prepared-v2.json')
    original.require(manifest['scope']=='ONE_FRESH_GROUP_DESKTOP_SUPPLEMENT' and manifest['original_prepared_sha256']==original.sha(HERE/'prepared.json'),'Wrong supplemental preparation')
    for pin in manifest['pins']:original.require(original.sha(pin['path'])==pin['sha256'],'Supplement changed: '+pin['path'])
    return dict(result,supplement_pins=len(manifest['pins']))


def route():
    verify()
    guard,observer=original.route()
    import wddm_admission_v2
    observer.namespace['admit_desktops']=wddm_admission_v2.make_admit(observer.prior)
    # Do not alter guard.__file__: existing private registration and ready SHA are exact originals.
    return guard,observer


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--watch',action='store_true');p.add_argument('--case',choices=('pilot',),default='pilot');args=p.parse_args()
    if args.watch:
        _,observer=route();asyncio.run(observer.run_case(args.case))
    else:print(json.dumps(verify()))
