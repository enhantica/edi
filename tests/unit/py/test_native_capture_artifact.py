"""Prevent a concurrent native relink from changing a running acceptance module."""

from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws import rendering
from tests.fixtures.fast_chart_redraws.rendering import native_arguments


def test_native_capture_retains_its_artifact_across_relink(tmp_path):
    binary = tmp_path / 'edi_app_tests'
    binary.write_bytes(b'first completed artifact')
    binary.chmod(0o755)
    first = native_arguments(['env', 'QT_QUICK_BACKEND=software', binary, '-input', 'actor.qml'])
    binary.write_bytes(b'a later relink replaced the executable')
    second = native_arguments([binary, '-input', 'another.qml'])
    assert first[:2] == ['env', 'QT_QUICK_BACKEND=software'], (
        'Backend overrides remain intact when the native artifact is retained'
    )
    assert first[2] == second[0] and first[2] != str(binary), (
        'Every capture in the run uses the same retained artifact after a relink'
    )
    assert Path(second[0]).read_bytes() == b'first completed artifact', (
        'A later relink cannot replace the artifact actually used for acceptance'
    )


def test_copy_that_straddles_a_relink_is_refused(tmp_path, monkeypatch):
    binary = tmp_path / 'edi_app_tests'
    binary.write_bytes(b'completed first link')
    binary.chmod(0o755)
    copy = rendering.shutil.copy2

    def relink(source, destination):
        copy(source, destination)
        source.write_bytes(b'another link replaced the source during the copy')

    monkeypatch.setattr(rendering.shutil, 'copy2', relink)
    with pytest.raises(RuntimeError, match='changed while its capture snapshot was copied'):
        native_arguments([binary])
