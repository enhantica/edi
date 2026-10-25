"""Observe real page completion, tab availability and frames against the retained baseline."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PAGES = ('project', 'structure', 'experiment', 'analysis', 'report')
BASELINE = json.loads((ROOT / 'tests/fixtures/project_opening/baseline.json').read_text())
# Gate policy chosen for the owner's explicit background-build responsiveness requirement:
# a real rendered frame at least every 100 ms, including synchronous open and final completion.
# This is a new acceptance ceiling, not a measured baseline or a claim about display refresh rate.
FRAME_CEILING_MS = 100


@pytest.fixture(scope='module')
def opening_receipts():
    # The runtime instrument accounts a module fixture once; do not parameterize its lifetime.
    return {
        route: run_opening_route(route) for route in ('folder', 'project.edi', 'zip', 'example')
    }


def run_opening_route(route):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Page readiness requires the actual built application test host'
    result = subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_project_page_readiness.qml'),
            '-o',
            '-,txt',
            'ProjectPageReadiness::test_routes:' + route,
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, 'The real application completes the page measurement: ' + output
    assert (
        len(re.findall(r'^PASS\s*:.*ProjectPageReadiness::test_routes\(', output, re.MULTILINE))
        == 1
    ), 'Each route produces exactly one completed actual-window measurement'
    assert not re.search(r'^(?:FAIL!|QFATAL|SKIP)\s*:', output, re.MULTILINE), (
        'Failed, skipped or incomplete measurements cannot count as readiness evidence'
    )
    receipts = [
        json.loads(row) for row in re.findall(r'PAGE_READINESS_EVIDENCE (\{[^\n]+\})', output)
    ]
    assert [(row['route'], row['phase']) for row in receipts] == [
        (route, 'cold'),
        (route, 'warm'),
    ], 'Each real input route retains both its first open and its second open in the same window'
    artifact = ROOT / 'build/project-opening' / (route + '.json')
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(receipts, indent=2) + '\n')
    return receipts


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_tabs_are_disabled_until_their_actual_page_is_built(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    painted = [snap for snap in row['snapshots'] if snap['painted']]
    assert painted, 'Disabled-tab evidence includes actual rendered frames'
    for index, name in enumerate(PAGES):
        assert any(
            not snap['ready'][index] and not snap['enabled'][index] for snap in row['snapshots']
        ), (
            'Every opened page first has a disabled tab while its actual Loader is incomplete: '
            + name
        )
        assert all(not snap['enabled'][index] or snap['ready'][index] for snap in painted), (
            'An exposed enabled tab always has an actual completed page behind it: ' + name
        )
        assert row['enabledAt'][index] >= row['built'][index] >= 0, (
            'The actual tab becomes available only after its actual page completion: ' + name
        )
    assert all(painted[-1]['ready']) and all(painted[-1]['enabled']), (
        'All five tabs become available after all five actual pages complete without visiting them'
    )


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_pages_build_in_workflow_order_without_a_placeholder(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    assert row['order'] == list(range(len(PAGES))), (
        'Actual Loader completion follows Project, Structure, Experiment, Analysis, Report'
    )
    assert all(not snap['placeholders'] for snap in row['snapshots']), (
        'Background page construction never exposes the removed Opening this page state'
    )


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_tab_availability_improves_the_committed_opening_baseline(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    baseline = BASELINE['routes'][row['route']][phase]
    assert 0 < row['firstDisplay'] <= baseline['target_first_display_ms'], (
        'The actual first Project frame meets its retained per-route display target'
    )
    assert 0 < row['firstUsable'] <= baseline['target_usable_ms'], (
        'The actual first calculated Project frame meets its retained per-route usable target'
    )
    for index, name in enumerate(PAGES):
        ceiling = (
            baseline['target_first_display_ms']
            if index == 0
            else baseline['marks_ms']['tab:appBar.tab.' + name + ':frame']
        )
        assert 0 < row['enabledAt'][index] <= ceiling, (
            "Each enabled tab meets Project's target or beats its retained baseline: "
            + name
            + ' measured='
            + str(row['enabledAt'][index])
            + ' ceiling='
            + str(ceiling)
        )


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_background_build_keeps_rendering_within_the_frame_ceiling(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    end = max(row['built'])
    frames = [0] + [ms for ms in row['frames'] if ms <= end] + [end]
    gaps = [right - left for left, right in zip(frames, frames[1:], strict=False)]
    assert len(frames) > 3 and frames == sorted(frames), (
        'Responsiveness observes multiple real frame swaps during the actual background build'
    )
    assert max(gaps) <= FRAME_CEILING_MS, (
        'No opening-to-last-page frame gap exceeds the explicit 100 ms gate policy: ' + str(gaps)
    )


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_opening_progress_counts_actual_pages_in_the_status_bar(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    painted = [snap for snap in row['snapshots'] if snap['painted']]
    pending = [snap for snap in painted if not all(snap['ready'])]
    assert pending, 'Status progress is exercised while actual page construction is pending'
    counts = []
    for snap in pending:
        match = re.search(r'Opening project…\s+([0-5])\s+of\s+5\s+pages', snap['statusText'])
        assert match is not None, (
            'The visible status bar shows Opening project… N of 5 pages while pages build'
        )
        count = int(match[1])
        counts.append(count)
        assert count == sum(snap['ready']), (
            'The status-bar count equals actual completed Loader items in the same rendered frame'
        )
        assert len(snap['bars']) == 1, (
            'Opening uses exactly one actual fit-style progress bar in the status bar'
        )
        bar = snap['bars'][0]
        assert bar['indeterminate'] or abs(bar['fraction'] - count / 5) < 1e-9, (
            'An estimated opening bar counts actual pages; an unknown estimate stays indeterminate'
        )
    assert counts == sorted(counts) and len(set(counts)) > 1, (
        'Visible opening progress advances monotonically through real page completions'
    )
    assert 'Opening project' not in painted[-1]['statusText'] and not painted[-1]['bars'], (
        'The opening status text and progress bar disappear when all five actual pages are built'
    )


@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip', 'example'])
@pytest.mark.parametrize('phase', ['cold', 'warm'])
def test_disabled_tabs_have_only_the_preparing_tooltip(opening_receipts, phase, route):
    row = next(row for row in opening_receipts[route] if row['phase'] == phase)
    assert all(not any(snap['busy']) for snap in row['snapshots']), (
        'No app-bar tab shows a busy indicator while opening progress belongs in the status bar'
    )
    assert row['tooltip'] == ['Preparing this page…'], (
        "A real hover over a disabled tab shows only the owner's Preparing this page tooltip"
    )
