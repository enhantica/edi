# SPDX-License-Identifier: BSD-3-Clause
"""easydiffraction: edi's public module name, ``import easydiffraction as edi`` (ADR-0079).

The same module object as ``edi``, so the two names never load the compiled extension twice.
"""

import sys

import edi

sys.modules[__name__] = edi
