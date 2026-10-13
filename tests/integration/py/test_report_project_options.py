"""Project report options: separate-file placement, strict tokens and presence retention."""

import re
import shlex

import edi as engine
import pytest

from tests.integration.py.test_report_iucr_persistence import project


def source(tmp_path, items):
    path = project(tmp_path, '4()', None)
    report_items, analysis_items = [], []
    for item in items:
        if item.startswith('_report.correlation_threshold '):
            analysis_items.append(
                item.replace('_report.correlation_threshold', '_correlation_chart.threshold', 1)
            )
        elif item.startswith('_report.x_axis '):
            analysis_items.append(item.replace('_report.x_axis', '_pattern_chart.x_axis', 1))
        else:
            report_items.append(item)
    if report_items:
        metadata = path / 'reports/report.edi'
        metadata.parent.mkdir(exist_ok=True)
        metadata.write_text('_edi.schema_version 3\n' + '\n'.join(report_items) + '\n')
    if analysis_items:
        analysis = path / 'analysis/analysis.edi'
        analysis.write_text(analysis.read_text() + '\n' + '\n'.join(analysis_items) + '\n')
    return path


def tags(path):
    result = {}
    file = path / 'reports/report.edi'
    for line in file.read_text().splitlines() if file.exists() else []:
        if line.startswith('_report.'):
            words = shlex.split(line)
            result[words[0]] = words[1]
    return result


def report(loaded):
    assert hasattr(loaded, 'report'), (
        'The engine exposes the project-owned ReportSettings category'
    )
    return loaded.report


def test_absent_report_items_resolve_defaults_without_inventing_an_offline_item(tmp_path):
    loaded = engine.Project.load(source(tmp_path, []))
    settings = report(loaded)
    assert (settings.cif, settings.html, settings.pdf, settings.html_offline) == (
        False,
        True,
        False,
        False,
    ), 'Absent report formats use diffraction-lib defaults, including online HTML'
    assert settings.correlation_threshold is None, 'An absent report threshold remains automatic'
    assert settings.x_axis == 'native', 'An absent report axis resolves to native'
    assert list(settings.excluded) == ['data'], (
        'An absent exclusion item leaves only Data out, independently of app preferences'
    )
    target = tmp_path / 'saved'
    loaded.save_as(target)
    assert '_report.html_offline' not in tags(target), (
        'Saving an old project without html_offline must not add a Preferences-dependent item'
    )


@pytest.mark.parametrize('offline', ['true', 'false'])
def test_declared_report_options_survive_reload_and_canonical_resave(tmp_path, offline):
    lines = [
        '_report.cif false',
        '_report.html true',
        '_report.pdf false',
        f'_report.html_offline {offline}',
        '_report.correlation_threshold 0.9',
        '_report.x_axis d_spacing',
        '_report.excluded "reflections data"',
    ]
    loaded = engine.Project.load(source(tmp_path, lines))
    first = tmp_path / 'first'
    loaded.save_as(first)
    expected = {
        shlex.split(line)[0]: shlex.split(line)[1]
        for line in lines
        if not line.startswith(('_report.correlation_threshold ', '_report.x_axis '))
    }
    assert tags(first) == expected, (
        'The project writer preserves every explicit format, threshold, axis and exclusion token'
    )
    restored = engine.Project.load(first)
    settings = report(restored)
    assert settings.html_offline is (offline == 'true'), (
        'Explicit online and embedded options retain their boolean meanings'
    )
    assert settings.correlation_threshold.hex() == (0.9).hex(), (
        'The report threshold retains the correctly rounded binary64 decimal input'
    )
    assert settings.x_axis == 'd_spacing', 'The report keeps its stored d-axis option'
    assert list(settings.excluded) == ['reflections', 'data'], (
        'Excluded optional group identities retain their declared order'
    )
    second = tmp_path / 'second'
    restored.save_as(second)
    first_bytes = [
        line
        for line in (first / 'reports/report.edi').read_bytes().splitlines()
        if line.startswith(b'_report.')
    ]
    second_bytes = [
        line
        for line in (second / 'reports/report.edi').read_bytes().splitlines()
        if line.startswith(b'_report.')
    ]
    assert second_bytes == first_bytes, (
        'Reloading canonical report items must re-save byte-identical report-category lines'
    )


@pytest.mark.parametrize('threshold', [0.0, 1.0])
def test_report_threshold_accepts_both_closed_interval_endpoints(tmp_path, threshold):
    loaded = engine.Project.load(source(tmp_path, [f'_report.correlation_threshold {threshold}']))
    assert report(loaded).correlation_threshold == threshold, (
        'Report thresholds include zero and one without conflating zero with an absent threshold'
    )


@pytest.mark.parametrize(
    ('item', 'value'),
    [
        ('correlation_threshold', '1.5'),
        ('correlation_threshold', '-0.1'),
        ('correlation_threshold', 'abc'),
        ('correlation_threshold', 'nan'),
        ('correlation_threshold', 'inf'),
        ('x_axis', 'tof'),
        ('x_axis', 'd'),
        ('html_offline', 'yes'),
        ('html_offline', '1'),
        ('html_offline', 'False'),
        ('cif', 'abc'),
        ('html', '0'),
        ('html', 'yes'),
        ('tex', 'true'),
        ('pdf', 'no'),
    ],
)
def test_invalid_report_tokens_refuse_at_load_naming_the_item(tmp_path, item, value):
    name = (
        '_correlation_chart.threshold'
        if item == 'correlation_threshold'
        else '_pattern_chart.x_axis'
        if item == 'x_axis'
        else '_report.' + item
    )
    with pytest.raises(ValueError, match=re.escape(name)) as error:
        engine.Project.load(source(tmp_path, ['_report.' + item + ' ' + value]))
    assert name in str(error.value), (
        'A rejected report setting names its complete project item for correction'
    )


@pytest.mark.parametrize('empty', ["''", '""'], ids=['single-quotes', 'double-quotes'])
def test_explicit_empty_exclusions_include_data_and_survive_save_and_reload(tmp_path, empty):
    path = source(tmp_path, ['_report.excluded ' + empty])
    original = (path / 'reports/report.edi').read_bytes()
    loaded = engine.Project.load(path)
    assert list(report(loaded).excluded) == [], (
        'An explicitly empty exclusion list includes every optional group, including Data'
    )
    assert (path / 'reports/report.edi').read_bytes() == original, (
        'Resolving an explicit empty report value never rewrites its source item'
    )
    first = tmp_path / 'first'
    loaded.save_as(first)
    assert '_report.excluded' in tags(first), (
        'An explicitly empty exclusion item remains present after save'
    )
    assert not tags(first)['_report.excluded'], (
        'The writer retains an explicit empty exclusion item instead of replacing it by absence'
    )
    restored = engine.Project.load(first)
    assert list(report(restored).excluded) == [], (
        'A reload preserves explicit include-all rather than applying the absent-item Data default'
    )
