import base64
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codex_runtime as runtime


FAKE_SERVER = r'''
import json,sys
mode=sys.argv[1]
def send(value):
 print(json.dumps(value),flush=True)
def finish(text='DYNAMIC_OK'):
 send({'method':'item/completed','params':{'threadId':'thread-1','turnId':'turn-1','item':{'type':'agentMessage','id':'message-1','text':text,'phase':'final_answer'}}})
 send({'method':'thread/tokenUsage/updated','params':{'threadId':'thread-1','turnId':'turn-1','tokenUsage':{'total':{'totalTokens':12},'last':{'totalTokens':12}}}})
 send({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'completed','error':None}}})
for raw in sys.stdin:
 m=json.loads(raw);method=m.get('method');i=m.get('id')
 if method=='initialize':send({'id':i,'result':{'userAgent':'fake'}})
 elif method=='initialized':pass
 elif method=='experimentalFeature/enablement/set':send({'id':i,'result':{}})
 elif method=='account/read':send({'id':i,'result':{'account':None if mode=='nooauth' else {'type':'chatgpt'},'requiresOpenaiAuth':True}})
 elif method=='thread/start':
  p=m['params']
  if p['sandbox']!='read-only' or p['approvalPolicy']!='never' or not p['ephemeral']:raise RuntimeError('unsafe thread config')
  send({'id':i,'result':{'thread':{'id':'thread-1'},'model':'test-model','instructionSources':[]}})
 elif method=='turn/start':
  if m['params']['sandboxPolicy']!={'type':'readOnly','networkAccess':False}:raise RuntimeError('unsafe turn config')
  send({'id':i,'result':{'turn':{'id':'turn-1','status':'inProgress'}}})
  if mode=='approval':send({'id':'approve-1','method':'item/commandExecution/requestApproval','params':{'command':'blocked'}})
  else:send({'id':'tool-1','method':'item/tool/call','params':{'threadId':'thread-1','turnId':'turn-1','callId':'call-1','namespace':None,'tool':'test_echo','arguments':{'message':'hello'}}})
 elif method=='turn/interrupt':
  send({'id':i,'result':{}})
  send({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1','status':'interrupted'}}})
 elif i=='tool-1':
  if not m['result']['success']:raise RuntimeError('tool failed')
  if m['result']['contentItems'][0]['type']!='inputText':raise RuntimeError('wrong protocol output')
  finish()
 elif i=='approve-1':
  if m['result']!={'decision':'decline'}:raise RuntimeError('approval bypass')
  finish('DENIED')
'''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.script = self.root / 'fake_server.py'
        self.script.write_text(FAKE_SERVER)
        self.spec = [{'name': 'test_echo', 'description': 'Echo', 'inputSchema': {'type': 'object', 'properties': {'message': {'type': 'string'}}, 'required': ['message']}}]

    def tearDown(self):
        self.temp.cleanup()

    def argv(self, mode='echo'):
        return patch.object(runtime, '_server_argv', return_value=([sys.executable, '-u', str(self.script), mode], {'scope': 'process-only'}))

    def test_real_stdio_dynamic_round_trip_and_usage(self):
        calls = []
        def handler(name, args):
            calls.append((name, args))
            return {'echo': args['message']}
        with self.argv():
            result = runtime.run_codex(self.root, 'Use test_echo.', self.spec, handler, None, threading.Event(), timeout_seconds=5)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['finalText'], 'DYNAMIC_OK')
        self.assertEqual(result['usage']['total']['totalTokens'], 12)
        self.assertEqual(calls, [('test_echo', {'message': 'hello'})])
        events = [json.loads(line) for line in Path(result['eventsPath']).read_text().splitlines()]
        self.assertTrue(any(event['message'].get('method') == 'item/tool/call' for event in events))
        self.assertTrue(any(event['direction'] == 'client' and event['message'].get('id') == 'tool-1' for event in events))

    def test_oauth_metadata_does_not_block_configured_provider_inference(self):
        with self.argv('nooauth'):
            result = runtime.run_codex(self.root, 'Use test_echo.', self.spec, lambda n, a: a, None, threading.Event(), timeout_seconds=5)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['accountMetadata']['accountPresent'])

    def test_escalation_is_declined_not_approved(self):
        with self.argv('approval'):
            result = runtime.run_codex(self.root, 'Only test.', self.spec, lambda n, a: a, None, threading.Event(), timeout_seconds=5)
        self.assertEqual(result['status'], 'needs_approval')
        self.assertEqual(result['deniedRequests'][0]['method'], 'item/commandExecution/requestApproval')

    def test_timeout_cancels_bound_broker_without_setting_job_cancel(self):
        class Broker:
            def __init__(self):self.stop=threading.Event();self.cancelled=False
            def call(self, name, args):
                self.stop.wait(10)
                return {'stopped':True}
            def cancel_current_call(self):self.cancelled=True;self.stop.set()
        broker=Broker();job_cancel=threading.Event()
        with self.argv():
            result=runtime.run_codex(self.root,'Use test_echo.',self.spec,broker.call,None,job_cancel,timeout_seconds=1)
        self.assertEqual(result['status'],'timeout')
        self.assertTrue(broker.cancelled)
        self.assertFalse(job_cancel.is_set())
        self.assertLess(result['elapsedSeconds'],5)

    def test_screenshot_is_returned_as_image_content(self):
        path=self.root/'shot.png'
        path.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jQ1EAAAAASUVORK5CYII='))
        output=runtime._tool_output({'_imagePath':str(path),'status':'captured'},self.root)
        self.assertEqual(output['contentItems'][1]['type'],'inputImage')
        self.assertTrue(output['contentItems'][1]['imageUrl'].startswith('data:image/png;base64,'))
        self.assertNotIn('_imagePath',output['contentItems'][0]['text'])

    def test_screenshot_cannot_escape_card_directory(self):
        outside=self.root/'outside.png';outside.write_bytes(b'png')
        child=self.root/'card';child.mkdir()
        with self.assertRaises(runtime.CodexRuntimeError):runtime._tool_output({'_imagePath':str(outside)},child)

    def test_tool_whitelist_rejects_builtin_and_duplicate_names(self):
        for specs in ([{'name':'exec_command','inputSchema':{}}],self.spec+self.spec):
            with self.assertRaises(runtime.CodexRuntimeError):runtime._tool_specs(specs)
        normalized,names=runtime._tool_specs(self.spec)
        self.assertEqual(normalized[0]['type'],'function')
        self.assertEqual(names,{'test_echo'})

    def test_all_approval_variants_deny(self):
        self.assertEqual(runtime._approval_denial('item/permissions/requestApproval'),{'permissions':{},'scope':'turn'})
        self.assertEqual(runtime._approval_denial('mcpServer/elicitation/request'),{'action':'decline'})
        self.assertIn('denied',runtime._approval_denial('execCommandApproval')['decision'])


if __name__=='__main__':unittest.main()
