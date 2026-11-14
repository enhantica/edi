"""Real browser event windows use the same authored and generated assets as the website."""

import shutil
import subprocess

import pytest

from tests.integration.py.test_preferences_and_survey import DOCS, ROOT, survey


@pytest.mark.parametrize(
    'instant',
    [
        '2030-05-09T23:59:59Z',
        '2030-05-10T00:00:00Z',
        '2030-05-11T12:00:00Z',
        '2030-05-12T23:59:59Z',
        '2030-05-13T00:00:00Z',
    ],
)
def test_survey_event_windows_in_browser(instant, tmp_path, monkeypatch):
    survey()
    files = list(DOCS.rglob('*events*.json'))
    assert len(files) == 1, 'Survey events must be declared in one file'
    pages = list(DOCS.glob('about/**/survey*.md'))
    staged = tmp_path / 'docs'
    for path in [pages[0], files[0], *DOCS.rglob('*.js')]:
        target = staged / path.relative_to(DOCS)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(DOCS.parent / 'mkdocs.yml', staged.parent / 'mkdocs.yml')
    from tests.integration.py.test_tutorial_docs_presentation import site_module  # noqa: PLC0415

    site_module('build', monkeypatch)._write_feedback_form(staged)
    result = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/survey/events.mjs'),
            str(staged),
            str(pages[0].relative_to(DOCS)),
            str(staged / files[0].relative_to(DOCS)),
            instant,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'The real survey combobox must enforce active event dates: ' + result.stderr
    )
