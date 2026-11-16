import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import codex_engine
import engine


class FakeBroker:
    def __init__(self,root,item_dir,job,request,brief,skill,emit,cancel):
        self.selection=brief['selection']['id']
        self.state={}
    def definitions(self):return [{'name':'save_draft','description':'test','inputSchema':{'type':'object'}}]
    def call(self,name,args):
        self.state.update(templateId=self.selection+'-template',iteration=1,
                          validation={'savedFull':'pass','preview':'pass'},localFiles=[])
        return self.state
    def result(self):return self.state


class CodexEngineTests(unittest.TestCase):
    def execute(self,behavior,briefs=None,cancel=None):
        root=Path(self.tmp.name);job=root/'job';skill=root/'skill';skill.mkdir(exist_ok=True)
        briefs=briefs or [{'selection':{'id':'first','name':'First'}},{'selection':{'id':'second','name':'Second'}}]
        env={'cli':{'authenticated':True,'apiReachable':True,'apiUrl':engine.PRODUCTION},
             'codex':{'ready':True},'versions':[{'id':'v1.5','authoringAvailable':True}],
             'workspaces':[{'id':'ws-test'}]}
        request={'targetVersion':'v1.5','workspaceId':'ws-test','folderId':'default','itemTimeoutSeconds':300,'maxRepairs':1}
        with patch.object(codex_engine,'get_environment',return_value=env), \
             patch('mosaic_agent_tools.MosaicAgentTools',FakeBroker), \
             patch('codex_runtime.run_codex',side_effect=behavior), \
             patch.object(engine,'_run_legacy_autopilot_job') as old_runner:
            report=codex_engine.run_job(root,job,request,briefs,skill,lambda e:self.events.append(e),cancel or threading.Event())
            old_runner.assert_not_called()
        return report

    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.events=[]
    def tearDown(self):self.tmp.cleanup()

    def test_failed_first_card_does_not_skip_second(self):
        calls=[]
        def run(cwd,prompt,defs,handler,emit,cancel,**kw):
            calls.append(prompt)
            if len(calls)==1:raise RuntimeError('first source failed')
            handler('save_draft',{})
            return {'status':'completed','threadId':'real-shape-id','turnId':'turn-id'}
        result=self.execute(run)
        self.assertEqual(len(calls),2)
        self.assertEqual([i['status'] for i in result['items']],['failed','needs_review'])
        self.assertEqual(result['summary']['total'],2)
        self.assertEqual(result['summary']['saved'],1)
        self.assertEqual(result['summary']['failed'],1)
        self.assertEqual(result['status'],'partial')

    def test_timeout_keeps_draft_and_continues_next(self):
        calls=[]
        def run(cwd,prompt,defs,handler,emit,cancel,**kw):
            handler('save_draft',{});calls.append(1)
            return {'status':'timed_out' if len(calls)==1 else 'completed'}
        result=self.execute(run)
        self.assertEqual([i['status'] for i in result['items']],['timed_out','needs_review'])
        self.assertEqual(result['summary']['saved'],2)
        self.assertEqual(result['summary']['timedOut'],1)

    def test_cancel_accounts_for_every_selected_card(self):
        cancel=threading.Event()
        def run(cwd,prompt,defs,handler,emit,item_cancel,**kw):
            handler('save_draft',{});cancel.set()
            return {'status':'interrupted'}
        result=self.execute(run,cancel=cancel)
        self.assertEqual(len(result['items']),2)
        self.assertTrue(all(i['status']=='cancelled' for i in result['items']))
        self.assertEqual(result['summary']['cancelled'],2)

    def test_large_source_is_a_file_not_a_giant_prompt(self):
        source={'selection':{'id':'large','name':'Large'},'designTree':{'large':'x'*250000}}
        def run(cwd,prompt,defs,handler,emit,cancel,**kw):
            self.assertLess(len(prompt.encode()),16000)
            self.assertEqual(len(json.loads((cwd/'source.json').read_text())['designTree']['large']),250000)
            handler('save_draft',{})
            return {'status':'completed'}
        result=self.execute(run,[source])
        self.assertEqual(result['items'][0]['status'],'needs_review')

    def test_model_final_text_is_not_a_save_receipt(self):
        result=self.execute(lambda *a,**kw:{'status':'completed','finalText':'Everything saved successfully!'})
        self.assertEqual(result['summary']['saved'],0)
        self.assertEqual(result['summary']['failed'],2)

    def test_every_terminal_block_is_in_summary(self):
        result=codex_engine.summarize({'items':[{'status':'needs_context_reduction'}, {'status':'needs_source_evidence'}, {'status':'not_run'}, {'status':'cancelled'}, {'status':'needs_recovery'}, {'status':'future_failure_code'}]})
        self.assertEqual(result['summary']['failed'],4)
        self.assertEqual(result['summary']['notRun'],1)
        self.assertEqual(result['summary']['cancelled'],1)


if __name__=='__main__':unittest.main()
