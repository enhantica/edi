"""Dataset uncertainties, selected scan templates and report null values."""

import json
import math
import re
import shlex
import shutil
from pathlib import Path

import edi
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'


def loop(path, category):
    for section in path.read_text().split('loop_')[1:]:
        tokens = shlex.split(section, comments=True)
        keys = []
        while tokens and tokens[0].startswith('_'):
            keys.append(tokens.pop(0))
        if not keys or not all(key.startswith(category + '.') for key in keys):
            continue
        records = []
        while len(tokens) >= len(keys) and not tokens[0].startswith('_'):
            records.append(dict(zip(keys, tokens[: len(keys)], strict=True)))
            del tokens[: len(keys)]
        return records
    return []


def raw_points(path):
    points = []
    for text in path.read_text().splitlines():
        try:
            values = list(map(float, text.split()))
        except ValueError:
            continue
        if len(values) not in {2, 3}:
            continue
        x, y = values[:2]
        sigma = values[2] if len(values) == 3 else math.sqrt(max(y, 1))
        if sigma > 0:
            points.append((x, y, sigma))
    return np.asarray(points)


def embedded(path):
    rows = loop(path, '_data')
    return np.asarray([
        [
            float(row['_data.two_theta']),
            float(row['_data.intensity_meas']),
            float(row['_data.intensity_meas_su']),
        ]
        for row in rows
    ])


@pytest.mark.parametrize(
    ('case', 'raw', 'experiment'),
    [
        ('pd-neut-cwl_hs-hrpt', 'data/hs-hrpt.xye', 'hrpt.edi'),
        ('pd-xray-cwl_lam7o3-p021', 'data/hep7c-xray-synchrotron.dat', 'p021.edi'),
        (
            'pd-neut-cwl_cosio-d20_scan',
            'project/experiments/d20_scan/01_001_497p3790.dat',
            'd20.edi',
        ),
    ],
)
def test_embedding_preserves_stated_uncertainties_and_missing_sigma_rule(case, raw, experiment):
    root = CLI / case
    expected = raw_points(root / raw)
    actual = embedded(root / 'project/experiments' / experiment)
    assert actual.shape == expected.shape, 'Embedded data must preserve every usable raw point'
    np.testing.assert_allclose(
        actual,
        expected,
        rtol=5e-6,
        atol=1e-7,
        err_msg='Raw sigma must survive; only missing sigma uses sqrt(max(y,1))',
    )
    if case == 'pd-neut-cwl_hs-hrpt':
        assert actual[0] == pytest.approx([3.950, 645.0, 49.5]), (
            'The HS point must retain sigma 49.5 rather than the Poisson estimate'
        )
    elif case == 'pd-xray-cwl_lam7o3-p021':
        assert actual[0, 2] == 1, 'A zero count without a sigma must receive unit uncertainty'
    else:
        assert len(actual) == 1506, 'The scan template must omit exactly the two zero-sigma rows'
        assert not np.isin(actual[:, 0], [150.7953, 150.8953]).any(), (
            'Zero-sigma observations must not enter the embedded pattern'
        )


@pytest.mark.parametrize(
    ('case', 'experiment', 'filename'),
    [
        ('pd-neut-cwl_cosio-d20_scan', 'd20', '01_001_497p3790.dat'),
        ('pd-xray-cwl_latp-bm01_scan', 'bm01', 'latp_312.dat'),
    ],
)
def test_scan_template_names_the_file_whose_observations_are_embedded(case, experiment, filename):
    project = CLI / case / 'project'
    analysis = dict(
        shlex.split(line)
        for line in (project / 'analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_sequential_fit.')
    )
    data = project / f'experiments/{experiment}.edi'
    source = re.findall(r'^_data_source.file_name\s+(\S+)', data.read_text(), re.MULTILINE)
    assert source == [filename] and analysis['_sequential_fit.template_file'] == filename, (
        'The scan declaration and embedded dataset must name the same selected template'
    )
    raw = project / analysis['_sequential_fit.data_dir'] / filename
    actual = embedded(data)
    expected = raw_points(raw)
    assert actual.shape == expected.shape, (
        'The selected template must supply the entire embedded dataset'
    )
    np.testing.assert_allclose(
        actual,
        expected,
        rtol=5e-6,
        atol=1e-7,
        err_msg='The template filename must identify the actual embedded values',
    )


@pytest.mark.parametrize(
    ('authors', 'shown'), [('.', ''), ('?', ''), ('A. Author; B. Author', 'A. Author; B. Author')]
)
def test_report_omits_cif_null_authors_but_keeps_named_authors(tmp_path, authors, shown):
    source = CLI / 'pd-neut-cwl_lbco-hrpt/project'
    target = tmp_path / 'project'
    shutil.copytree(source, target)
    metadata = target / 'project.edi'
    metadata.write_text(
        re.sub(
            r'^_metadata.authors .*$',
            f'_metadata.authors "{authors}"',
            metadata.read_text(),
            flags=re.MULTILINE,
        )
    )
    project = edi.Project.load(target)
    assert project.metadata.authors == authors, 'The project must retain the literal Authors field'
    model = json.loads(project.report.model().to_json())
    assert model.get('project', model)['authors'] == shown, (
        'Report authors must omit CIF nulls and retain real names'
    )
