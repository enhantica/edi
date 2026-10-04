# SPDX-License-Identifier: BSD-3-Clause
"""Repo-root conftest.

Exists so the repository root is on `sys.path` for plugin resolution: the autoloaded runtime fit
policy lives at `tools/testing/fit_policy.py`, and a conftest under `tests/` puts only `tests/` on
the path. Registered here rather than imported so the entry-point wrappers are installed before
any test module binds a bare reference to one.
"""

from __future__ import annotations

# Invariant I20: actual-entry-point sentinels in BOTH repos; this is edi's half.
pytest_plugins = ('tools.testing.fit_policy',)
