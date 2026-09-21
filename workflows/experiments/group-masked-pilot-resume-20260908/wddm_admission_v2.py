"""Exact two newly root-reviewed desktop lifetimes; never a name/PID-only exception."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys
from datetime import timedelta

HERE=Path(__file__).resolve().parent
OLD=Path('C:/projects/AI-Tools/Mitch-Comfy/work/9b-readiness-resume-20260907/group-identity-hook-gate/runtime-3090')
sys.path.insert(0,str(OLD))
import wddm_watch_v3 as original
g=original.g
FIELDS=original.FIELDS
instant=original.instant
allowed_current=original.allowed_current  # Exact unchanged six-field live comparison.
EVIDENCE_SHA='6DB95A535879701647228C5271948EE01FD353640730C4D2659EF7E3BF1776C0'
BASE_CANDIDATE_SHA='A83F7325972CA5393BFA8C12ADFF149DB42BC095BB2E5F208A848B40837EFC51'
NEW_IDS={39712,54788}
PARENT_IDS={2012,14796}
SCOPE='GROUP_FRESH_V2_EXACT_DESKTOP_LIFETIMES'


def data():
    g.require(g.sha(OLD/'wddm_watch_v3.py')=='DFA4F28578635B2D94BD104CD378485C9E6996104475AE12668C819E6C395B15','Original desktop helper changed')
    evidence=HERE/'desktop-parent-evidence-20260908.json';base=HERE/'wddm-candidate-v3.json'
    g.require(g.sha(evidence)==EVIDENCE_SHA and g.sha(base)==BASE_CANDIDATE_SHA,'Pinned desktop evidence changed')
    e=json.loads(evidence.read_text(encoding='utf-8-sig'));b=json.loads(base.read_text(encoding='utf-8-sig'))
    g.require(e['amd_signature_status']=='Valid' and e['amd_signature_subject']=='CN=Advanced Micro Devices, O=Advanced Micro Devices, S=California, C=US','AMD signature evidence differs')
    g.require(len(b['processes'])==20 and all(r['matches_prior_lifetime'] is True for r in b['processes']),'Expected exact20 old desktop candidates')
    return b,e


def fields(row):
    # Missing metadata is not equivalent to explicit protected null metadata.
    g.require(set(FIELDS)<=set(row),'Incomplete process identity fields')
    g.require(type(row['pid']) is int and type(row['parent_pid']) is int,'Numeric exact process IDs required')
    g.require(isinstance(row['name'],str) and row['name'],'Process name missing')
    g.require(instant(row['creation_utc']).tzinfo is not None,'Timezone-aware process creation required')
    for key in ('executable_path','argv'):
        if row[key] is not None:
            g.require(isinstance(row[key],str) if key=='executable_path' else isinstance(row[key],list) and all(isinstance(v,str) for v in row[key]),'Wrong metadata type')
    return {k:row[k] for k in FIELDS}


def validate_approval(approval,candidate,current):
    base,evidence=data()
    g.require(approval.get('approved') is True and approval.get('scope')==SCOPE,'Explicit fresh-v2 desktop approval required')
    issued,expires=instant(approval['issued_utc']),instant(approval['expires_utc'])
    g.require(issued<=current<=expires and timedelta(0)<expires-issued<=timedelta(hours=1),'Desktop approval expired/future/overlong')
    g.require(candidate.get('approved') is False and candidate.get('scope')=='GROUP_FRESH_V2_DESKTOP_CANDIDATE','Wrong candidate scope')
    g.require(instant(candidate['captured_utc'])<=issued,'Approval predates its fresh capture')
    for value in (candidate,approval):
        g.require(value.get('parent_evidence_sha256')==EVIDENCE_SHA and value.get('prior_candidate_sha256')==BASE_CANDIDATE_SHA,'Desktop evidence chain changed')
        g.require(value.get('wddm_helper_sha256')==g.sha(Path(__file__)),'Wrong actual desktop helper')
    g.require(approval.get('supplement_prepared_sha256')==g.sha(HERE/'prepared-v2.json'),'Approval not bound to supplement')
    expected={r['pid']:r for r in base['processes']}
    new={r['pid']:r for r in evidence['processes'] if r['pid'] in NEW_IDS}
    expected.update(new)
    rows=candidate['processes'];reviewed=approval['reviewed_processes']
    g.require(len(rows)==len({r['pid'] for r in rows})==22 and {r['pid'] for r in rows}==set(expected),'Candidate adds/omits/duplicates lifetime')
    g.require(len(reviewed)==len({r['pid'] for r in reviewed})==22 and {r['pid'] for r in reviewed}==set(expected),'Approval adds/omits/duplicates lifetime')
    captured={r['pid']:r for r in rows}
    for row in reviewed:
        pid=row['pid'];record=captured[pid]
        g.require(g.same_graph(fields(record),fields(expected[pid])) and g.same_graph(fields(row),fields(record)),'Exact captured/reviewed lifetime changed')
        if pid in NEW_IDS:
            g.require(record.get('matches_prior_lifetime') is False and record.get('review_basis')=='explicit_new_lifetime','Never relabel a new PID as prior')
            g.require(row.get('new_lifetime_approved') is True,'New lifetime needs explicit per-process review')
        else:g.require(record.get('matches_prior_lifetime') is True,'Prior desktop lifetime changed')
        if row['executable_path'] is None or row['argv'] is None:
            g.require(row.get('protected_metadata_approved') is True,'Protected null metadata needs explicit per-process approval')
    parents={r['pid']:r for r in evidence['processes'] if r['pid'] in PARENT_IDS}
    for key,values in (('captured',candidate['parents']),('reviewed',approval['reviewed_parents'])):
        g.require(len(values)==2 and {r['pid'] for r in values}==PARENT_IDS,'Parent evidence incomplete')
        for row in values:
            g.require(g.same_graph(fields(row),fields(parents[row['pid']])),'Parent lifetime changed')
            if key=='reviewed' and (row['executable_path'] is None or row['argv'] is None):
                g.require(row.get('protected_metadata_approved') is True,'Protected parent needs explicit approval')
    return {r['pid']:r for r in reviewed}


def make_admit(bound):
    # Keep the tested bound subprocess environment, timing, receipts and comparisons.
    source=bound.admit_adapted
    changes=[("'wddm-root-approval-v3.json'","'wddm-root-approval-v2.json'"),
        ("'wddm-candidate-v3.json'","'wddm-candidate-v2.json'"),
        ("str(g.HERE/'wddm-lifetimes-v3.ps1'),","str(g.HERE/'fresh-v2.ps1'),'-Action','wddm',"),
        ("'approval':approval,'candidate':candidate,'first_checked_utc':g.now()",
         "'approval':approval,'candidate':candidate,'first_checked_utc':g.now(),'wddm_helper_sha256':g.sha(HELPER_PATH),'wddm_helper_path':str(HELPER_PATH),'supplement_prepared_sha256':g.sha(g.HERE/'prepared-v2.json')"),
        ("accepted=allowed_current(nvml_ids,owned_ids,approved,current['processes'])",
         "validate_capture(current,candidate)\n    accepted=allowed_current(nvml_ids,owned_ids,approved,current['processes'])")]
    result=source
    for before,after in changes:
        g.require(result.count(before)==1,'Desktop admission route anchor changed')
        result=result.replace(before,after)
    restored=result
    for before,after in reversed(changes):restored=restored.replace(after,before)
    g.require(restored==source,'Unexpected desktop observer change')
    namespace=dict(bound.admit_namespace,validate_approval=validate_approval,allowed_current=allowed_current,
                   validate_capture=validate_capture,HELPER_PATH=Path(__file__))
    exec(compile(result,str(__file__)+':admit_desktops','exec'),namespace)
    return namespace['admit_desktops']


def validate_capture(current,candidate):
    g.require(current['scope']==candidate['scope'] and current['wddm_helper_sha256']==candidate['wddm_helper_sha256'],'Wrong live capture route')
    g.require(current['parent_evidence_sha256']==EVIDENCE_SHA and current['prior_candidate_sha256']==BASE_CANDIDATE_SHA,'Live evidence route changed')
    g.require(g.same_graph(current['parents'],candidate['parents']),'Live parent lifetime changed')
    g.require(len(current['processes'])==len({r['pid'] for r in current['processes']})==22,'Missing/duplicate live process')
