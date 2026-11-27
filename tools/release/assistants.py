# SPDX-License-Identifier: BSD-3-Clause
"""The installers' optional assistant components and which of them public artifacts carry.

One component per provider (edi ADR-0108). Claude is distributed only once enhantica's
acceptance of Anthropic's Commercial Terms is recorded: until then data/distribution.json sets
claude_distribution to "internal", and the offline installers, the component repositories, their
publication and the installer pages all leave Claude out. Each of them asks here.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHATGPT_COMPONENT = 'org.easydiffraction.app.assistant'
CLAUDE_COMPONENT = 'org.easydiffraction.app.claude'
COPILOT_COMPONENT = 'org.easydiffraction.app.copilot'
ASSISTANT_COMPONENTS = (CHATGPT_COMPONENT, CLAUDE_COMPONENT, COPILOT_COMPONENT)


def claude_distributed() -> bool:
    """Whether public installers and repositories may carry Claude."""
    policy = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    value = policy.get('claude_distribution')
    if value not in {'internal', 'public'}:
        raise RuntimeError('data/distribution.json must set claude_distribution')
    return value == 'public'


def distributed_assistants(*, internal: bool = False) -> tuple[str, ...]:
    """The assistant components an installer or repository carries; internal builds add Claude."""
    return tuple(
        name
        for name in ASSISTANT_COMPONENTS
        if name != CLAUDE_COMPONENT or internal or claude_distributed()
    )
