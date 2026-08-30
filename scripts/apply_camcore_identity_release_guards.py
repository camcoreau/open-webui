#!/usr/bin/env python3
"""Apply CamCore identity defaults and fork-safe publishing controls."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

EXPECTED = {
    "deploy/camcore/compose.yaml": "4e1ec281bf3f7ad8ca1a34b927de6969613f675d",
    ".github/workflows/release-pypi.yml": "9995ccedae0c241b000074d92b1baf8232efa67a",
    ".github/workflows/docker.yaml": "f14afd6a584366bf3b62ca1ecfc5f506f35dab00",
}


def sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # noqa: S324


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_compose(text: str) -> str:
    marker = """\n\n      # Dedicated Microsoft Entra sign-in. Local account and password paths are off."""
    insert = """\n\n      # Canonical CamCore identity and interpretation rules. This is a default system
      # instruction for chats that do not have a more-specific approved model prompt.
      DEFAULT_INTERFACE_SETTINGS: >-
        {"system":"You are Jarvis, the authorised operational assistant for CamCore — Cameron Family Secure Network. CamCore is Jayden Cameron's privately operated hybrid infrastructure and digital-services environment. Jarvis provides visibility, diagnostics, documentation support and explicitly authorised assistance; it does not own CamCore or independently manage or change the environment. For health reports, use exact observation times and source names. Treat integration failures as visibility gaps unless service impact is independently confirmed. When sources conflict, state the discrepancy and lower confidence. Distinguish host from guest utilisation and avoid double counting, service failure from integration failure, and failed from cancelled or optional release workflows. Treat Microsoft 365 advisory-backed degradation as provider-side unless tenant evidence confirms local impact. Do not infer Synology hardware, pool, SMART, RAID or UPS health from API discovery. Treat qBittorrent firewalled status behind a VPN without port forwarding as informational unless transfer evidence confirms impact. Declare RED only for a direct evidence-backed critical condition or confirmed outage."}

      # Dedicated Microsoft Entra sign-in. Local account and password paths are off."""
    return once(text, marker, insert, "CamCore default system context")


def patch_pypi(text: str) -> str:
    text = once(
        text,
        """on:
  push:
    branches:
      - main # or whatever branch you want to use
      - pypi-release
""",
        """# Publishing is intentionally disabled in the CamCore fork unless the repository
# variable CAMCORE_ENABLE_PYPI_PUBLISH is explicitly set to true and the PyPI
# trusted-publisher identity is configured for this exact repository/workflow/environment.
on:
  workflow_dispatch:
""",
        "PyPI trigger",
    )
    return once(
        text,
        """jobs:
  release:
    runs-on: ubuntu-latest""",
        """jobs:
  release:
    if: ${{ vars.CAMCORE_ENABLE_PYPI_PUBLISH == 'true' }}
    runs-on: ubuntu-latest""",
        "PyPI repository-variable guard",
    )


def patch_docker(text: str) -> str:
    text = once(
        text,
        """    if: ${{ !cancelled() && needs.merge.result == 'success' && (github.ref == 'refs/heads/dev' || startsWith(github.ref, 'refs/tags/v')) }}""",
        """    if: ${{ vars.CAMCORE_ENABLE_HELM_NOTIFY == 'true' && !cancelled() && needs.merge.result == 'success' && (github.ref == 'refs/heads/dev' || startsWith(github.ref, 'refs/tags/v')) }}""",
        "Helm notification guard",
    )
    return once(
        text,
        """    if: ${{ !cancelled() && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')) }}""",
        """    if: ${{ vars.CAMCORE_ENABLE_DOCKERHUB_PUBLISH == 'true' && !cancelled() && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')) }}""",
        "Docker Hub publishing guard",
    )


PATCHERS = {
    "deploy/camcore/compose.yaml": patch_compose,
    ".github/workflows/release-pypi.yml": patch_pypi,
    ".github/workflows/docker.yaml": patch_docker,
}


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    for relative, expected in EXPECTED.items():
        path = root / relative
        data = path.read_bytes()
        actual = sha(data)
        if actual != expected:
            raise RuntimeError(
                f"revision mismatch: {relative}: expected {expected}, found {actual}"
            )
        path.write_text(PATCHERS[relative](data.decode()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
