""": both CLIs canonicalize absent absorption as typed none."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import (
    crysta_reference_prefix,
    crysta_reference_source,
    project_record_datetime,
    project_record_value,
    project_record_without_fields,
    project_tree_parts,
)

ROOT = Path(__file__).resolve().parents[3]


def _crysta_root() -> Path:
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    fitting = Path(override) if override else crysta_reference_source() / 'tests/fitting'
    assert (fitting / 'manifest.yml').is_file(), (
        "the absorption CLI pin requires edi's pinned crysta corpus authority"
    )
    return fitting


def _crysta_cli() -> Path:
    executable = crysta_reference_prefix() / 'bin/crysta'
    assert executable.is_file(), 'edi core-build must install the comparison crysta CLI'
    return executable


def _stage(destination: Path, *, spelling: str) -> Path:
    case = _crysta_root() / 'ncaf-wish-3bank-s5'
    shutil.copytree(case / 'project', destination)
    analysis = (case / 'bounded-analysis/analysis.edi').read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 2' in analysis, (
        'the absorption CLI witness must derive its fit recipe from a declared corpus variant'
    )
    (destination / 'analysis/analysis.edi').write_text(
        analysis.replace('_minimizer.max_iterations 2', '_minimizer.max_iterations 1'),
        encoding='utf-8',
    )
    for experiment in sorted((destination / 'experiments').glob('*.edi')):
        text = experiment.read_text(encoding='utf-8')
        block = '_absorption.type cylinder\n_absorption.abscor1 0.0(10)\n_absorption.abscor2 0.0\n'
        assert text.count(block) == 1, (
            'each NCAF bank must expose exactly one declared cylinder block before mutation'
        )
        replacement = '_absorption.type none\n' if spelling == 'explicit-none' else ''
        experiment.write_text(text.replace(block, replacement), encoding='utf-8')
    return destination


def _run(command: list[str], project: Path) -> None:
    completed = subprocess.run(
        [*command, 'fit', str(project), '--verbosity', 'off'],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, (
        'each CLI must successfully canonicalize the independently declared absorption witness; '
        + completed.stdout
        + completed.stderr
    )


@pytest.mark.parametrize('spelling', ['absent', 'explicit-none'])
def test_both_clis_write_one_typed_none_absorption_tree(
    tmp_path: Path,
    spelling: str,
) -> None:
    crysta_project = _stage(tmp_path / 'crysta', spelling=spelling)
    edi_project = _stage(tmp_path / 'edi', spelling=spelling)
    source_record = (crysta_project / 'project.edi').read_bytes()
    assert (edi_project / 'project.edi').read_bytes() == source_record, (
        'both CLI comparisons must begin from the same committed partial project record'
    )

    _run([str(_crysta_cli())], crysta_project)
    _run([sys.executable, '-m', 'edi'], edi_project)

    crysta_tree, crysta_record = project_tree_parts(crysta_project, normalize_fit_time=True)
    edi_tree, edi_record = project_tree_parts(edi_project, normalize_fit_time=True)
    assert crysta_tree == edi_tree, (
        'crysta and edi must save every non-record path and byte identically except fit time '
        'from each absorption-none spelling'
    )
    expected_carried = source_record.replace(b'_edi.schema_version 2', b'_edi.schema_version 3', 1)
    assert crysta_record == expected_carried, (
        'the disengaged crysta CLI must carry its partial project record byte-for-byte apart '
        'from the required schema reconciliation'
    )
    assert (
        project_record_without_fields(edi_record, 'created', 'last_modified', 'timestamp')
        == crysta_record
    ), (
        'edi must enrich the carried project record only with its three previously absent owned '
        'metadata fields, never rebaseline or discard the carried bytes'
    )
    assert project_record_value(edi_record, 'timestamp') == b'?', (
        'the enriched record must retain the loaded project timestamp default as the STAR sentinel'
    )
    assert project_record_datetime(edi_record, 'last_modified') > project_record_datetime(
        edi_record, 'created'
    ), (
        'the enriched record must carry a materializable creation time and a strictly later '
        'successful-save time'
    )
    for experiment_file in sorted((edi_project / 'experiments').glob('*.edi')):
        experiment = experiment_file.read_text(encoding='utf-8')
        assert experiment.count('_absorption.type none') == 1, (
            'each absent or explicit-none input must materialize one typed-none selector per bank'
        )
        assert (
            '_absorption.abscor1' not in experiment and '_absorption.abscor2' not in experiment
        ), 'typed-none output must contain no cylinder-only abscor pair'
