# SPDX-License-Identifier: BSD-3-Clause
"""The installers' optional assistant components and which of them public artifacts carry.

One component per provider (edi ADR-0108). Claude is distributed only once enhantica's
acceptance of Anthropic's Commercial Terms is recorded, and GitHub Copilot only once its input
opens and its component fits the download site: until then data/distribution.json sets
claude_distribution and copilot_distribution to "internal", and the offline installers, the
component repositories, their publication and the installer pages all leave that provider out.
Each of them asks here.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHATGPT_COMPONENT = 'org.easydiffraction.app.assistant'
CLAUDE_COMPONENT = 'org.easydiffraction.app.claude'
COPILOT_COMPONENT = 'org.easydiffraction.app.copilot'
ASSISTANT_COMPONENTS = (CHATGPT_COMPONENT, CLAUDE_COMPONENT, COPILOT_COMPONENT)
# The data/distribution.json setting that holds each provider back; ChatGPT has none.
DISTRIBUTION_SETTINGS = {
    CLAUDE_COMPONENT: 'claude_distribution',
    COPILOT_COMPONENT: 'copilot_distribution',
}


def component_distributed(component: str) -> bool:
    """Whether public installers and repositories may carry this assistant component."""
    setting = DISTRIBUTION_SETTINGS.get(component)
    if setting is None:
        return component in ASSISTANT_COMPONENTS
    policy = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    value = policy.get(setting)
    if value not in {'internal', 'public'}:
        raise RuntimeError(f'data/distribution.json must set {setting}')
    return value == 'public'


def claude_distributed() -> bool:
    """Whether public installers and repositories may carry Claude."""
    return component_distributed(CLAUDE_COMPONENT)


def copilot_distributed() -> bool:
    """Whether public installers and repositories may carry GitHub Copilot."""
    return component_distributed(COPILOT_COMPONENT)


def distributed_assistants(*, internal: bool = False) -> tuple[str, ...]:
    """The assistant components an installer or repository carries; internal builds carry all."""
    return tuple(name for name in ASSISTANT_COMPONENTS if internal or component_distributed(name))
