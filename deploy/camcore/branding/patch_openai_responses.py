#!/usr/bin/env python3
"""Harden Open WebUI's stateless OpenAI Responses tool continuation.

Open WebUI stores the standard reasoning setting as the Chat Completions field
``reasoning_effort``. Responses requests instead need ``reasoning.effort`` and,
when context is managed statelessly, the completed encrypted reasoning item must
be replayed before the matching function output.

This CamCore patch makes four deliberately narrow changes to the approved
Open WebUI v0.11.1 runtime:

* translate ``reasoning_effort`` without overriding explicit Responses options;
* force private stateless requests and request ``reasoning.encrypted_content`` once;
* carry the provider-native output sequence through the internal tool loop; and
* remove that internal replay metadata before Chat Completions requests.

Every replacement is exact-match guarded and idempotent. A partially patched or
drifted upstream source is rejected so a new Open WebUI release must be reviewed
before CamCore changes the runtime again.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_ROUTER_TARGET = Path('/app/backend/open_webui/routers/openai.py')
DEFAULT_MIDDLEWARE_TARGET = Path('/app/backend/open_webui/utils/middleware.py')

ROUTER_FIELDS_EXPECTED = """# Fields accepted by the Responses API for each input item type.
RESPONSES_ALLOWED_FIELDS: dict[str, set[str]] = {
    'message': {'type', 'role', 'content'},
    'function_call': {'type', 'call_id', 'name', 'arguments', 'id'},
    'function_call_output': {'type', 'call_id', 'output'},
}


def _normalize_stored_item(item: dict) -> dict:
    \"\"\"Strip local-only fields from a stored output item before replaying it.

    Open WebUI stores extra bookkeeping fields (``id``, ``status``,
    ``started_at``, ``ended_at``, ``duration``, ``_tag_type``,
    ``attributes``, ``summary``, etc.) that the Responses API does
    not accept.  This helper returns a copy containing only the
    fields the API understands.
    \"\"\"
    item_type = item.get('type', '')
    allowed = RESPONSES_ALLOWED_FIELDS.get(item_type)
    if allowed is None:
        # Unknown type — pass through as-is (e.g. reasoning, extension items).
        return item
    return {k: v for k, v in item.items() if k in allowed}
"""

ROUTER_FIELDS_REPLACEMENT = """# Provider fields accepted when replaying Responses output as input.
CAMCORE_RESPONSES_REPLAY_FIELD = '_camcore_responses_replay'
RESPONSES_ALLOWED_FIELDS: dict[str, set[str]] = {
    'reasoning': {'id', 'type', 'summary', 'content', 'encrypted_content', 'status'},
    'message': {'id', 'type', 'role', 'content', 'status', 'phase'},
    'function_call': {
        'id',
        'type',
        'call_id',
        'name',
        'arguments',
        'caller',
        'namespace',
        'status',
    },
    'function_call_output': {
        'id',
        'type',
        'call_id',
        'output',
        'caller',
        'name',
        'namespace',
        'status',
    },
}
RESPONSES_ITEM_STATUSES = {'in_progress', 'completed', 'incomplete'}
RESPONSES_UI_ONLY_FIELDS = {
    'started_at',
    'ended_at',
    'duration',
    '_tag_type',
    'attributes',
    'files',
    'embeds',
    'start_tag',
    'end_tag',
    'reasoning_details',
}


def _is_trailing_empty_ui_placeholder(item: dict) -> bool:
    if (
        item.get('type') != 'message'
        or item.get('role') != 'assistant'
        or item.get('status') != 'in_progress'
    ):
        return False

    content = item.get('content', [])
    return (
        isinstance(content, list)
        and len(content) == 1
        and content[0].get('type') == 'output_text'
        and not content[0].get('text', '').strip()
    )


def _normalize_stored_item(item: dict) -> dict | None:
    \"\"\"Return provider input fields while removing Open WebUI bookkeeping.\"\"\"
    if not isinstance(item, dict):
        return None

    item_type = item.get('type', '')
    if item_type.startswith('open_webui:'):
        return None

    allowed = RESPONSES_ALLOWED_FIELDS.get(item_type)
    if allowed is not None:
        normalized = {key: value for key, value in item.items() if key in allowed}
        if normalized.get('status') not in RESPONSES_ITEM_STATUSES:
            normalized.pop('status', None)
        return normalized

    # Preserve future provider-native item types, but never replay UI metadata.
    return {key: value for key, value in item.items() if key not in RESPONSES_UI_ONLY_FIELDS}


def _normalize_stored_output(stored_output: list) -> list[dict]:
    items = list(stored_output)
    if items and isinstance(items[-1], dict) and _is_trailing_empty_ui_placeholder(items[-1]):
        items.pop()

    normalized_items = []
    for item in items:
        normalized = _normalize_stored_item(item)
        if normalized:
            normalized_items.append(normalized)
    return normalized_items


def _strip_camcore_responses_replay_for_chat(payload: dict) -> dict:
    \"\"\"Remove internal replay fields while preserving Chat Completions messages.\"\"\"
    messages = payload.get('messages')
    if not isinstance(messages, list):
        return payload

    cleaned_messages = []
    for message in messages:
        if isinstance(message, dict) and message.get(CAMCORE_RESPONSES_REPLAY_FIELD):
            message = dict(message)
            message.pop(CAMCORE_RESPONSES_REPLAY_FIELD, None)
            message.pop('output', None)
        cleaned_messages.append(message)

    payload['messages'] = cleaned_messages
    return payload
"""

ROUTER_STORED_EXPECTED = """        # Check for stored output items (from previous Responses API turn)
        stored_output = msg.get('output')
        if stored_output and isinstance(stored_output, list):
            input_items.extend(_normalize_stored_item(item) for item in stored_output)
            continue
"""

ROUTER_STORED_REPLACEMENT = """        # Reuse completed provider output for a stateless tool continuation.
        # Later flattened messages are Chat Completions compatibility duplicates.
        replay_action = msg.get(CAMCORE_RESPONSES_REPLAY_FIELD)
        if replay_action == 'skip':
            continue
        if replay_action == 'output' and message_index != latest_replay_index:
            continue

        stored_output = msg.get('output')
        if stored_output and isinstance(stored_output, list):
            input_items.extend(_normalize_stored_output(stored_output))
            continue
"""

ROUTER_LOOP_EXPECTED = """    for msg in messages:
        role = msg.get('role', 'user')
"""

ROUTER_LOOP_REPLACEMENT = """    # Each internal continuation carries cumulative output. Replaying only the
    # newest marked message prevents earlier tool iterations from being duplicated.
    latest_replay_index = next(
        (
            index
            for index in range(len(messages) - 1, -1, -1)
            if isinstance(messages[index], dict)
            and messages[index].get(CAMCORE_RESPONSES_REPLAY_FIELD) == 'output'
        ),
        None,
    )

    for message_index, msg in enumerate(messages):
        role = msg.get('role', 'user')
"""

ROUTER_PAYLOAD_EXPECTED = """    responses_payload = {**payload, 'input': input_items}

    # Forward previous_response_id when the middleware has set it
"""

ROUTER_PAYLOAD_REPLACEMENT = """    responses_payload = {**payload, 'input': input_items}

    # The standard model setting uses the Chat Completions field name. The
    # Responses API expects the same value nested under reasoning.effort.
    reasoning_effort = responses_payload.pop('reasoning_effort', None)
    if reasoning_effort is not None:
        reasoning = responses_payload.get('reasoning')
        if reasoning is None:
            responses_payload['reasoning'] = {'effort': reasoning_effort}
        elif isinstance(reasoning, dict) and 'effort' not in reasoning:
            responses_payload['reasoning'] = {**reasoning, 'effort': reasoning_effort}

    # CamCore manages context by replaying output and must not retain Responses.
    responses_payload['store'] = False

    # Preserve caller-requested includes and add opaque reasoning exactly once.
    include = responses_payload.get('include')
    if include is None:
        include = []
    elif not isinstance(include, list):
        raise ValueError('Responses include must be a list')
    else:
        include = list(include)
    if 'reasoning.encrypted_content' not in include:
        include.append('reasoning.encrypted_content')
    responses_payload['include'] = include

    # Forward previous_response_id when the middleware has set it
"""

ROUTER_CHAT_EXPECTED = """    is_responses = api_config.get('api_type') == 'responses'

    if api_config.get('azure') or api_config.get('provider') == 'azure':
"""

ROUTER_CHAT_REPLACEMENT = """    is_responses = api_config.get('api_type') == 'responses'

    # The middleware adds native Responses output alongside the existing
    # flattened tool messages. Chat Completions must receive the exact flattened
    # messages it did before this patch, without any internal replay metadata.
    if not is_responses:
        payload = _strip_camcore_responses_replay_for_chat(payload)

    if api_config.get('azure') or api_config.get('provider') == 'azure':
"""

MIDDLEWARE_HELPER_EXPECTED = """def output_id(prefix: str) -> str:
    \"\"\"Generate OR-style ID: prefix + 24-char hex UUID.\"\"\"
    return f'{prefix}_{uuid4().hex[:24]}'


"""

MIDDLEWARE_HELPER_REPLACEMENT = """def output_id(prefix: str) -> str:
    \"\"\"Generate OR-style ID: prefix + 24-char hex UUID.\"\"\"
    return f'{prefix}_{uuid4().hex[:24]}'


def _camcore_function_call_linkage(output: list[dict], call_id: str) -> dict:
    \"\"\"Copy provider linkage from the matching native function call.\"\"\"
    function_call = next(
        (
            item
            for item in reversed(output)
            if isinstance(item, dict)
            and item.get('type') == 'function_call'
            and item.get('call_id') == call_id
        ),
        None,
    )
    if function_call is None:
        return {}

    return {
        field: function_call[field]
        for field in ('caller', 'name', 'namespace')
        if field in function_call
    }


def _attach_camcore_responses_replay(tool_messages: list[dict], output: list[dict]) -> list[dict]:
    \"\"\"Carry native output through the provider-agnostic internal tool loop.\"\"\"
    if not tool_messages or not output:
        return tool_messages

    replay_output = list(output)
    if replay_output:
        trailing = replay_output[-1]
        trailing_content = trailing.get('content', []) if isinstance(trailing, dict) else []
        if (
            isinstance(trailing, dict)
            and trailing.get('type') == 'message'
            and trailing.get('role') == 'assistant'
            and trailing.get('status') == 'in_progress'
            and isinstance(trailing_content, list)
            and len(trailing_content) == 1
            and trailing_content[0].get('type') == 'output_text'
            and not trailing_content[0].get('text', '').strip()
        ):
            replay_output.pop()

    if not replay_output:
        return tool_messages

    replay_index = next(
        (
            index
            for index, message in enumerate(tool_messages)
            if isinstance(message, dict) and message.get('role') == 'assistant'
        ),
        None,
    )
    if replay_index is None:
        return tool_messages

    marked_messages = []
    for index, message in enumerate(tool_messages):
        if not isinstance(message, dict):
            marked_messages.append(message)
            continue

        marked_message = dict(message)
        if index == replay_index:
            marked_message['output'] = replay_output
            marked_message['_camcore_responses_replay'] = 'output'
        else:
            # Native output already contains the matching function_call_output.
            marked_message['_camcore_responses_replay'] = 'skip'
        marked_messages.append(marked_message)

    return marked_messages


"""

MIDDLEWARE_CONTINUATION_EXPECTED = """                            tool_messages = convert_output_to_messages(
                                output,
                                raw=True,
                                reasoning_format=get_reasoning_format(model),
                                flatten_tool_images=True,
                            )

                            # Chat Completions providers don't support multimodal
"""

MIDDLEWARE_CONTINUATION_REPLACEMENT = """                            tool_messages = convert_output_to_messages(
                                output,
                                raw=True,
                                reasoning_format=get_reasoning_format(model),
                                flatten_tool_images=True,
                            )
                            if responses_stream_seen:
                                tool_messages = _attach_camcore_responses_replay(tool_messages, full_output())

                            # Chat Completions providers don't support multimodal
"""

MIDDLEWARE_STATE_EXPECTED = """            last_response_id = None

            def full_output():
"""

MIDDLEWARE_STATE_REPLACEMENT = """            last_response_id = None
            responses_stream_seen = False

            def full_output():
"""

MIDDLEWARE_NONLOCAL_EXPECTED = """                    nonlocal output
                    nonlocal prior_output
                    nonlocal last_response_id

                    response_tool_calls = []
"""

MIDDLEWARE_NONLOCAL_REPLACEMENT = """                    nonlocal output
                    nonlocal prior_output
                    nonlocal last_response_id
                    nonlocal responses_stream_seen

                    response_tool_calls = []
"""

MIDDLEWARE_EVENT_EXPECTED = """                                elif data.get('type', '').startswith('response.'):
"""

MIDDLEWARE_EVENT_REPLACEMENT = """                                elif data.get('type', '').startswith('response.'):
                                    responses_stream_seen = True
"""

MIDDLEWARE_IMAGE_EXPECTED = """                            if image_urls:
                                new_form_data['messages'].append(
"""

MIDDLEWARE_IMAGE_REPLACEMENT = """                            if image_urls and not responses_stream_seen:
                                new_form_data['messages'].append(
"""

MIDDLEWARE_STATEFUL_EXPECTED = """                        if ENABLE_RESPONSES_API_STATEFUL and last_response_id:
"""

MIDDLEWARE_STATEFUL_REPLACEMENT = """                        if (
                            ENABLE_RESPONSES_API_STATEFUL
                            and last_response_id
                            and not responses_stream_seen
                        ):
"""

MIDDLEWARE_FUNCTION_OUTPUT_EXPECTED = """                                'call_id': result.get('tool_call_id', ''),
                                'output': output_parts,
"""

MIDDLEWARE_FUNCTION_OUTPUT_REPLACEMENT = """                                'call_id': result.get('tool_call_id', ''),
                                **_camcore_function_call_linkage(
                                    output, result.get('tool_call_id', '')
                                ),
                                'output': output_parts,
"""

MIDDLEWARE_NATIVE_TOOL_CALLS_EXPECTED = """                        if responses_api_tool_calls:
                            tool_calls.append(_split_tool_calls(responses_api_tool_calls))
"""

MIDDLEWARE_NATIVE_TOOL_CALLS_REPLACEMENT = """                        if responses_api_tool_calls:
                            # Provider-native call IDs must remain paired with replayed output.
                            tool_calls.append(responses_api_tool_calls)
"""


def replace_guarded(source: str, expected: str, replacement: str, label: str, target: Path) -> str:
    expected_matches = source.count(expected)
    replacement_matches = source.count(replacement)
    if expected_matches == 1 and replacement_matches == 0:
        return source.replace(expected, replacement, 1)
    if replacement_matches == 1 and expected_matches == replacement.count(expected):
        return source
    raise SystemExit(
        f'CamCore Responses patch refused to run: expected one unpatched or one '
        f'patched {label} block in {target}, found {expected_matches} unpatched '
        f'and {replacement_matches} patched. Review the upstream release first.'
    )


def patch_router(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore Responses router patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    for expected, replacement, label in (
        (ROUTER_FIELDS_EXPECTED, ROUTER_FIELDS_REPLACEMENT, 'stored-output schema'),
        (ROUTER_LOOP_EXPECTED, ROUTER_LOOP_REPLACEMENT, 'message replay selection'),
        (ROUTER_STORED_EXPECTED, ROUTER_STORED_REPLACEMENT, 'stored-output conversion'),
        (ROUTER_PAYLOAD_EXPECTED, ROUTER_PAYLOAD_REPLACEMENT, 'Responses payload'),
        (ROUTER_CHAT_EXPECTED, ROUTER_CHAT_REPLACEMENT, 'Chat Completions cleanup'),
    ):
        source = replace_guarded(source, expected, replacement, label, target)

    required = (
        "responses_payload.pop('reasoning_effort', None)",
        "responses_payload['store'] = False",
        "include.append('reasoning.encrypted_content')",
        "'encrypted_content'",
        "'phase'",
        'latest_replay_index',
        "replay_action == 'skip'",
        '_strip_camcore_responses_replay_for_chat(payload)',
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f'CamCore Responses router patch verification failed: missing {missing}')

    target.write_text(source, encoding='utf-8')


def patch_middleware(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore Responses middleware patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    source = replace_guarded(
        source,
        MIDDLEWARE_HELPER_EXPECTED,
        MIDDLEWARE_HELPER_REPLACEMENT,
        'middleware replay helper',
        target,
    )
    source = replace_guarded(
        source,
        MIDDLEWARE_CONTINUATION_EXPECTED,
        MIDDLEWARE_CONTINUATION_REPLACEMENT,
        'stateless tool continuation',
        target,
    )
    for expected, replacement, label in (
        (MIDDLEWARE_STATE_EXPECTED, MIDDLEWARE_STATE_REPLACEMENT, 'Responses stream state'),
        (MIDDLEWARE_NONLOCAL_EXPECTED, MIDDLEWARE_NONLOCAL_REPLACEMENT, 'Responses stream nonlocal'),
        (MIDDLEWARE_EVENT_EXPECTED, MIDDLEWARE_EVENT_REPLACEMENT, 'Responses stream detection'),
        (MIDDLEWARE_IMAGE_EXPECTED, MIDDLEWARE_IMAGE_REPLACEMENT, 'tool image compatibility copy'),
        (MIDDLEWARE_STATEFUL_EXPECTED, MIDDLEWARE_STATEFUL_REPLACEMENT, 'stateful continuation guard'),
        (
            MIDDLEWARE_FUNCTION_OUTPUT_EXPECTED,
            MIDDLEWARE_FUNCTION_OUTPUT_REPLACEMENT,
            'function-call-output linkage',
        ),
        (
            MIDDLEWARE_NATIVE_TOOL_CALLS_EXPECTED,
            MIDDLEWARE_NATIVE_TOOL_CALLS_REPLACEMENT,
            'provider-native tool-call identity',
        ),
    ):
        source = replace_guarded(source, expected, replacement, label, target)

    required = (
        'def _attach_camcore_responses_replay',
        'def _camcore_function_call_linkage',
        "marked_message['output'] = replay_output",
        "marked_message['_camcore_responses_replay'] = 'skip'",
        'responses_stream_seen = False',
        'responses_stream_seen = True',
        '_attach_camcore_responses_replay(tool_messages, full_output())',
        'if image_urls and not responses_stream_seen:',
        'and not responses_stream_seen',
        '**_camcore_function_call_linkage(',
        'tool_calls.append(responses_api_tool_calls)',
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f'CamCore Responses middleware patch verification failed: missing {missing}')

    target.write_text(source, encoding='utf-8')


def patch(router_target: Path, middleware_target: Path | None = None) -> None:
    patch_router(router_target)
    if middleware_target is not None:
        patch_middleware(middleware_target)


def main() -> None:
    router_target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROUTER_TARGET
    middleware_target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MIDDLEWARE_TARGET
    patch(router_target, middleware_target)


if __name__ == '__main__':
    main()
