"""Receipt transport controls: synthetic executable bytes are never app evidence."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.scan_screen import build, normal_app
from tests.integration.py.test_app_build_cache import namespace  # noqa: F401
from tests.integration.py.test_app_cache_closure import dispatch, request  # noqa: F401


def head(root):
    return subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()


def marker(revision):
    return b'transport-only executable\x00edi-build-commit:' + revision.encode() + b'\n'


@pytest.mark.parametrize(
    'stamp', ['missing', 'plain-sha', 'stale', 'dirty', 'unknown', 'ambiguous']
)
def test_receipt_rejects_unqualified_binary_stamp(namespace, stamp):  # noqa: F811
    root, sdk, source, _ = namespace
    revision = head(root)
    payloads = {
        'missing': b'transport-only binary without build evidence',
        'plain-sha': revision.encode(),
        'stale': marker('b' * 40),
        'dirty': marker(revision + '-dirty'),
        'unknown': marker('unknown'),
        'ambiguous': marker(revision) + marker('b' * 40),
    }
    binary = root / normal_app.APP
    binary.write_bytes(payloads[stamp])
    os.utime(binary, (2_000_000_000, 2_000_000_000))
    output = root.parent / 'rejected'
    with pytest.raises(RuntimeError, match='build identity'):
        normal_app.receipt(root, output, sdk, source)
    assert not (output / 'receipt.json').exists(), (
        'A newly timestamped stale, dirty, absent or ambiguous binary cannot publish a receipt'
    )


@pytest.mark.parametrize('change', ['unstaged', 'staged', 'untracked-source'])
def test_receipt_refuses_uncommitted_source_even_with_current_marker(namespace, change):  # noqa: F811
    root, sdk, source, _ = namespace
    path = root / ('app/extra.cpp' if change == 'untracked-source' else 'app/main.cpp')
    path.write_text('changed transport source')
    if change == 'staged':
        subprocess.run(['git', '-C', str(root), 'add', 'app/main.cpp'], check=True)
    with pytest.raises(RuntimeError, match='uncommitted source'):
        normal_app.receipt(root, root.parent / 'dirty', sdk, source)
    assert not (root.parent / 'dirty/receipt.json').exists(), (
        'A current marker cannot certify dirty tracked, staged or new production inputs'
    )


def test_receipt_binds_clean_marker_and_actual_binary_bytes(namespace):  # noqa: F811
    root, sdk, source, _ = namespace
    path = normal_app.receipt(root, root.parent / 'qualified', sdk, source)
    record = json.loads(path.read_text())
    assert record['source_sha'] == head(root) == record['build_identity']['source_sha'], (
        'The receipt source must be the independently authored embedded executable identity'
    )
    assert (
        record['binary']
        == record['build_identity']['binary']
        == hashlib.sha256((root / normal_app.APP).read_bytes()).hexdigest()
    ), 'The identity seal must bind exactly the bytes the observer will execute'


def test_receipt_rechecks_binary_before_publication(namespace, monkeypatch):  # noqa: F811
    root, sdk, source, _ = namespace
    original = normal_app.validate_current_inputs

    def replace_after_input_check(*args):
        original(*args)
        (root / normal_app.APP).write_bytes(marker('b' * 40))

    monkeypatch.setattr(normal_app, 'validate_current_inputs', replace_after_input_check)
    output = root.parent / 'replaced'
    with pytest.raises(RuntimeError, match='build identity'):
        normal_app.receipt(root, output, sdk, source)
    assert not (output / 'receipt.json').exists(), (
        'Replacing the executable during qualification cannot publish stale build evidence'
    )


@pytest.mark.parametrize('reuse', ['cache', 'prepared'])
def test_relabelled_receipt_cannot_hide_stale_delivered_binary(
    dispatch, reuse, tmp_path, monkeypatch  # noqa: F811
):
    first = request('screen', 'desktop', tmp_path / 'first')
    path = tmp_path / 'first/desktop/receipt.json'
    record = json.loads(path.read_text())
    binary = Path(record['executable'])
    binary.write_bytes(marker('b' * 40))
    record['binary'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    record['build_identity'] = {
        'kind': 'embedded-commit',
        'source_sha': record['source_sha'],
        'binary': record['binary'],
    }
    path.write_text(json.dumps(record))
    if reuse == 'prepared':
        monkeypatch.setenv('EDI_SCAN_SCREEN_DESKTOP_RECEIPT', str(path))
    with pytest.raises(RuntimeError, match='build identity'):
        request('screen', 'desktop', tmp_path / 'relabelled')
    assert first['receipt']['backend'] == 'desktop' and dispatch.captures == ['desktop'], (
        'Fresh receipt hashes and current source labels cannot bypass actual binary identity'
    )


def test_browser_snapshot_excludes_dirty_working_source_and_declares_it(namespace, monkeypatch):  # noqa: F811
    root, _, _, fixture = namespace
    expected = (root / 'app/main.cpp').read_bytes()
    (root / 'app/main.cpp').write_text('uncommitted transport mutation')
    output = root.parent / 'archive'
    output.mkdir()
    monkeypatch.setattr(build, 'observer_sources', lambda _source: {})
    source, _ = build.snapshot(root, output, fixture)
    assert (source / 'app/main.cpp').read_bytes() == expected, (
        'The browser production snapshot must use committed source, excluding working edits'
    )
    policy = json.loads((output / 'source-policy.json').read_text())
    assert policy == {
        'kind': 'git-archive',
        'revision': head(root),
        'includes_uncommitted_changes': False,
    }, 'The browser snapshot must explicitly describe its revision and excluded working changes'
