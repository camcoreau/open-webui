#!/usr/bin/env python3
"""Behavior tests for the CamCore OpenAI Responses compatibility patch."""

from __future__ import annotations

import ast
import copy
import os
import tempfile
import unittest
from pathlib import Path

from patch_openai_responses import patch, patch_middleware

ROUTER_SOURCE = Path(os.environ.get('CAMCORE_OPENAI_SOURCE', 'backend/open_webui/routers/openai.py'))
MIDDLEWARE_SOURCE = Path(os.environ.get('CAMCORE_MIDDLEWARE_SOURCE', 'backend/open_webui/utils/middleware.py'))


def load_symbols(source: str, names: set[str]) -> dict:
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        node_name = node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
        if node_name in names:
            selected.append(node)
            continue
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names for target in node.targets
        ):
            selected.append(node)
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            selected.append(node)

    namespace: dict = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<patched-source>', 'exec'), namespace)
    return namespace


class ResponsesPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(ROUTER_SOURCE.is_file(), f'missing source fixture: {ROUTER_SOURCE}')
        self.assertTrue(MIDDLEWARE_SOURCE.is_file(), f'missing source fixture: {MIDDLEWARE_SOURCE}')

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        temp_path = Path(self.temp_dir.name)
        self.router_target = temp_path / 'openai.py'
        self.middleware_target = temp_path / 'middleware.py'
        self.router_target.write_text(ROUTER_SOURCE.read_text(encoding='utf-8'), encoding='utf-8')
        self.middleware_target.write_text(MIDDLEWARE_SOURCE.read_text(encoding='utf-8'), encoding='utf-8')
        patch(self.router_target, self.middleware_target)

        self.router_source = self.router_target.read_text(encoding='utf-8')
        self.middleware_source = self.middleware_target.read_text(encoding='utf-8')
        router = load_symbols(
            self.router_source,
            {
                'CAMCORE_RESPONSES_REPLAY_FIELD',
                'RESPONSES_ALLOWED_FIELDS',
                'RESPONSES_ITEM_STATUSES',
                'RESPONSES_UI_ONLY_FIELDS',
                '_is_trailing_empty_ui_placeholder',
                '_normalize_stored_item',
                '_normalize_stored_output',
                '_strip_camcore_responses_replay_for_chat',
                'convert_to_responses_payload',
            },
        )
        middleware = load_symbols(
            self.middleware_source,
            {'_attach_camcore_responses_replay', '_camcore_function_call_linkage'},
        )
        self.converter = router['convert_to_responses_payload']
        self.clean_chat_payload = router['_strip_camcore_responses_replay_for_chat']
        self.attach_replay = middleware['_attach_camcore_responses_replay']
        self.function_call_linkage = middleware['_camcore_function_call_linkage']

        self.assertIn('if image_urls and not responses_stream_seen:', self.middleware_source)
        self.assertIn('and not responses_stream_seen', self.middleware_source)
        self.assertIn('**_camcore_function_call_linkage(', self.middleware_source)
        self.assertIn('tool_calls.append(responses_api_tool_calls)', self.middleware_source)

    def basic_payload(self, **extra) -> dict:
        return {
            'model': 'gpt-5.6-luna',
            'messages': [{'role': 'user', 'content': 'Check CamCore health'}],
            **extra,
        }

    def test_translates_standard_reasoning_effort_and_forces_stateless_privacy(self) -> None:
        result = self.converter(
            self.basic_payload(
                reasoning_effort='medium',
                tools=[
                    {
                        'type': 'function',
                        'function': {
                            'name': 'health_check',
                            'description': 'Check service health',
                            'parameters': {'type': 'object', 'properties': {}},
                        },
                    }
                ],
            )
        )

        self.assertNotIn('reasoning_effort', result)
        self.assertEqual(result['reasoning'], {'effort': 'medium'})
        self.assertIs(result['store'], False)
        self.assertEqual(result['include'], ['reasoning.encrypted_content'])
        self.assertEqual(
            result['input'],
            [
                {
                    'type': 'message',
                    'role': 'user',
                    'content': [{'type': 'input_text', 'text': 'Check CamCore health'}],
                }
            ],
        )
        self.assertEqual(result['tools'][0]['name'], 'health_check')

    def test_preserves_explicit_nested_reasoning_effort(self) -> None:
        result = self.converter(
            self.basic_payload(
                reasoning_effort='low',
                reasoning={'effort': 'high', 'summary': 'auto'},
            )
        )

        self.assertNotIn('reasoning_effort', result)
        self.assertEqual(result['reasoning'], {'effort': 'high', 'summary': 'auto'})

    def test_merges_effort_with_other_nested_reasoning_options(self) -> None:
        result = self.converter(
            self.basic_payload(
                reasoning_effort='medium',
                reasoning={'summary': 'auto'},
            )
        )

        self.assertEqual(result['reasoning'], {'summary': 'auto', 'effort': 'medium'})

    def test_leaves_reasoning_unset_when_model_setting_is_unset(self) -> None:
        result = self.converter(self.basic_payload())

        self.assertNotIn('reasoning_effort', result)
        self.assertNotIn('reasoning', result)

    def test_preserves_include_order_and_appends_encrypted_reasoning_once(self) -> None:
        result = self.converter(
            self.basic_payload(include=['file_search_call.results', 'message.output_text.logprobs'])
        )

        self.assertEqual(
            result['include'],
            [
                'file_search_call.results',
                'message.output_text.logprobs',
                'reasoning.encrypted_content',
            ],
        )

        already_included = self.converter(
            self.basic_payload(include=['file_search_call.results', 'reasoning.encrypted_content'])
        )
        self.assertEqual(
            already_included['include'],
            ['file_search_call.results', 'reasoning.encrypted_content'],
        )
        self.assertEqual(already_included['include'].count('reasoning.encrypted_content'), 1)

    def test_rejects_malformed_non_list_include(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Responses include must be a list'):
            self.converter(self.basic_payload(include='reasoning.encrypted_content'))

    def test_replays_ordered_native_output_and_appends_function_output_once(self) -> None:
        reasoning = {
            'id': 'rs_1',
            'type': 'reasoning',
            'status': 'completed',
            'summary': [],
            'content': [],
            'encrypted_content': 'opaque-reasoning',
            'started_at': 1,
            'ended_at': 2,
            'duration': 1,
            '_tag_type': 'reasoning',
            'attributes': {'ui': True},
        }
        message = {
            'id': 'msg_commentary',
            'type': 'message',
            'status': 'completed',
            'role': 'assistant',
            'phase': 'commentary',
            'content': [{'type': 'output_text', 'text': 'Checking CamCore.'}],
            'started_at': 3,
            'attributes': {'ui': True},
        }
        function_call = {
            'id': 'fc_1',
            'type': 'function_call',
            'status': 'completed',
            'call_id': 'call_health',
            'name': 'health_check',
            'arguments': '{"service":"camcore"}',
            'caller': {'type': 'direct'},
            'namespace': 'camcore',
            'duration': 4,
            'files': ['ui-only'],
        }
        function_output = {
            'id': 'fco_local',
            'type': 'function_call_output',
            'status': 'completed',
            'call_id': 'call_health',
            'output': [
                {'type': 'input_text', 'text': '{"status":"healthy"}'},
                {'type': 'input_image', 'image_url': 'data:image/png;base64,AA=='},
            ],
            'caller': {'type': 'direct'},
            'name': 'health_check',
            'namespace': 'camcore',
            'files': ['ui-only'],
            'embeds': ['ui-only'],
        }
        placeholder = {
            'id': 'msg_placeholder',
            'type': 'message',
            'status': 'in_progress',
            'role': 'assistant',
            'content': [{'type': 'output_text', 'text': ''}],
            'started_at': 5,
        }

        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [
                    {'role': 'user', 'content': 'Check CamCore health'},
                    {
                        'role': 'assistant',
                        'content': '',
                        'tool_calls': [
                            {
                                'id': 'call_health',
                                'type': 'function',
                                'function': {
                                    'name': 'health_check',
                                    'arguments': '{"service":"camcore"}',
                                },
                            }
                        ],
                        'output': [reasoning, message, function_call, function_output, placeholder],
                        '_camcore_responses_replay': 'output',
                    },
                    {
                        'role': 'tool',
                        'tool_call_id': 'call_health',
                        'content': '{"status":"healthy"}',
                        '_camcore_responses_replay': 'skip',
                    },
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': 'Tool image compatibility copy'},
                            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AA=='}},
                        ],
                        '_camcore_responses_replay': 'skip',
                    },
                ],
            }
        )

        self.assertEqual(
            result['input'],
            [
                {
                    'type': 'message',
                    'role': 'user',
                    'content': [{'type': 'input_text', 'text': 'Check CamCore health'}],
                },
                {
                    'id': 'rs_1',
                    'type': 'reasoning',
                    'status': 'completed',
                    'summary': [],
                    'content': [],
                    'encrypted_content': 'opaque-reasoning',
                },
                {
                    'id': 'msg_commentary',
                    'type': 'message',
                    'status': 'completed',
                    'role': 'assistant',
                    'phase': 'commentary',
                    'content': [{'type': 'output_text', 'text': 'Checking CamCore.'}],
                },
                {
                    'id': 'fc_1',
                    'type': 'function_call',
                    'status': 'completed',
                    'call_id': 'call_health',
                    'name': 'health_check',
                    'arguments': '{"service":"camcore"}',
                    'caller': {'type': 'direct'},
                    'namespace': 'camcore',
                },
                {
                    'id': 'fco_local',
                    'type': 'function_call_output',
                    'call_id': 'call_health',
                    'output': [
                        {'type': 'input_text', 'text': '{"status":"healthy"}'},
                        {'type': 'input_image', 'image_url': 'data:image/png;base64,AA=='},
                    ],
                    'caller': {'type': 'direct'},
                    'name': 'health_check',
                    'namespace': 'camcore',
                    'status': 'completed',
                },
            ],
        )

    def test_replays_only_latest_cumulative_internal_output(self) -> None:
        first_items = [
            {
                'id': 'rs_1',
                'type': 'reasoning',
                'status': 'completed',
                'summary': [],
                'encrypted_content': 'opaque-1',
            },
            {
                'id': 'fc_1',
                'type': 'function_call',
                'status': 'completed',
                'call_id': 'call_1',
                'name': 'first_tool',
                'arguments': '{}',
            },
            {
                'id': 'fco_1',
                'type': 'function_call_output',
                'status': 'completed',
                'call_id': 'call_1',
                'output': 'first result',
            },
        ]
        second_items = [
            *first_items,
            {
                'id': 'rs_2',
                'type': 'reasoning',
                'status': 'completed',
                'summary': [],
                'encrypted_content': 'opaque-2',
            },
            {
                'id': 'fc_2',
                'type': 'function_call',
                'status': 'completed',
                'call_id': 'call_2',
                'name': 'second_tool',
                'arguments': '{}',
            },
            {
                'id': 'fco_2',
                'type': 'function_call_output',
                'status': 'completed',
                'call_id': 'call_2',
                'output': 'second result',
            },
        ]

        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [
                    {'role': 'user', 'content': 'Run two checks'},
                    {
                        'role': 'assistant',
                        'content': '',
                        'output': first_items,
                        '_camcore_responses_replay': 'output',
                    },
                    {'role': 'tool', 'content': 'first result', '_camcore_responses_replay': 'skip'},
                    {
                        'role': 'assistant',
                        'content': '',
                        'output': second_items,
                        '_camcore_responses_replay': 'output',
                    },
                    {'role': 'tool', 'content': 'second result', '_camcore_responses_replay': 'skip'},
                ],
            }
        )

        self.assertEqual(
            result['input'][1:],
            second_items,
        )
        self.assertEqual(
            [item.get('id') for item in result['input'] if item.get('id') == 'rs_1'],
            ['rs_1'],
        )

    def test_preserves_only_provider_valid_function_output_status(self) -> None:
        def converted_output(status: str) -> dict:
            result = self.converter(
                {
                    'model': 'gpt-5.6-luna',
                    'messages': [
                        {
                            'role': 'assistant',
                            'content': '',
                            'output': [
                                {
                                    'id': 'fco_1',
                                    'type': 'function_call_output',
                                    'call_id': 'call_1',
                                    'output': 'healthy',
                                    'status': status,
                                }
                            ],
                        }
                    ],
                }
            )
            return result['input'][0]

        self.assertEqual(converted_output('completed')['status'], 'completed')
        invalid_status = converted_output('failed')
        self.assertEqual(invalid_status['id'], 'fco_1')
        self.assertNotIn('status', invalid_status)

    def test_drops_only_a_trailing_empty_placeholder(self) -> None:
        non_trailing_empty = {
            'id': 'msg_provider',
            'type': 'message',
            'status': 'in_progress',
            'role': 'assistant',
            'phase': 'commentary',
            'content': [{'type': 'output_text', 'text': ''}],
        }
        function_call = {
            'id': 'fc_1',
            'type': 'function_call',
            'status': 'completed',
            'call_id': 'call_health',
            'name': 'health_check',
            'arguments': '{}',
        }

        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [
                    {
                        'role': 'assistant',
                        'content': '',
                        'output': [non_trailing_empty, function_call],
                    }
                ],
            }
        )

        self.assertEqual(result['input'], [non_trailing_empty, function_call])

    def test_middleware_attaches_native_replay_and_removes_trailing_placeholder(self) -> None:
        output = [
            {
                'id': 'rs_1',
                'type': 'reasoning',
                'status': 'completed',
                'summary': [],
                'encrypted_content': 'opaque',
            },
            {
                'id': 'fc_1',
                'type': 'function_call',
                'status': 'completed',
                'call_id': 'call_health',
                'name': 'health_check',
                'arguments': '{}',
            },
            {
                'id': 'fco_local',
                'type': 'function_call_output',
                'status': 'completed',
                'call_id': 'call_health',
                'output': [{'type': 'input_text', 'text': 'healthy'}],
            },
            {
                'id': 'msg_placeholder',
                'type': 'message',
                'status': 'in_progress',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': ''}],
            },
        ]
        tool_messages = [
            {
                'role': 'assistant',
                'content': '',
                'tool_calls': [
                    {
                        'id': 'call_health',
                        'type': 'function',
                        'function': {'name': 'health_check', 'arguments': '{}'},
                    }
                ],
            },
            {'role': 'tool', 'tool_call_id': 'call_health', 'content': 'healthy'},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Tool image compatibility copy'},
                    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AA=='}},
                ],
            },
        ]
        original_tool_messages = copy.deepcopy(tool_messages)

        marked = self.attach_replay(tool_messages, output)

        self.assertEqual(marked[0]['output'], output[:-1])
        self.assertEqual(marked[0]['_camcore_responses_replay'], 'output')
        self.assertEqual(marked[1]['_camcore_responses_replay'], 'skip')
        self.assertEqual(marked[2]['_camcore_responses_replay'], 'skip')
        self.assertEqual(tool_messages, original_tool_messages)

        cleaned = self.clean_chat_payload({'messages': marked})
        self.assertEqual(cleaned['messages'], original_tool_messages)

    def test_responses_stream_disables_accidental_stateful_continuation(self) -> None:
        stateful_guard = """                        if (
                            ENABLE_RESPONSES_API_STATEFUL
                            and last_response_id
                            and not responses_stream_seen
                        ):
"""
        self.assertIn(stateful_guard, self.middleware_source)
        self.assertNotIn(
            'if ENABLE_RESPONSES_API_STATEFUL and last_response_id:',
            self.middleware_source,
        )

    def test_local_function_output_copies_program_caller_linkage(self) -> None:
        provider_output = [
            {
                'id': 'fc_program',
                'type': 'function_call',
                'status': 'completed',
                'call_id': 'call_program',
                'name': 'run_program_tool',
                'arguments': '{}',
                'caller': {'type': 'program', 'caller_id': 'prog_42'},
                'namespace': 'camcore.program',
            }
        ]

        linkage = self.function_call_linkage(provider_output, 'call_program')
        local_output = {
            'type': 'function_call_output',
            'id': 'fco_local',
            'call_id': 'call_program',
            **linkage,
            'output': [{'type': 'input_text', 'text': 'healthy'}],
            'status': 'completed',
        }

        self.assertEqual(
            local_output,
            {
                'type': 'function_call_output',
                'id': 'fco_local',
                'call_id': 'call_program',
                'caller': {'type': 'program', 'caller_id': 'prog_42'},
                'name': 'run_program_tool',
                'namespace': 'camcore.program',
                'output': [{'type': 'input_text', 'text': 'healthy'}],
                'status': 'completed',
            },
        )
        self.assertEqual(self.function_call_linkage(provider_output, 'missing'), {})

    def test_chat_cleanup_golden_preserves_plain_parallel_tool_and_image_messages(self) -> None:
        golden_messages = [
            {'role': 'user', 'content': 'Run both checks'},
            {'role': 'assistant', 'content': 'I will run both checks.'},
            {
                'role': 'assistant',
                'content': '',
                'tool_calls': [
                    {
                        'id': 'call_1',
                        'type': 'function',
                        'function': {'name': 'first_tool', 'arguments': '{}'},
                    },
                    {
                        'id': 'call_2',
                        'type': 'function',
                        'function': {'name': 'second_tool', 'arguments': '{}'},
                    },
                ],
            },
            {'role': 'tool', 'tool_call_id': 'call_1', 'content': 'first result'},
            {'role': 'tool', 'tool_call_id': 'call_2', 'content': 'second result'},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Tool image compatibility copy'},
                    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AA=='}},
                ],
            },
        ]
        marked_messages = copy.deepcopy(golden_messages)
        marked_messages[2]['output'] = [{'type': 'reasoning', 'encrypted_content': 'opaque'}]
        marked_messages[2]['_camcore_responses_replay'] = 'output'
        for index in (3, 4, 5):
            marked_messages[index]['_camcore_responses_replay'] = 'skip'

        cleaned = self.clean_chat_payload({'model': 'chat-provider', 'messages': marked_messages, 'stream': True})

        self.assertEqual(
            cleaned,
            {'model': 'chat-provider', 'messages': golden_messages, 'stream': True},
        )

    def test_native_responses_tool_call_keeps_original_id_on_malformed_arguments(self) -> None:
        native_call = {
            'id': 'call_provider',
            'index': 0,
            'function': {
                'name': 'health_check',
                'arguments': '{"service":"one"}{"service":"two"}',
            },
        }
        tool_calls = []
        responses_api_tool_calls = [native_call]
        tool_calls.append(responses_api_tool_calls)

        self.assertEqual(tool_calls, [[native_call]])
        self.assertEqual(tool_calls[0][0]['id'], 'call_provider')
        self.assertNotIn(
            'tool_calls.append(_split_tool_calls(responses_api_tool_calls))',
            self.middleware_source,
        )
        self.assertIn(
            'tool_calls.append(_split_tool_calls(response_tool_calls))',
            self.middleware_source,
        )

    def test_patcher_is_idempotent(self) -> None:
        router_before = self.router_target.read_text(encoding='utf-8')
        middleware_before = self.middleware_target.read_text(encoding='utf-8')

        patch(self.router_target, self.middleware_target)

        self.assertEqual(self.router_target.read_text(encoding='utf-8'), router_before)
        self.assertEqual(self.middleware_target.read_text(encoding='utf-8'), middleware_before)

    def test_refuses_unreviewed_router_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'openai.py'
            target.write_text('def convert_to_responses_payload():\n    pass\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                patch(target)

    def test_refuses_unreviewed_middleware_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'middleware.py'
            target.write_text('async def process_chat_response():\n    pass\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                patch_middleware(target)


if __name__ == '__main__':
    unittest.main()
