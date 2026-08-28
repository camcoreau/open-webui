#!/usr/bin/env python3
"""Translate Open WebUI reasoning effort for the OpenAI Responses API.

Open WebUI v0.11.0 stores the standard model setting as the Chat Completions
field ``reasoning_effort``. When a managed connection uses the Responses API,
OpenAI instead expects ``reasoning: {"effort": ...}``. Without this narrow
translation, GPT-5.6 requests that combine reasoning and function tools fail.

The patch fails closed if the approved v0.11.0 source block drifts. An explicit
nested ``reasoning.effort`` value wins over the compatibility field.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_TARGET = Path('/app/backend/open_webui/routers/openai.py')

EXPECTED = """    responses_payload = {**payload, 'input': input_items}

    # Forward previous_response_id when the middleware has set it
"""

REPLACEMENT = """    responses_payload = {**payload, 'input': input_items}

    # The standard model setting uses the Chat Completions field name. The
    # Responses API expects the same value nested under reasoning.effort.
    reasoning_effort = responses_payload.pop('reasoning_effort', None)
    if reasoning_effort is not None:
        reasoning = responses_payload.get('reasoning')
        if reasoning is None:
            responses_payload['reasoning'] = {'effort': reasoning_effort}
        elif isinstance(reasoning, dict) and 'effort' not in reasoning:
            responses_payload['reasoning'] = {**reasoning, 'effort': reasoning_effort}

    # Forward previous_response_id when the middleware has set it
"""


def patch(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore Responses patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    matches = source.count(EXPECTED)
    if matches != 1:
        raise SystemExit(
            'CamCore Responses patch refused to run: expected exactly one '
            f'Responses payload block in {target}, found {matches}. '
            'Review the upstream release before changing this guard.'
        )

    patched = source.replace(EXPECTED, REPLACEMENT, 1)
    if "responses_payload.pop('reasoning_effort', None)" not in patched:
        raise SystemExit('CamCore Responses patch verification failed: translation missing')
    if "responses_payload['reasoning'] = {'effort': reasoning_effort}" not in patched:
        raise SystemExit('CamCore Responses patch verification failed: nested effort missing')

    target.write_text(patched, encoding='utf-8')


if __name__ == '__main__':
    patch(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET)
