#!/usr/bin/env python3
"""Apply the narrow CamCore product-identity patch to Open WebUI v0.11.1.

The deployment remains Open WebUI software and keeps its upstream licence and
provenance. This patch changes only the runtime product-name suffix and favicon
URL for the CamCore deployment. It intentionally fails closed if the expected
upstream source block changes so an Open WebUI upgrade cannot silently receive
an unreviewed patch.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_TARGET = Path('/app/backend/open_webui/env.py')

EXPECTED = """# LICENSE covers this Open WebUI branding surface, including name, logo,
# visual, textual, symbolic identifiers, metadata, and surrounding UI.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
WEBUI_NAME = os.getenv('WEBUI_NAME', 'Open WebUI')
if WEBUI_NAME != 'Open WebUI':
    WEBUI_NAME += ' (Open WebUI)'

# LICENSE covers this Open WebUI branding surface, including this favicon
# and any visual, textual, or symbolic identifiers it preserves.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
WEBUI_FAVICON_URL = 'https://openwebui.com/favicon.png'
"""

REPLACEMENT = """# LICENSE covers this Open WebUI branding surface, including name, logo,
# visual, textual, symbolic identifiers, metadata, and surrounding UI.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
WEBUI_NAME = os.getenv('WEBUI_NAME', 'Open WebUI')

# LICENSE covers this Open WebUI branding surface, including this favicon
# and any visual, textual, or symbolic identifiers it preserves.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.
WEBUI_FAVICON_URL = '/static/favicon.png'
"""


def patch(target: Path) -> None:
    if not target.is_file():
        raise SystemExit(f'CamCore branding patch target is missing: {target}')

    source = target.read_text(encoding='utf-8')
    matches = source.count(EXPECTED)
    if matches != 1:
        raise SystemExit(
            'CamCore branding patch refused to run: expected exactly one '
            f'Open WebUI identity block in {target}, found {matches}. '
            'Review the upstream release before changing this guard.'
        )

    patched = source.replace(EXPECTED, REPLACEMENT, 1)
    if "WEBUI_NAME += ' (Open WebUI)'" in patched:
        raise SystemExit('CamCore branding patch verification failed: suffix remains')
    if "WEBUI_FAVICON_URL = '/static/favicon.png'" not in patched:
        raise SystemExit('CamCore branding patch verification failed: local favicon missing')

    target.write_text(patched, encoding='utf-8')


if __name__ == '__main__':
    patch(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET)
