"""Filesystem containment and binary64 reader closure at report publication boundaries."""

import math
import shutil

import edi
import pytest

from tests.fixtures.report_units.iucr_reference import rounded_pair
from tests.integration.py.test_report_iucr_persistence import project as numeric_project
from tests.integration.py.test_report_save_workflow import command
from tests.integration.py.test_report_storage import inventory, put, source


@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize('link', ['directory', 'final', 'temporary'])
def test_project_report_settings_never_follow_retained_links(tmp_path, operation, link):
    path = source(tmp_path, ['_report.html_offline false'])
    put(path, 'reports/opaque.html', 'independently retained report bytes\n')
    external = tmp_path / 'external'
    external.mkdir()
    settings = path / 'reports/report.edi'
    if link == 'directory':
        shutil.copytree(path / 'reports', external / 'reports')
        shutil.rmtree(path / 'reports')
        (path / 'reports').symlink_to(external / 'reports', target_is_directory=True)
    else:
        target = external / 'sentinel'
        target.write_bytes(
            settings.read_bytes() if link == 'final' else b'opaque external bytes\n'
        )
        selected = settings if link == 'final' else settings.with_name('report.edi.tmp')
        selected.unlink(missing_ok=True)
        selected.symlink_to(target)
    outside = inventory(external)
    original = inventory(path)
    loaded = edi.Project.load(path)
    loaded.report.html_offline = True
    destination = path if operation == 'save' else tmp_path / 'destination'
    error = None
    try:
        loaded.save() if operation == 'save' else loaded.save_as(destination)
    except (OSError, ValueError, RuntimeError) as caught:
        error = caught
    assert inventory(external) == outside, (
        'Project Save and Save as must never change bytes outside their owned report directory'
    )
    if operation == 'save-as' or error is not None:
        assert inventory(path) == original, (
            'Save as and refused publication retain every source byte, including linked reports'
        )
    if error is None:
        assert not (destination / 'reports').is_symlink(), (
            'Successful project publication materializes its owned report directory'
        )
        assert edi.Project.load(destination).report.html_offline is True, (
            'Successful contained publication persists the requested report settings'
        )
        assert (
            destination / 'reports/opaque.html'
        ).read_bytes() == b'independently retained report bytes\n', (
            'Materializing the owned report directory retains carried report artifacts exactly'
        )


@pytest.mark.parametrize('surface', ['core-save', 'python-save-html', 'cli-save', 'cli-output'])
@pytest.mark.parametrize('link', ['directory', 'final', 'temporary'])
def test_html_publication_never_truncates_a_link_target(tmp_path, surface, link):
    path = source(
        tmp_path, ['_report.html true', '_report.pdf false', '_report.html_offline false']
    )
    loaded = edi.Project.load(path)
    output = path / 'reports' / (loaded.name + '.html')
    external = tmp_path / 'external-html'
    external.mkdir()
    sentinel = external / 'sentinel'
    sentinel.write_bytes(b'independent external target, never an output\n')
    if link == 'directory':
        shutil.copytree(path / 'reports', external / 'reports')
        shutil.rmtree(path / 'reports')
        (path / 'reports').symlink_to(external / 'reports', target_is_directory=True)
    else:
        selected = output if link == 'final' else output.with_name('.' + output.name + '.part')
        selected.symlink_to(sentinel)
    outside = inventory(external)
    actions = {
        'core-save': loaded.report.save,
        'python-save-html': lambda: loaded.report.save_html(output, offline=False),
        'cli-save': lambda: command(path),
        'cli-output': lambda: command(path, '--output', str(output), '--online'),
    }
    succeeded = False
    try:
        result = actions[surface]()
        succeeded = result.returncode == 0 if surface.startswith('cli') else True
    except (OSError, ValueError, RuntimeError):
        pass
    assert inventory(external) == outside, (
        'Core, Python and CLI report output must not follow a retained final or temporary symlink'
    )
    if succeeded:
        assert output.is_file() and not output.is_symlink(), (
            'A successful CLI publication owns its output instead of retaining a link'
        )


@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
@pytest.mark.parametrize('operation', ['save', 'save-as'])
@pytest.mark.parametrize(
    ('value', 'uncertainty'),
    [
        (1.79e308, 2e307),
        (-1.79e308, 2e307),
        (3.88, 1.79e308),
        (0.0, 1.79e308),
        (1.1e308, 1e306),
        (0.0023, 0.019),
        (5e-324, 5e-324),
    ],
    ids=[
        'value-limit',
        'negative-limit',
        'fallback-su-limit',
        'zero-su-limit',
        'finite-control',
        'nonzero-control',
        'subnormal-control',
    ],
)
def test_successful_numeric_save_stays_inside_both_readers_finite_domain(
    tmp_path, rule, operation, value, uncertainty
):
    path = numeric_project(tmp_path, '4()', rule)
    loaded = edi.Project.load(path)
    parameter = loaded.experiments['bank'].background[0].intensity
    parameter.value, parameter.uncertainty, parameter.free = value, uncertainty, True
    original = inventory(path)
    destination = path if operation == 'save' else tmp_path / 'destination'
    try:
        loaded.save() if operation == 'save' else loaded.save_as(destination)
    except (OSError, ValueError, RuntimeError):
        rounded = rounded_pair(value, uncertainty, rule)
        assert not all(math.isfinite(number) for number in rounded), (
            'Representable ordinary, nonzero and subnormal controls must save successfully'
        )
        assert inventory(path) == original, (
            'A numeric-domain refusal occurs before replacing any previously readable source byte'
        )
        return
    try:
        restored = edi.Project.load(destination).experiments['bank'].background[0].intensity
    except (OSError, ValueError, RuntimeError) as error:
        pytest.fail(
            'A successful save must remain readable by its finite-domain loader: ' + str(error)
        )
    assert math.isfinite(restored.value) and math.isfinite(restored.uncertainty), (
        'Writer rounding may never publish a value or uncertainty outside binary64 finite range'
    )
    if value:
        assert restored.value != 0, 'Reader closure also retains every nonzero-value witness'
