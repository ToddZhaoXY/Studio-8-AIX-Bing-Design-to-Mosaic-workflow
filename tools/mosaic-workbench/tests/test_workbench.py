from __future__ import annotations

import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skills import SkillStore
from server import Workbench, ROOT


def skill_text(version='3.6'):
    return '---\nname: mosaic-gen-workflow\ndescription: Test package\n---\n# Mosaic Gen Workflow (v'+version+', Bing-focused)\n[Reference](./references/rules.md)\n'


def package(version='3.7',broken=False):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        archive.writestr('mosaic-gen-workflow/SKILL.md',skill_text(version))
        if not broken:archive.writestr('mosaic-gen-workflow/references/rules.md','Test rules')
    return out.getvalue()


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        installed=self.root/'.agents/skills/mosaic-gen-workflow'
        (installed/'references').mkdir(parents=True)
        (installed/'SKILL.md').write_text(skill_text())
        (installed/'references/rules.md').write_text('Original rules')
        self.store=SkillStore(self.root)

    def tearDown(self):self.tmp.cleanup()

    def test_import_never_switches_running_snapshot(self):
        old=self.store.list()['activeId'];snapshot=self.root/'snapshot'
        self.store.snapshot(old,snapshot)
        imported=self.store.import_zip(package())
        self.assertEqual(self.store.list()['activeId'],old)
        self.store.activate(imported['id'])
        self.assertEqual(self.store.list()['versions'][0]['version'],'3.7')
        self.assertIn('v3.6',(snapshot/'SKILL.md').read_text())
        self.assertIn('v3.6',(self.root/'.agents/skills/mosaic-gen-workflow/SKILL.md').read_text())

    def test_missing_reference_rejected(self):
        with self.assertRaisesRegex(ValueError,'reference is missing'):self.store.import_zip(package(broken=True))

    def test_traversal_rejected_without_write(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:archive.writestr('../escape','bad')
        with self.assertRaisesRegex(ValueError,'unsafe path'):self.store.import_zip(out.getvalue())
        self.assertFalse((self.root/'escape').exists())

    def test_modified_skill_rejected(self):
        folder,info=self.store.resolve();(folder/'references/rules.md').write_text('Changed')
        with self.assertRaisesRegex(ValueError,'files have changed'):self.store.resolve(info['id'])

    def test_unknown_version_rejected(self):
        with self.assertRaises(ValueError):self.store.activate('../../other')


class RunGuardTests(unittest.TestCase):
    def make_app(self):
        app=object.__new__(Workbench)
        app.catalog={'items':[{'id':'one','name':'Example'}]}
        return app

    def test_no_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Select between'):self.make_app().start({'selectionIds':[]})

    def test_unknown_selection_is_rejected(self):
        app=self.make_app();app.get_catalog=lambda:app.catalog
        with self.assertRaisesRegex(ValueError,'no longer in this library'):app.start({'selectionIds':['unknown']})

    def test_workspace_shell_text_is_rejected(self):
        app=self.make_app();app.get_catalog=lambda:app.catalog
        with self.assertRaisesRegex(ValueError,'Workspace'):app.start({'selectionIds':['one'],'targetVersion':'v1.5','workspaceId':'ws;echo bad','folderId':'default'})

    def test_outside_project_output_is_rejected(self):
        app=self.make_app();app.get_catalog=lambda:app.catalog
        with self.assertRaisesRegex(ValueError,'inside the current project'):app.start({'selectionIds':['one'],'targetVersion':'v1.5','workspaceId':'ws-test','folderId':'default','outputRoot':'/tmp/outside'})

    def test_restart_retains_drafts_and_closes_stale_item_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp);directory=state/'job';directory.mkdir()
            jobs={'batch':{'status':'running','directory':str(directory),'partialItems':[
                {'selectionId':'saved','status':'needs_review','templateId':'keep-me'},
                {'selectionId':'active','status':'running','templateId':'draft'},
                {'selectionId':'waiting','status':'queued'}]}}
            (state/'jobs.json').write_text(json.dumps(jobs))
            with patch('server.STATE',state),patch('server.SkillStore'):
                app=Workbench()
            job=app.jobs['batch']
            self.assertEqual(job['status'],'interrupted')
            self.assertEqual([i['status'] for i in job['partialItems']],['needs_review','interrupted','not_run'])
            self.assertEqual(job['partialItems'][1]['templateId'],'draft')

    def test_batch_events_keep_full_evidence_only_in_item_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            item={'selectionId':'one','status':'needs_review','execution':{'evidence':'x'*100000}}
            job={'id':'batch','directory':str(directory),'request':{'selectionIds':['one']},'events':[]}
            app=object.__new__(Workbench)
            app.jobs={'batch':job};app.lock=threading.RLock();app.active_id='batch';app.cancel=threading.Event()
            app.index=directory/'jobs.json'
            def execute(root,path,request,briefs,skill,emit,cancel):
                emit({'type':'batch','items':[item],'message':'progress'})
                emit({'type':'item','item':item})
                return {'status':'needs_review','items':[item],'summary':{'message':'done'}}
            with patch('catalog.extract_selection',return_value={'selection':{'id':'one'}}),patch('codex_engine.run_job',side_effect=execute):
                app.execute('batch',app.cancel)
            self.assertEqual(job['partialItems'],[item])
            self.assertEqual(job['report']['items'],[item])
            self.assertTrue(all('items' not in e and 'item' not in e for e in job['events']))
            self.assertLess((directory/'job.json').stat().st_size,210000)


if __name__=='__main__':unittest.main()
