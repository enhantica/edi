"""Live acceptance actors must reach their intended scientific input before assertions."""

import re
from pathlib import Path

from tests.integration.py.test_example_catalogue import app_cases

ROOT = Path(__file__).resolve().parents[3]
IDENTITY = r'([a-z0-9-]+_[a-z0-9_-]+)'
QUOTED = r"""["']""" + IDENTITY + r"""["']"""
CALLS = (
    r'\bopen_example\s*\(\s*' + QUOTED,
    r'(?:\.|->)openExample\s*\(\s*' + QUOTED,
    r'Examples\.bundled\s*\([^,]+,\s*[^,]+,\s*' + QUOTED,
    r'openExampleRow\s*\(\s*' + QUOTED,
    r'hot\s*\(\s*["\'][^"\']+["\']\s*,\s*' + QUOTED,
    r'["\']bundle["\']\s*,\s*' + QUOTED,
)


def requests(source):
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.DOTALL)
    found = {identity for pattern in CALLS for identity in re.findall(pattern, source)}
    for row in re.findall(r'\{[^{}]*\bexample\s*:[^{}]*\}', source):
        if not re.search(r'\bfixture\s*:\s*true\b', row):
            found.update(re.findall(r'\bexample\s*:\s*' + QUOTED, row))
    for assignment in re.findall(r'\bconst\s+exampleId\s*=[^;]+;', source):
        found.update(re.findall(QUOTED, assignment))
    return found


def test_live_actors_request_only_bundled_example_ids():
    bundled = set(app_cases(ROOT))
    assert bundled, 'Catalogue precondition: the independent registry declares bundled cases'
    removed = 'pd-neut-cwl_cosio-d20_start-1'
    plants = (
        f'open_example("{removed}")',
        f'Session.openExample("{removed}")',
        f'session->openExample("{removed}")',
        f'Examples.bundled(this, Session, "{removed}")',
        f"await openExampleRow('{removed}', /cosio/)",
        f"harness.invoke('bundle', '{removed}', destination)",
        f'hot("line-segment", "{removed}", true)',
        f'const cases = [{{example: "{removed}", count: 1}}]',
        f"const exampleId = ncaf ? '{removed}' : 'pd-neut-cwl_lbco-hrpt';",
    )
    for plant in plants:
        assert removed in requests(plant) - bundled, (
            'Catalogue precondition: literal and indirect QML, native, Python and browser '
            'requests for a removed example must fail before their behavioural assertions'
        )
    assert not requests(f'Examples.fixture(Session, "{removed}")'), (
        'Catalogue precondition: a retained fixture uses the file-project boundary'
    )
    assert not requests(f'const rows = [{{example: "{removed}", fixture: true}}]'), (
        'Catalogue precondition: indirect retained inputs explicitly declare their fixture route'
    )
    violations = {}
    paths = [*(ROOT / 'tests').rglob('*'), ROOT / 'app/src/demo_driver.cpp']
    for path in paths:
        if path.suffix not in {'.qml', '.cpp', '.js', '.mjs', '.py'} or path == Path(__file__):
            continue
        missing = requests(path.read_text()) - bundled
        if missing:
            violations[str(path.relative_to(ROOT))] = sorted(missing)
    assert not violations, (
        'Catalogue precondition: live actors must select a bundled id or explicitly open '
        f'a retained fixture through its file-project route: {violations}'
    )
