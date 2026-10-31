"""Native-generated offline HTML keeps open style metadata through real browser rendering."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from tests.integration.py.test_report_html_text import Contents
from tests.integration.py.test_report_option_resolution import external_scripts
from tests.unit.py.test_report_collection_domain import model

from tests.fixtures.report_evolution.observe_browser import observe

ROOT = Path(__file__).resolve().parents[3]
LIBRARIES = {
    'report/vendor/plotly-cartesian-3.7.0.min.js': (
        '7c593b9eda0e74a1d07335cf89cbf7a55ffc114909980c3729af835453bdb02a'
    ),
    'report/vendor/three-0.160.0.module.min.js': (
        '3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6'
    ),
    'report/vendor/three-0.160.0-OrbitControls.js': (
        '5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064'
    ),
}


def library_state():
    return {
        name: hashlib.sha256((ROOT / 'data' / name).read_bytes()).hexdigest() for name in LIBRARIES
    }


def native_html(tmp_path, document):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Native report codec requires the actual built Qt test host'
    source = json.dumps(document, ensure_ascii=True, allow_nan=False)
    (tmp_path / 'input.json').write_text(source, encoding='utf-8')
    before = {
        'runner': str(runner.resolve()),
        'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
        'libraries': library_state(),
        'input_sha256': hashlib.sha256(source.encode()).hexdigest(),
    }
    assert before['libraries'] == LIBRARIES, 'The explicit offline inputs are the pinned libraries'
    case = tmp_path / 'tst_native_report_codec.qml'
    case.write_text(
        'import QtQuick\nimport QtTest\nimport ReportBoundaryAcceptance 1.0\n'
        'TestCase { name: "NativeReportCodec"; when: windowShown; '
        'function test_native_html() { '
        'verify(Qt.isQtObject(BoundaryProof)); '
        'const source = ' + json.dumps(source, ensure_ascii=True) + '; '
        'const html = BoundaryProof.htmlFromJson(source, '
        + json.dumps(str(ROOT / 'data'), ensure_ascii=True)
        + '); verify(typeof html === "string" && html.length > 0); '
        'console.log("E11_REPORT_NATIVE_HTML " + JSON.stringify({html:html, '
        'name:JSON.parse(source).name})); }}\n',
        encoding='utf-8',
    )
    result = subprocess.run(
        [str(runner), '-input', str(case), 'NativeReportCodec::test_native_html', '-o', '-,txt'],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
            'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software'),
        },
    )
    (tmp_path / 'qt.stdout').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'qt.stderr').write_text(result.stderr, encoding='utf-8')
    output = result.stdout + result.stderr
    (tmp_path / 'identity.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == before['runner_sha256'], (
        'The same built host produced this receipt'
    )
    assert library_state() == before['libraries'], (
        'The owned offline library bytes remain unchanged'
    )
    assert result.returncode == 0, 'Actual native HTML production completes: ' + output
    assert (
        len(
            re.findall(
                r'^PASS\s*:\s*(?:edi_app::)?NativeReportCodec::test_native_html\(\)\s*$',
                output,
                re.MULTILINE,
            )
        )
        == 1
    ), 'Exactly one actual Qt producer completes'
    assert not re.search(r'^(?:FAIL!|SKIP|QFATAL|QWARN|QSYSTEM)\s*:', output, re.MULTILINE), (
        'Unrelated Qt failures or warnings cannot qualify this ordinary producer'
    )
    receipts = re.findall(r'\bE11_REPORT_NATIVE_HTML (\{[^\r\n]*\})', output)
    assert len(receipts) == 1, 'Exactly one actual returned HTML payload is retained'
    receipt = json.loads(receipts[0])
    assert set(receipt) == {'name', 'html'} and receipt['name'] == document['name'], (
        'The payload belongs to this authored input rather than another report'
    )
    (tmp_path / 'native.html').write_text(receipt['html'], encoding='utf-8')
    return receipt['html']


def test_native_offline_html_renders_with_collision_shaped_style_metadata(tmp_path):
    document = model()
    document['name'] = 'native-codec-style-boundary'
    background = [row for row in document['structure_styles'] if row['key'] == 'background']
    assert len(background) == 1, 'The existing style table supplies one real background row'
    background[0].update(light='#ff0000', dark='#ff0000')
    for key in ('edi_renderer_number', 'edi_renderer_number.extra', '__proto__', 'constructor'):
        document['structure_styles'].append({
            'key': key,
            'light': '#123456',
            'dark': '#abcdef',
            'value': 0.375,
        })
    text = native_html(tmp_path, document)
    contents = Contents()
    contents.feed(text)
    assert contents.model is not None, 'The actual native HTML carries its inert model element'
    payload = json.loads(contents.model)
    assert payload['name'] == document['name'] and payload['schema_version'] == 1, (
        'The native HTML payload belongs to this exact authored model and public schema'
    )
    assert payload['structure_styles'] == document['structure_styles'], (
        'Every original and collision-shaped style record reaches the actual native HTML whole'
    )
    assert not external_scripts(text), (
        'The native writer genuinely embeds its supplied offline libs'
    )
    pages = observe(text, require_structure_rendering=True)
    (tmp_path / 'browser.json').write_text(json.dumps(pages, indent=2), encoding='utf-8')
    assert set(pages) == {'wide', 'narrow'}, (
        'The existing browser observes both original viewports'
    )
    for page in pages.values():
        assert page['errors'] == [] and page['ready'], (
            'The actual native HTML codec and renderer complete without browser errors'
        )
        assert len(page['structures']) == len(document['structures']), (
            'Every actual native structure figure is observed'
        )
        for structure in page['structures']:
            assert any(
                canvas['width'] > 0
                and canvas['height'] > 0
                and canvas['draws'] > 0
                and any(colour[:3] == [1, 0, 0] for colour in canvas['clearColours'])
                for canvas in structure['canvases']
            ), 'The real native canvas draws using the authored original background style'
