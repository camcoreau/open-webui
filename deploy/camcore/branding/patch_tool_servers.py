#!/usr/bin/env python3
"""Allow trusted global OpenAPI tool servers while local plugins stay disabled.

CamCore deliberately runs Open WebUI with ENABLE_PLUGINS=false so arbitrary
in-process Python tools, filters and pipes are not available. Open WebUI v0.11.0
also gates global OpenAPI tool-server resolution behind that same flag, which
means an otherwise authorised `server:<id>` tool is silently dropped.

This guarded runtime patch narrows that coupling:

* local DB-backed tools remain disabled when ENABLE_PLUGINS=false;
* `server:*` OpenAPI tool IDs are still passed to the existing external-tool
  resolver;
* access control, bearer authentication, TLS verification and tool schema
  handling continue to use Open WebUI's existing implementation.

The patch fails closed if the approved v0.11.0 source blocks drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_TOOLS_TARGET = Path('/app/backend/open_webui/utils/tools.py')
DEFAULT_MIDDLEWARE_TARGET = Path('/app/backend/open_webui/utils/middleware.py')

TOOLS_PLUGIN_GUARD = """    if not ENABLE_PLUGINS:\n        return {}\n\n    if not tool_ids:\n        return {}\n"""

TOOLS_PLUGIN_GUARD_REPLACEMENT = """    if not tool_ids:\n        return {}\n"""

TOOLS_DB_LOOKUP = """    tool_models = await Tools.get_tools_by_ids(tool_ids)\n"""

TOOLS_DB_LOOKUP_REPLACEMENT = """    tool_models = await Tools.get_tools_by_ids(tool_ids) if ENABLE_PLUGINS else {}\n"""

MIDDLEWARE_TOOL_GATE = """                elif ENABLE_PLUGINS:\n                    db_tool_ids.append(tool_id)\n"""

MIDDLEWARE_TOOL_GATE_REPLACEMENT = """                elif tool_id.startswith('server:') or ENABLE_PLUGINS:\n                    # External OpenAPI servers remain available when local plugin execution is disabled.\n                    # Non-server DB tool IDs are still ignored unless ENABLE_PLUGINS is enabled.\n                    db_tool_ids.append(tool_id)\n"""


def replace_once(source: str, expected: str, replacement: str, label: str, target: Path) -> str:
    matches = source.count(expected)
    if matches != 1:
        raise SystemExit(
            f'CamCore OpenAPI patch refused to run: expected exactly one {label} '
            f'block in {target}, found {matches}. Review the upstream release first.'
        )
    return source.replace(expected, replacement, 1)


def patch_tools(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore OpenAPI tools patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    source = replace_once(
        source,
        TOOLS_PLUGIN_GUARD,
        TOOLS_PLUGIN_GUARD_REPLACEMENT,
        'ENABLE_PLUGINS early-return',
        target,
    )
    source = replace_once(
        source,
        TOOLS_DB_LOOKUP,
        TOOLS_DB_LOOKUP_REPLACEMENT,
        'DB tool lookup',
        target,
    )

    if 'if not ENABLE_PLUGINS:\n        return {}' in source:
        raise SystemExit('CamCore OpenAPI patch verification failed: global plugin guard remains')
    if 'Tools.get_tools_by_ids(tool_ids) if ENABLE_PLUGINS else {}' not in source:
        raise SystemExit('CamCore OpenAPI patch verification failed: DB lookup is not gated')

    target.write_text(source, encoding='utf-8')


def patch_middleware(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore OpenAPI middleware patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    source = replace_once(
        source,
        MIDDLEWARE_TOOL_GATE,
        MIDDLEWARE_TOOL_GATE_REPLACEMENT,
        'middleware tool-id gate',
        target,
    )

    if "elif tool_id.startswith('server:') or ENABLE_PLUGINS:" not in source:
        raise SystemExit('CamCore OpenAPI patch verification failed: server tool gate missing')

    target.write_text(source, encoding='utf-8')


def main() -> None:
    tools_target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOOLS_TARGET
    middleware_target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MIDDLEWARE_TARGET
    patch_tools(tools_target)
    patch_middleware(middleware_target)


if __name__ == '__main__':
    main()
