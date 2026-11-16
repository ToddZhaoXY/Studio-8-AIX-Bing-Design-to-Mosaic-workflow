import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine


class EngineTests(unittest.TestCase):
    def test_exact_version_is_per_run_without_global_switch(self):
        args = engine._autopilot_args('v1.3', 'Workspace/Default', Path('/tmp/data.json'), 'literal $(touch surprise); instruction', Path('/tmp/checkpoints'), 'Title', '3x2')
        self.assertIn('--sdl-version', args)
        self.assertEqual(args[args.index('--sdl-version') + 1], 'v1.3')
        self.assertNotIn('--auto-approve', args)
        self.assertEqual(args[args.index('--custom-instructions') + 1], 'literal $(touch surprise); instruction')
        self.assertNotIn('extensions', args)
        for flag in ('--author-model', '--critic-model', '--eval-model'):
            self.assertEqual(args[args.index(flag) + 1], 'gpt-5.6-sol')

    def test_invalid_version_and_identifiers_rejected(self):
        for value in ('../outside', 'x;rm -rf x', 'a/b', ''):
            with self.assertRaises(engine.EngineError):
                engine._identifier(value, 'workspaceId')
        with self.assertRaises(engine.EngineError):
            engine._autopilot_args('v1.5;cmd', 'x', Path('x'), '', Path('x'), '', '3x2')

    def test_secret_redaction_recursive_and_text(self):
        value = engine.redact({'secret': 'danger', 'log': 'Bearer abcdef123', 'nested': [{'access_token': 'token'}]})
        self.assertNotIn('danger', json.dumps(value))
        self.assertNotIn('abcdef123', json.dumps(value))
        self.assertEqual(value['nested'][0]['access_token'], '[REDACTED]')

    def test_json_extraction_ignores_progress_noise(self):
        text = '[progress] working\n{"data":{"templateId":"abc"}}\n'
        self.assertEqual(engine._last_json(text)['data']['templateId'], 'abc')
        self.assertEqual(engine._collect_template_ids(engine._last_json(text)), {'abc'})

    def test_environment_uses_live_availability_and_cli_choices(self):
        def fake(args, root, **kwargs):
            if args == ['status']:
                return {'authenticated': True, 'apiReachable': True, 'version': '1.0', 'apiUrl': engine.PRODUCTION}
            if args == ['extensions', 'current']:
                return {'schemaVersion': 'v1.5'}
            if args == ['extensions', 'list']:
                return [{'id': engine.EXTENSION, 'versions': [
                    {'id': 'v1.3', 'authoring': {'available': True}},
                    {'id': 'v1.4', 'authoring': {'available': False, 'reason': 'unsupported-schema-version'}},
                    {'id': 'v1.5', 'authoring': {'available': True}},
                    {'id': 'v1.6', 'authoring': {'available': False, 'reason': 'feature-disabled'}}]}]
            if args == ['workspaces', 'list']:
                return [{'workspaceId': 'ws-a', 'workspaceName': 'A'}]
            return {'flags': [{'name': '--sdl-version', 'choices': ['v1.3', 'v1.5']}]}
        with patch.object(engine, '_cli_path', return_value='/tmp/mosaic'), patch.object(engine, '_cli_json', side_effect=fake):
            result = engine.get_environment('.')
        versions = {row['id']: row for row in result['versions']}
        self.assertTrue(versions['v1.3']['authoringAvailable'])
        self.assertFalse(versions['v1.4']['authoringAvailable'])
        self.assertEqual(versions['v1.4']['reason'], 'unsupported-schema-version')
        self.assertFalse(versions['v1.6']['authoringAvailable'])

    def test_preview_http_success_is_not_render_success(self):
        self.assertFalse(engine._preview_pass({'status': 'success'}, 'v1.5'))
        self.assertFalse(engine._preview_pass({'isSuccess': True, 'sdl': {'a': 1}, 'schemaVersion': 'v1.3'}, 'v1.5'))
        self.assertTrue(engine._preview_pass({'isSuccess': True, 'sdl': {'a': 1}, 'schemaVersion': 'v1.5', 'diagnostics': []}, 'v1.5'))
        self.assertFalse(engine._contains_validation_pass({'isValid': False, 'savedChecks': {'isValid': True}}))
        self.assertFalse(engine._contains_validation_pass({'isValid': True, 'exact': {'isValid': False}}))
        self.assertFalse(engine._contains_validation_pass({'isValid': True, 'errors': [{'message': 'invalid'}]}))
        self.assertFalse(engine._contains_validation_pass({'validation': {'isValid': True}}))
        self.assertTrue(engine._contains_validation_pass({'isValid': True, 'errors': [], 'validationAvailable': True}))

    def test_cancellation_prevents_launch(self):
        cancel = threading.Event()
        cancel.set()
        with patch.object(engine.subprocess, 'Popen') as launch:
            with self.assertRaises(engine.EngineError) as caught:
                engine._run_cli(['status'], '.', cancel=cancel)
        self.assertEqual(caught.exception.status, 'cancelled')
        launch.assert_not_called()
        with patch.object(engine, '_http_evidence') as fetch:
            with self.assertRaises(engine.EngineError) as assets_error:
                engine._safe_brief_assets({'assets': [{'archivePath': 'image.png'}]}, Path('/tmp/unused'), cancel)
            self.assertEqual(assets_error.exception.status, 'cancelled')
            fetch.assert_not_called()
        with patch.object(engine, '_api') as request:
            with self.assertRaises(engine.EngineError) as verify_error:
                engine._verify_template(Path('.'), Path('/tmp/unused'), 'new', {}, set(), lambda e: None, cancel)
            self.assertEqual(verify_error.exception.status, 'cancelled')
            request.assert_not_called()

    def test_existing_template_cannot_pass_as_new_run(self):
        with self.assertRaisesRegex(engine.EngineError, 'pre-existing'):
            engine._verify_template(Path('.'), Path('/tmp/unused'), 'old', {}, {'old'}, lambda e: None, threading.Event())

    def test_api_does_not_allow_arbitrary_hosts_or_routes(self):
        with self.assertRaises(engine.EngineError):
            engine._api('https://outside.test/anything')
        with self.assertRaises(engine.EngineError):
            engine._api('/api/v2/../../anything')
        with self.assertRaises(engine.EngineError):
            engine._api('/api/v2/templates/old', method='DELETE')

    def test_disabled_version_never_starts_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / 'skill'
            skill.mkdir()
            (skill / 'SKILL.md').write_text('# skill')
            environment = {'cli': {'authenticated': True, 'apiUrl': engine.PRODUCTION}, 'versions': [{'id': 'v1.4', 'authoringAvailable': False, 'reason': 'unsupported-schema-version'}]}
            with patch.object(engine, 'get_environment', return_value=environment), patch.object(engine, '_run_cli') as launch:
                result = engine._run_legacy_autopilot_job(root, root / 'job', {'targetVersion': 'v1.4', 'workspaceId': 'ws-a', 'folderId': 'default'}, [{'selection': {'id': 'test'}}], skill, lambda event: None, threading.Event())
            self.assertEqual(result['status'], 'unsupported_version')
            launch.assert_not_called()
            self.assertTrue((root / 'job/report.json').exists())

    def test_metadata_is_not_renderer_evidence(self):
        self.assertFalse(engine._source_readiness({'sourceEvidence': {'excerpt': '{name:"Card",width:200}'}})[0])
        self.assertTrue(engine._source_readiness({'designTree': {'type': 'Box', 'children': []}})[0])
        self.assertFalse(engine._source_readiness({'designTree': {'type': 'Box'}, 'authoringReadiness': {'canAttempt': False, 'reason': 'reference-only'}})[0])
        self.assertTrue(engine._source_readiness({'authoringReadiness': {'canAttempt': True, 'status': 'source-code-evidence'}})[0])

    def test_existing_template_list_id_variants_are_protected(self):
        self.assertEqual(engine._template_listing_ids([{'id': 'first'}, {'templateId': 'second'}]), {'first', 'second'})
        self.assertEqual(engine._template_listing_ids({'data': [{'id': 'third'}]}), {'third'})

    def test_components_are_extracted_from_tags_not_strings_or_comments(self):
        jsx = '''<Box><Image alt="Literal <NotComponent>" />
        {/* <Wrong /> */}<Tabs.Panel><Text value={'<NotATag>'} /></Tabs.Panel>
        <Image src={photo} /></Box>'''
        self.assertEqual(engine._jsx_component_counts(jsx), {'Box': 1, 'Image': 2, 'Tabs.Panel': 1, 'Text': 1})

    def test_component_evidence_distinguishes_pre_and_post_generation_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            refs = root / 'references'
            refs.mkdir()
            (refs / 'Image-schema.json').write_text(json.dumps({'name': 'Image', 'schemaSetId': 'v1.5'}))
            (refs / 'live-guides-and-examples.json').write_text(json.dumps({'get_component_guide:1': {'text': '# Image Guide — schema v1.5'}}))
            with patch.object(engine, '_cli_json', return_value={'name': 'Box', 'schemaSetId': 'v1.5'}):
                result = engine._component_usage(root, root, '<Box><Image /></Box>', 'v1.5', threading.Event())
            records = {row['name']: row for row in result['componentEvidence']}
            self.assertEqual(records['Image']['schemaReadPhase'], 'before-generation')
            self.assertEqual(records['Image']['guideStatus'], 'read')
            self.assertEqual(records['Box']['schemaReadPhase'], 'after-generation')
            self.assertEqual(records['Box']['guideStatus'], 'not-read')
            self.assertEqual(result['usedComponents'], ['Box', 'Image'])

    def test_inline_context_preserves_source_and_actual_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = {'selection': {'id': 'single', 'width': 200}, 'designTree': {'style': {'borderRadius': 16}},
                      'sourceEvidence': {'excerpt': 'const exactCtor = () => originalTree;'}, 'assets': []}
            refs = [{'file': 'Image-schema.json', 'content': {'name': 'Image', 'schemaSetId': 'v1.5', 'props': ['exactProp']}},
                    {'file': 'live-guides-and-examples.json', 'content': {'get_component_guide:1': {'text': '# Image Guide exact body'},
                                                                       'skill_search-card-rules:2': {'text': 'Complete native rules\n### Search Card Reference Examples\nunrelated large example'}}},
                    {'file': 'working-example.json', 'content': {'id': 'reference', 'schemaVersion': 'v1.5', 'jsxTemplate': '<Card><Image /></Card>'}}]
            result = engine._inline_design_context(source, [{'url': 'https://source/image.png', 'sha256': 'checked'}], [], refs,
                       [('SKILL.md', 'main skill'), ('references/bing-contract.md', 'complete selected Bing rules')], 'v1.5', root)
            for expected in ('exactCtor', 'borderRadius', 'exactProp', '# Image Guide exact body', '<Card><Image /></Card>', 'complete selected Bing rules', 'https://source/image.png'):
                self.assertIn(expected, result)
            self.assertNotIn('unrelated large example', result)
            coverage = json.loads((root / 'context-coverage.json').read_text())
            self.assertTrue(coverage['sourceContractComplete'])
            self.assertEqual(len(coverage['referenceExcerptSelections']), 1)

    def test_oversize_source_contract_is_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(engine.EngineError) as caught:
                engine._inline_design_context({'designTree': {'source': 'x' * engine.MAX_INLINE_BYTES}}, [], [], [], [('SKILL.md', 'skill')], 'v1.5', Path(temporary))
            self.assertEqual(caught.exception.status, 'needs_context_reduction')

    def test_model_failure_preserves_root_cause(self):
        error = engine._execution_failure({'stderr': 'workflow failed: Model "claude-opus-4.8" is not available', 'stdout': ''})
        self.assertEqual(error.status, 'model_unavailable')
        self.assertIn('claude-opus-4.8', str(error))
        nested = engine._execution_failure({'stderr': '', 'stdout': json.dumps({'data': {'error': 'Request session.create: Model "claude-opus-4.8" is not available.'}})})
        self.assertEqual(nested.status, 'model_unavailable')
        critic = engine._execution_failure({'stderr': '', 'stdout': json.dumps({'error': 'Critic session did not produce a critique_search_card result for iteration 3.'})})
        self.assertEqual(critic.status, 'critic_incomplete')

    def test_partial_save_attribution_uses_notes_not_only_name(self):
        template = {'id': 'new', 'name': 'Library native Single image', 'createdAt': '2026-11-12T06:18:00.4768541+00:00',
                    'iterations': [{'notes': '## WORKBENCH_REPORT\n```json\n{"selectionId":"single"}\n```'}]}
        result = engine._attribution(template, {'namePrefix': 'Library native'}, 'job1', 1, 'single', {'old'}, '2026-11-12T06:11:00+00:00')
        self.assertTrue(result['attributed'])
        self.assertNotIn('createdAtCheck', result)
        self.assertFalse(engine._attribution(template, {'namePrefix': 'Library native'}, 'job1', 1, 'other', {'old'})['attributed'])
        self.assertFalse(engine._attribution(template, {'namePrefix': 'Library native'}, 'job1', 1, 'single', {'new'})['attributed'])
        self.assertFalse(engine._attribution(template, {'namePrefix': 'Wrong'}, 'job1', 1, 'single', set())['attributed'])

    def test_unique_job_item_tag_can_attribute_new_template(self):
        template = {'id': 'new', 'name': 'Library [WB:job1:02] Card', 'iterations': []}
        self.assertTrue(engine._attribution(template, {'namePrefix': 'Library'}, 'job1', 2, 'single', set())['attributed'])
        self.assertFalse(engine._attribution(template, {'namePrefix': 'Library'}, 'job1', 1, 'single', set())['attributed'])

    def test_agent_exact_icon_and_scores_remain_unverified(self):
        with tempfile.TemporaryDirectory() as temporary:
            item = {'selectionId': 'single', 'differences': []}
            notes = '## WORKBENCH_REPORT\n' + json.dumps({'selectionId': 'single', 'icons': {'status': 'exact', 'reason': 'Agent says looks fine'}, 'validation': {'targetHostVisual': 'pass'}}) + '\n[Hillclimb card score: 100]'
            verified = {'notes': notes, 'validation': {'savedFull': 'pass', 'preview': 'pass', 'targetHostVisual': 'not-tested'}}
            engine._merge_agent_report(item, verified, Path(temporary))
            self.assertEqual(item['agentReportedIcons']['status'], 'exact')
            self.assertEqual(item['icons']['status'], 'unverified')
            self.assertEqual(item['validation']['targetHostVisual'], 'not-tested')
            self.assertEqual(item['scoring']['status'], 'unverified')

    def test_readonly_recovery_never_moves_wrong_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            template = {'id': 'new', 'currentIteration': 1, 'iterations': [{'iteration': 1, 'schemaVersion': 'v1.5', 'jsxTemplate': '<Box />', 'schema': '{}', 'schemaData': '{}'}]}
            request = {'targetVersion': 'v1.5', 'workspaceId': 'ws-a', 'folderId': 'default'}
            with patch.object(engine, '_cli_json', return_value=template), patch.object(engine, '_component_usage', return_value={}), patch.object(engine, '_api', return_value=[]) as api:
                with self.assertRaises(engine.EngineError) as caught:
                    engine._verify_template(Path(temporary), Path(temporary), 'new', request, set(), lambda e: None, threading.Event(), allow_placement=False)
            self.assertEqual(caught.exception.status, 'needs_placement')
            self.assertTrue(all(call.kwargs.get('method', 'GET') == 'GET' for call in api.call_args_list))

    def test_manual_observation_overrides_duplicate_area_and_icon_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'review').mkdir()
            review = {'templateId': 'new', 'iteration': 3, 'findings': [{'area': 'moreAction', 'reason': 'Observed missing gallery'}, {'area': 'iconRuntime', 'reason': 'Observed placeholder'}],
                      'observations': {'iconVisual': 'failed comparison'}, 'iconDiscovery': {'schemaVersion': 'v1.5', 'nativeExactMatch': 'not-established'}}
            (root / 'review/visual-review.json').write_text(json.dumps(review))
            item = {'templateId': 'new', 'iteration': 3, 'agentReportedIcons': {'status': 'exact'}, 'differences': [{'area': 'canvas'}, {'area': 'moreAction', 'evidenceLevel': 'agent-reported'}]}
            engine._apply_manual_review(root, item)
            self.assertEqual(sum(row['area'] == 'moreAction' for row in item['differences']), 1)
            self.assertEqual(item['icons']['status'], 'failed')
            self.assertIn('已查v1.5 Icon枚举', item['icons']['reason'])
            self.assertEqual(item['agentReportedIcons']['status'], 'exact')


if __name__ == '__main__':
    unittest.main()
