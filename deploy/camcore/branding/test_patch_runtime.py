#!/usr/bin/env python3
"""Behavior tests for the CamCore Open WebUI v0.11.1 identity patch."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from patch_runtime import EXPECTED, REPLACEMENT, patch

SOURCE = Path(os.environ['CAMCORE_ENV_SOURCE']) if 'CAMCORE_ENV_SOURCE' in os.environ else None

LICENSE_NOTICES = (
    """# LICENSE covers this Open WebUI branding surface, including name, logo,
# visual, textual, symbolic identifiers, metadata, and surrounding UI.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.""",
    """# LICENSE covers this Open WebUI branding surface, including this favicon
# and any visual, textual, or symbolic identifiers it preserves.
# Do not alter, remove, obscure, or replace it except as LICENSE permits:
# https://docs.openwebui.com/license.""",
)


class RuntimePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        if SOURCE is None:
            self.source = EXPECTED
        else:
            self.assertTrue(SOURCE.is_file(), f'missing source fixture: {SOURCE}')
            self.source = SOURCE.read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'env.py'
            target.write_text(self.source, encoding='utf-8')
            patch(target)
            self.patched = target.read_text(encoding='utf-8')

    def test_changes_only_the_reviewed_identity_block(self) -> None:
        self.assertEqual(self.source.count(EXPECTED), 1)
        self.assertEqual(self.patched, self.source.replace(EXPECTED, REPLACEMENT, 1))

    def test_removes_suffix_and_uses_local_favicon(self) -> None:
        self.assertNotIn("WEBUI_NAME += ' (Open WebUI)'", self.patched)
        self.assertIn("WEBUI_FAVICON_URL = '/static/favicon.png'", self.patched)

    def test_preserves_upstream_license_notices(self) -> None:
        for notice in LICENSE_NOTICES:
            self.assertEqual(self.source.count(notice), 1)
            self.assertEqual(self.patched.count(notice), 1)

    def test_refuses_unreviewed_upstream_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'env.py'
            target.write_text("WEBUI_NAME = 'changed upstream'\n", encoding='utf-8')
            with self.assertRaises(SystemExit):
                patch(target)


if __name__ == '__main__':
    unittest.main()
