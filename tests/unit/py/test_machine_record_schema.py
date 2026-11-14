"""Manual machine records share the linked engine header and reject missing proof."""

import pytest

# Exercise the package-private boundary shared by manual records.
from edi._machine_records import schema_line  # noqa: PLC2701


def test_shared_header_preserves_an_engine_version_without_a_local_literal():
    assert schema_line('schema=47\nrecord=error\nstatus=error\n') == 'schema=47\n'


@pytest.mark.parametrize(
    'report',
    [
        None,
        '',
        'schema=0\nrecord=error\n',
        'schema=9\nrecord=fit\n',
        'schema=9\nrecord=error',
        'schema=9\nrecord=error\nschema=8\n',
    ],
)
def test_malformed_engine_header_cannot_be_used_for_an_undo_record(report):
    with pytest.raises(ValueError, match='report schema is malformed'):
        schema_line(report)
