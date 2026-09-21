"""CPU regression fixtures only. No live capture/approval files, processes or GPU calls."""
import copy
from datetime import datetime,timezone
from pathlib import Path
import unittest
from unittest.mock import patch
import wddm_admission_v2 as w
import fresh_runtime_v2 as f


class DesktopTests(unittest.TestCase):
    def setUp(self):
        base,e=w.data();self.current=datetime(2026,9,8,6,0,tzinfo=timezone.utc)
        rows=copy.deepcopy(base['processes'])
        for row in e['processes']:
            if row['pid'] in w.NEW_IDS:rows.append(dict(row,matches_prior_lifetime=False,review_basis='explicit_new_lifetime'))
        self.candidate=dict(captured_utc='2026-09-08T05:59:00Z',scope='GROUP_FRESH_V2_DESKTOP_CANDIDATE',approved=False,
            parent_evidence_sha256=w.EVIDENCE_SHA,prior_candidate_sha256=w.BASE_CANDIDATE_SHA,
            wddm_helper_sha256=w.g.sha(Path(w.__file__)),processes=rows,
            parents=[copy.deepcopy(r) for r in e['processes'] if r['pid'] in w.PARENT_IDS])
        self.approval=dict(approved=True,scope=w.SCOPE,issued_utc='2026-09-08T05:59:30Z',expires_utc='2026-09-08T06:30:00Z',
            parent_evidence_sha256=w.EVIDENCE_SHA,prior_candidate_sha256=w.BASE_CANDIDATE_SHA,
            wddm_helper_sha256=w.g.sha(Path(w.__file__)),supplement_prepared_sha256='A'*64,
            reviewed_processes=copy.deepcopy(rows),reviewed_parents=copy.deepcopy(self.candidate['parents']))
        for r in self.approval['reviewed_processes']+self.approval['reviewed_parents']:
            if r['pid'] in w.NEW_IDS:r['new_lifetime_approved']=True
            if r['executable_path'] is None or r['argv'] is None:r['protected_metadata_approved']=True
        old=w.g.sha
        self.sha_patch=patch.object(w.g,'sha',side_effect=lambda p:'A'*64 if Path(p)==w.HERE/'prepared-v2.json' else old(p))
        self.sha_patch.start();self.addCleanup(self.sha_patch.stop)

    def validate(self):return w.validate_approval(self.approval,self.candidate,self.current)

    def test_exact_old20_and_explicit_new2_pass(self):
        approved=self.validate();self.assertEqual(len(approved),22)
        self.assertFalse(approved[39712]['matches_prior_lifetime'])
        self.assertEqual(w.allowed_current(set(approved)|{888}, {888}, approved,self.candidate['processes']),set(approved))

    def test_new_flag_is_not_prior_lifetime(self):
        next(r for r in self.candidate['processes'] if r['pid']==39712)['matches_prior_lifetime']=True
        with self.assertRaises(RuntimeError):self.validate()

    def test_new_explicit_review_required(self):
        next(r for r in self.approval['reviewed_processes'] if r['pid']==54788).pop('new_lifetime_approved')
        with self.assertRaises(RuntimeError):self.validate()

    def test_changed_exact_field_rejected(self):
        for key,value in [('parent_pid',1),('name','other.exe'),('creation_utc','2026-09-08T05:43:18.9265190+00:00'),('executable_path','C:/other.exe'),('argv',['changed'])]:
            saved=copy.deepcopy(self.approval)
            next(r for r in self.approval['reviewed_processes'] if r['pid']==54788)[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):self.validate()
            self.approval=saved

    def test_missing_or_unapproved_null_rejected(self):
        row=next(r for r in self.approval['reviewed_processes'] if r['pid']==39712)
        row.pop('protected_metadata_approved')
        with self.assertRaises(RuntimeError):self.validate()
        row['protected_metadata_approved']=True;row.pop('argv')
        with self.assertRaises(RuntimeError):self.validate()

    def test_missing_unreviewed_and_duplicate_rejected(self):
        for change in ('missing','extra','duplicate'):
            saved=copy.deepcopy(self.approval)
            if change=='missing':self.approval['reviewed_processes'].pop()
            elif change=='duplicate':self.approval['reviewed_processes'].append(copy.deepcopy(self.approval['reviewed_processes'][0]))
            else:self.approval['reviewed_processes'][-1]['pid']=12345
            with self.subTest(change=change),self.assertRaises(RuntimeError):self.validate()
            self.approval=saved

    def test_expiry_future_overlong_and_wrong_supplement(self):
        for key,value in [('expires_utc','2026-09-08T05:59:59Z'),('issued_utc','2026-09-08T06:01:00Z'),('expires_utc','2026-09-08T08:00:00Z'),('supplement_prepared_sha256','B'*64)]:
            saved=copy.deepcopy(self.approval);self.approval[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):self.validate()
            self.approval=saved

    def test_parent_changed_or_protected_parent_not_approved(self):
        parent=next(r for r in self.approval['reviewed_parents'] if r['pid']==2012)
        parent.pop('protected_metadata_approved')
        with self.assertRaises(RuntimeError):self.validate()
        parent['protected_metadata_approved']=True;parent['creation_utc']='2026-09-08T01:00:00Z'
        with self.assertRaises(RuntimeError):self.validate()

    def test_live_reuse_changed_args_missing_and_unknown_refuse(self):
        approved=self.validate()
        for key,value in [('creation_utc','2026-09-08T05:43:18.9265190+00:00'),('argv',['changed']),('parent_pid',12)]:
            live=copy.deepcopy(self.candidate['processes']);next(r for r in live if r['pid']==54788)[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):w.allowed_current({54788},set(),approved,live)
        with self.assertRaises(RuntimeError):w.allowed_current({54788},set(),approved,[])
        with self.assertRaises(RuntimeError):w.allowed_current({999999},set(),approved,self.candidate['processes'])

    def test_observer_route_native_registration_unchanged(self):
        with patch.object(f,'verify',return_value={}):guard,observer=f.route()
        self.assertEqual(guard.__file__,str(f.HERE/'fresh_runtime.py'))
        fn=observer.namespace['admit_desktops']
        self.assertIn('fresh-v2.ps1',fn.__code__.co_consts)
        self.assertIn('wddm-root-approval-v2.json',fn.__code__.co_consts)
        self.assertIs(fn.__globals__['validate_approval'],w.validate_approval)
        self.assertIs(fn.__globals__['allowed_current'],w.original.allowed_current)


if __name__=='__main__':unittest.main()
