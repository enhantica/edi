"""The unreadable-file vehicle proves its real refusal and always restores access."""

import stat
from contextlib import nullcontext

import pytest

from tests.fixtures.read_access import unreadable_file


@pytest.mark.parametrize('body_fails', [False, True])
def test_actual_read_denial_preserves_the_file_and_restores_access(tmp_path, body_fails):
    path = tmp_path / 'record.edi'
    original = b'_metadata.name original\n'
    path.write_bytes(original)
    mode = stat.S_IMODE(path.stat().st_mode)
    scope = (
        pytest.raises(ValueError, match='intentional body failure')
        if body_fails
        else nullcontext()
    )
    with scope, unreadable_file(path) as denied_mode:
        assert path.is_file(), 'Actual read denial preserves the file and restores access.'
        assert stat.S_IMODE(path.stat().st_mode) == denied_mode, (
            'Actual read denial preserves the file and restores access.'
        )
        with pytest.raises(PermissionError):
            path.read_bytes()
        if body_fails:
            raise ValueError('intentional body failure')
    assert path.read_bytes() == original, (
        'Actual read denial preserves the file and restores access.'
    )
    assert stat.S_IMODE(path.stat().st_mode) == mode, (
        'Actual read denial preserves the file and restores access.'
    )


def test_read_denial_refuses_a_missing_file_without_creating_it(tmp_path):
    path = tmp_path / 'missing.edi'
    with pytest.raises(FileNotFoundError), unreadable_file(path):
        pytest.fail('A missing file must never become an unreadable-file witness')
    assert not path.exists(), 'Read denial refuses a missing file without creating it.'
