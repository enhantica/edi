"""Real browser event windows use the same authored and generated assets as the website."""

import json
import queue
import shutil
import subprocess
import threading

import pytest

from tests.fixtures.node_runtime import environment_node
from tests.integration.py.test_preferences_and_survey import DOCS, ROOT, survey


@pytest.fixture(scope='module')
def survey_browser(tmp_path_factory):
    # Share browser/Node startup only; each request runs every assertion on a fresh context/page.
    stderr_path = tmp_path_factory.mktemp('survey-browser') / 'stderr.log'
    with stderr_path.open('w+') as stderr:
        process = subprocess.Popen(
            [str(environment_node()), str(ROOT / 'tests/fixtures/survey/browser.mjs')],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
        )

        replies = queue.Queue()

        def read_replies():
            for line in process.stdout:
                replies.put(line)
            replies.put(None)

        reader = threading.Thread(target=read_replies, daemon=True)
        reader.start()

        def receive(timeout):
            try:
                line = replies.get(timeout=timeout)
            except queue.Empty:
                pytest.fail('The real survey worker must answer within its bounded request time')
            assert line, (
                'The real survey worker must publish a response; startup stderr: '
                + stderr_path.read_text()
            )
            return json.loads(line)

        def observe(root, page, events, instant):
            process.stdin.write(
                json.dumps({
                    'root': str(root),
                    'pagePath': str(page),
                    'eventPath': str(events),
                    'instant': instant,
                })
                + '\n'
            )
            process.stdin.flush()
            response = receive(20)
            assert set(response) == {'instant', 'ok', 'error'}, (
                'Every real-browser response must carry its exact request identity and outcome'
            )
            assert response['instant'] == instant and type(response['ok']) is bool, (
                'The browser must execute this supplied date rather than reuse another result'
            )
            return response

        startup_ready = False
        try:
            assert receive(10) == {'ready': True}, (
                'The shared real browser must complete startup before any date witness'
            )
            startup_ready = True
            yield observe
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=5)
            assert not reader.is_alive(), (
                'The browser response reader must finish after its worker exits'
            )
            process.stdout.close()
            if startup_ready:
                assert process.returncode == 0, (
                    'The shared browser must shut down cleanly after its cases'
                )


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
@pytest.mark.parametrize('surface', ['authored', 'generated'])
def test_survey_event_windows_in_browser(instant, surface, survey_browser, tmp_path, monkeypatch):
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
    root = DOCS if surface == 'authored' else staged
    result = survey_browser(
        root, pages[0].relative_to(DOCS), root / files[0].relative_to(DOCS), instant
    )
    assert result['ok'], (
        'The real survey combobox must enforce active event dates: ' + result['error']
    )
