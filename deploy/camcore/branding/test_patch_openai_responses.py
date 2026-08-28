#!/usr/bin/env python3
"""Behavior tests for the CamCore OpenAI Responses compatibility patch."""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path

from patch_openai_responses import patch

SOURCE = Path(os.environ.get('CAMCORE_OPENAI_SOURCE', 'backend/open_webui/routers/openai.py'))


def load_converter(source: str):
    tree = ast.parse(source)
    converter = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'convert_to_responses_payload'
    )
    namespace: dict = {}
    exec(compile(ast.Module(body=[converter], type_ignores=[]), '<responses-converter>', 'exec'), namespace)
    return namespace['convert_to_responses_payload']


class ResponsesPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SOURCE.is_file(), f'missing source fixture: {SOURCE}')
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'openai.py'
            target.write_text(SOURCE.read_text(encoding='utf-8'), encoding='utf-8')
            patch(target)
            self.converter = load_converter(target.read_text(encoding='utf-8'))

    def test_translates_standard_reasoning_effort(self) -> None:
        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [{'role': 'user', 'content': 'Check CamCore health'}],
                'reasoning_effort': 'medium',
                'tools': [
                    {
                        'type': 'function',
                        'function': {
                            'name': 'health_check',
                            'description': 'Check service health',
                            'parameters': {'type': 'object', 'properties': {}},
                        },
                    }
                ],
            }
        )

        self.assertNotIn('reasoning_effort', result)
        self.assertEqual(result['reasoning'], {'effort': 'medium'})
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
            {
                'model': 'gpt-5.6-luna',
                'messages': [{'role': 'user', 'content': 'Check CamCore health'}],
                'reasoning_effort': 'low',
                'reasoning': {'effort': 'high', 'summary': 'auto'},
            }
        )

        self.assertNotIn('reasoning_effort', result)
        self.assertEqual(result['reasoning'], {'effort': 'high', 'summary': 'auto'})

    def test_merges_effort_with_other_nested_reasoning_options(self) -> None:
        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [{'role': 'user', 'content': 'Check CamCore health'}],
                'reasoning_effort': 'medium',
                'reasoning': {'summary': 'auto'},
            }
        )

        self.assertEqual(result['reasoning'], {'summary': 'auto', 'effort': 'medium'})

    def test_leaves_reasoning_unset_when_model_setting_is_unset(self) -> None:
        result = self.converter(
            {
                'model': 'gpt-5.6-luna',
                'messages': [{'role': 'user', 'content': 'Check CamCore health'}],
            }
        )

        self.assertNotIn('reasoning_effort', result)
        self.assertNotIn('reasoning', result)

    def test_refuses_unreviewed_upstream_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'openai.py'
            target.write_text('def convert_to_responses_payload():\n    pass\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                patch(target)


if __name__ == '__main__':
    unittest.main()
