#!/usr/bin/env python3
"""Behavior tests for the CamCore OpenAPI tool-server patch.

The patched ``get_tools`` is extracted from the fixture source and executed
against small stand-ins for Open WebUI's models and helpers, so the tests prove
the runtime behaviour the Dockerfile relies on rather than only the text of the
replacement blocks.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from patch_tool_servers import (
    MIDDLEWARE_TOOL_GATE,
    MIDDLEWARE_TOOL_GATE_REPLACEMENT,
    TOOLS_DB_LOOKUP,
    TOOLS_DB_LOOKUP_REPLACEMENT,
    TOOLS_PLUGIN_GUARD,
    TOOLS_PLUGIN_GUARD_REPLACEMENT,
    patch_middleware,
    patch_tools,
)

TOOLS_SOURCE = Path(os.environ.get('CAMCORE_TOOLS_SOURCE', 'backend/open_webui/utils/tools.py'))
MIDDLEWARE_SOURCE = Path(os.environ.get('CAMCORE_MIDDLEWARE_SOURCE', 'backend/open_webui/utils/middleware.py'))

SERVER_ID = 'camcore-operations'
SERVER_TOOL_ID = f'server:{SERVER_ID}'
LOCAL_TOOL_ID = 'local-python-tool'


class AsyncRecorder:
    """Awaitable stand-in that records its calls and returns a fixed result."""

    def __init__(self, result=None):
        self.calls = []
        self.result = result

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def extract_get_tools(source: str, namespace: dict):
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'get_tools']
    if len(selected) != 1:
        raise AssertionError('expected exactly one get_tools definition in the patched source')
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<patched-tools>', 'exec'), namespace)
    return namespace['get_tools']


class ToolServerPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(TOOLS_SOURCE.is_file(), f'missing source fixture: {TOOLS_SOURCE}')
        self.assertTrue(MIDDLEWARE_SOURCE.is_file(), f'missing source fixture: {MIDDLEWARE_SOURCE}')

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        temp_path = Path(self.temp_dir.name)
        self.tools_target = temp_path / 'tools.py'
        self.middleware_target = temp_path / 'middleware.py'
        self.tools_source = TOOLS_SOURCE.read_text(encoding='utf-8')
        self.middleware_source = MIDDLEWARE_SOURCE.read_text(encoding='utf-8')
        self.tools_target.write_text(self.tools_source, encoding='utf-8')
        self.middleware_target.write_text(self.middleware_source, encoding='utf-8')
        patch_tools(self.tools_target)
        patch_middleware(self.middleware_target)
        self.patched_tools = self.tools_target.read_text(encoding='utf-8')
        self.patched_middleware = self.middleware_target.read_text(encoding='utf-8')

    def runtime(self, *, enable_plugins: bool, access_granted: bool = True, servers=None):
        """Build the patched get_tools with recorded stand-ins for its collaborators."""
        warnings = []
        tools_lookup = AsyncRecorder({})
        server = {
            'id': SERVER_ID,
            'idx': 0,
            'url': 'https://ai-tools.camcore.network',
            'specs': [
                {
                    'name': 'get_camcore_health',
                    'description': 'Read the CamCore health summary.',
                    'parameters': {'type': 'object', 'properties': {}},
                }
            ],
        }
        connection = {'config': {'function_name_filter_list': ''}}

        async def passthrough(function, extra_params):
            return function

        namespace = {
            'ENABLE_PLUGINS': enable_plugins,
            'BYPASS_ADMIN_ACCESS_CONTROL': False,
            'Request': object,
            'UserModel': object,
            'log': SimpleNamespace(
                warning=lambda message, *args: warnings.append(message),
                debug=lambda *args, **kwargs: None,
            ),
            'Groups': SimpleNamespace(get_groups_by_member_id=AsyncRecorder([])),
            'Tools': SimpleNamespace(get_tools_by_ids=tools_lookup),
            'AccessGrants': SimpleNamespace(has_access=AsyncRecorder(False)),
            'Config': SimpleNamespace(get=AsyncRecorder([connection])),
            'get_tool_servers': AsyncRecorder([server] if servers is None else servers),
            'has_connection_access': AsyncRecorder(access_granted),
            'is_string_allowed': lambda name, allowed: True,
            'build_tool_server_headers': AsyncRecorder(({}, {})),
            'execute_tool_server': AsyncRecorder(None),
            'get_async_tool_function_and_apply_extra_params': passthrough,
            'clean_openai_tool_schema': lambda spec: spec,
        }
        get_tools = extract_get_tools(self.patched_tools, namespace)
        request = object()
        user = SimpleNamespace(id='user-1', role='user')
        extra_params = {'__user__': {'id': 'user-1'}, '__metadata__': {}}

        def resolve(tool_ids):
            return asyncio.run(get_tools(request, tool_ids, user, extra_params))

        return SimpleNamespace(resolve=resolve, tools_lookup=tools_lookup, warnings=warnings)

    def test_changes_only_the_reviewed_blocks(self) -> None:
        for expected in (TOOLS_PLUGIN_GUARD, TOOLS_DB_LOOKUP):
            self.assertEqual(self.tools_source.count(expected), 1)
        self.assertEqual(self.middleware_source.count(MIDDLEWARE_TOOL_GATE), 1)

        expected_tools = self.tools_source.replace(TOOLS_PLUGIN_GUARD, TOOLS_PLUGIN_GUARD_REPLACEMENT, 1)
        expected_tools = expected_tools.replace(TOOLS_DB_LOOKUP, TOOLS_DB_LOOKUP_REPLACEMENT, 1)
        self.assertEqual(self.patched_tools, expected_tools)
        self.assertEqual(
            self.patched_middleware,
            self.middleware_source.replace(MIDDLEWARE_TOOL_GATE, MIDDLEWARE_TOOL_GATE_REPLACEMENT, 1),
        )

    def test_server_tools_resolve_without_db_lookup_when_plugins_are_disabled(self) -> None:
        runtime = self.runtime(enable_plugins=False)

        tools = runtime.resolve([SERVER_TOOL_ID, LOCAL_TOOL_ID])

        self.assertEqual(list(tools), ['get_camcore_health'])
        self.assertEqual(tools['get_camcore_health']['tool_id'], SERVER_TOOL_ID)
        self.assertEqual(tools['get_camcore_health']['type'], 'external')
        self.assertEqual(runtime.tools_lookup.calls, [], 'DB tool lookup must not run while ENABLE_PLUGINS is false')
        self.assertEqual(runtime.warnings, [])

    def test_local_tool_ids_stay_inert_when_plugins_are_disabled(self) -> None:
        runtime = self.runtime(enable_plugins=False)

        self.assertEqual(runtime.resolve([LOCAL_TOOL_ID]), {})
        self.assertEqual(runtime.tools_lookup.calls, [])

    def test_tool_server_access_control_still_applies(self) -> None:
        runtime = self.runtime(enable_plugins=False, access_granted=False)

        self.assertEqual(runtime.resolve([SERVER_TOOL_ID]), {})
        self.assertTrue(any('Access denied to tool server' in message for message in runtime.warnings))

    def test_unknown_tool_server_is_skipped(self) -> None:
        runtime = self.runtime(enable_plugins=False, servers=[])

        self.assertEqual(runtime.resolve([SERVER_TOOL_ID]), {})
        self.assertTrue(any('Tool server data not found' in message for message in runtime.warnings))

    def test_db_lookup_runs_when_plugins_are_enabled(self) -> None:
        runtime = self.runtime(enable_plugins=True)

        runtime.resolve([SERVER_TOOL_ID, LOCAL_TOOL_ID])

        self.assertEqual(runtime.tools_lookup.calls, [(([SERVER_TOOL_ID, LOCAL_TOOL_ID],), {})])

    def test_empty_tool_ids_short_circuit(self) -> None:
        runtime = self.runtime(enable_plugins=False)

        self.assertEqual(runtime.resolve([]), {})
        self.assertEqual(runtime.tools_lookup.calls, [])

    def test_middleware_admits_server_ids_only_while_plugins_are_disabled(self) -> None:
        self.assertEqual(self.patched_middleware.count(MIDDLEWARE_TOOL_GATE_REPLACEMENT), 1)
        self.assertNotIn(MIDDLEWARE_TOOL_GATE, self.patched_middleware)

        match = re.search(r"elif (tool_id\.startswith\('server:'\) or ENABLE_PLUGINS):\n", self.patched_middleware)
        self.assertIsNotNone(match)
        gate = match.group(1)
        for tool_id, enable_plugins, admitted in (
            (SERVER_TOOL_ID, False, True),
            (LOCAL_TOOL_ID, False, False),
            (LOCAL_TOOL_ID, True, True),
        ):
            self.assertIs(eval(gate, {}, {'tool_id': tool_id, 'ENABLE_PLUGINS': enable_plugins}), admitted)

    def test_refuses_unreviewed_upstream_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = Path(temp_dir) / 'tools.py'
            middleware = Path(temp_dir) / 'middleware.py'
            tools.write_text('async def get_tools():\n    return {}\n', encoding='utf-8')
            middleware.write_text('db_tool_ids = []\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                patch_tools(tools)
            with self.assertRaises(SystemExit):
                patch_middleware(middleware)

    def test_fails_closed_on_an_already_patched_source(self) -> None:
        with self.assertRaises(SystemExit):
            patch_tools(self.tools_target)
        with self.assertRaises(SystemExit):
            patch_middleware(self.middleware_target)
        self.assertEqual(self.tools_target.read_text(encoding='utf-8'), self.patched_tools)
        self.assertEqual(self.middleware_target.read_text(encoding='utf-8'), self.patched_middleware)


if __name__ == '__main__':
    unittest.main()
