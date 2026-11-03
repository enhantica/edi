"""A real buffered settings-write error must precede any success or tracking replacement."""

import json

import edi
import pytest

from tests.integration.py.test_report_save_workflow import rows
from tests.integration.py.test_report_storage import source
from tests.system.py import test_report_publication_failures as publication

fault_library = publication.fault_library
fault_environment = publication.fault_environment
run_fault = publication.run_fault


@pytest.mark.parametrize('surface', ['core-python', 'cli-save'])
@pytest.mark.parametrize('kind', ['settings-write', 'settings-close'])
def test_late_settings_write_error_preserves_the_previous_rows_and_reports_failure(
    tmp_path, fault_library, surface, kind
):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    loaded = edi.Project.load(path)
    loaded.report.save()
    settings = path / 'reports/report.edi'
    original, tracking = settings.read_bytes(), rows(path)
    loaded.metadata.title = 'Different digest before the buffered settings failure'
    loaded.save()
    receipt = tmp_path / 'late-write-receipt'
    environment = fault_environment(fault_library, settings.parent, kind, receipt)
    result = run_fault(path, surface, environment, settings.with_name(loaded.name + '.html'))
    event = 'write-after-open' if kind == 'settings-write' else 'close-after-write'
    assert receipt.exists() and event in receipt.read_text(), (
        (
            'The actual settings temporary file reaches an ENOSPC write after '
            'opening, independently of rename refusal: '
        )
        + result.stdout
        + result.stderr
    )
    failed = (
        result.returncode != 0 if surface == 'cli-save' else json.loads(result.stdout)['failed']
    )
    assert failed, (
        'Core, Python and CLI must report a late settings completion failure before success'
    )
    assert settings.read_bytes() == original and rows(path) == tracking, (
        'A late buffered settings error never renames partial bytes over '
        'the previous saved tracking rows'
    )
    if surface == 'core-python':
        observed = json.loads(result.stdout)
        assert observed['live'] == observed['disk'], (
            'After a late settings failure the open model rolls back to the persisted report rows'
        )
