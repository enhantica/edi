"""Author a rounded input control without saving through the product under test."""

import shutil
from pathlib import Path

from tests.fixtures.project_save.reference import declared_rule
from tests.fixtures.report_units.iucr_reference import saved_record


def materialize(source, destination):
    source, destination = Path(source), Path(destination)
    rule = declared_rule(source)
    shutil.copytree(source, destination)
    for path in destination.rglob('*.edi'):
        path.write_bytes(saved_record(path.read_bytes(), rule))
    return destination
