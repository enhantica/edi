"""Keep the auxiliary guide and case-owned tutorial inventory in sync."""

import json
from pathlib import Path

from contract import cases_for

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def build():
    cases = cases_for('app')
    required = ['interface', *cases]
    app = json.loads((HERE / 'app-tutorials.json').read_text())
    app['source'] = 'The Interface tour and one built-in tutorial per declared app case.'
    app['required'] = required
    app.pop('legacy', None)
    app['auxiliary'] = {'interface': 'Interface tour'}
    presentation = json.loads((HERE / 'presentation.json').read_text())
    presentation['builtins'] = {'interface': 'Interface tour'}
    onboarding_path = ROOT / 'tests/fixtures/onboarding/contracts.json'
    onboarding = json.loads(onboarding_path.read_text())
    onboarding['tutorial_manifest']['ids'] = required
    onboarding['tutorial_manifest']['step_fields'] = ['text', 'target']
    for path, value in [
        (HERE / 'app-tutorials.json', app),
        (HERE / 'presentation.json', presentation),
        (onboarding_path, onboarding),
    ]:
        path.write_text(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    build()
