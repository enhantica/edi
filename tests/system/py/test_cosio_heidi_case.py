"""Unit 9 case contract and actual independent fit against BP5024 Table 4."""

import ast
import hashlib
import json
import shutil

import edi
import numpy as np
import pytest

from tests.fixtures.cosio_heidi_2008.reference import REFERENCE
from tests.fixtures.tutorial_cases.contract import ROOT, case_record
from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL, python_syntax
from tests.fixtures.tutorial_cases.presentation import text
from tests.fixtures.tutorial_cases.stages import assert_teaching_stages, observe

CASE = 'sc-neut-cwl_cosio-heidi'


def test_three_temperature_case_links_three_distinct_structures_and_datasets():
    record = case_record(CASE)
    assert len(record['structures']) == len(record['experiments']) == 3, (
        'Unit 9: CoSiO HEiDi has exactly three structures and three datasets'
    )
    path = ROOT / 'docs/user/cli' / CASE / 'project'
    assert (path / 'project.edi').is_file(), (
        'Unit 9: the three-temperature example is a saved project'
    )
    project = edi.Project.load(path)
    assert project.analysis.fitting_mode == 'independent', (
        'Unit 9: the three temperatures fit independently rather than jointly or sequentially'
    )
    structures = list(project.structures)
    experiments = list(project.experiments)
    assert len(structures) == len(experiments) == 3, (
        'Unit 9: the actual example loads all three structures and datasets'
    )
    parameters = json.loads(project.report.model().to_json())['parameters']
    linked = []
    temperatures = []
    for experiment in experiments:
        links = list(experiment.linked_structures)
        assert len(links) == 1, 'Unit 9: each temperature links exactly its own structure'
        identity = links[0].structure_id
        linked.append(identity)
        data = experiment.refln
        actual = list(
            zip(data.index_h, data.index_k, data.index_l, data.intensity_meas, strict=True)
        )
        matching = [
            temp
            for temp, reference in REFERENCE['cases'].items()
            if actual == [tuple(row[:3] + [row[4]]) for row in reference['rows']]
        ]
        assert len(matching) == 1, (
            'Unit 9: each dataset retains one complete published temperature measurement'
        )
        temperatures.append(matching[0])
        moments = [
            row
            for row in parameters
            if row['unique_name'].startswith(identity + '.atom_site_moment.')
        ]
        assert len(moments) == (4 if matching[0] == '2.5K' else 0), (
            'Unit 9: 300 K and 55 K are nuclear only; '
            '2.5 K has both crystal and magnetic structure'
        )
        assert experiment.experiment_type.sample_form == edi.SampleFormEnum.SINGLE_CRYSTAL, (
            'Unit 9: all three measured datasets are single crystal'
        )
    assert temperatures == ['300K', '55K', '2.5K'], (
        'Unit 9: the independent example presents 300 K first, 55 K next and 2.5 K last'
    )
    assert len(set(linked)) == 3 and set(linked) == {structure.name for structure in structures}, (
        'Unit 9: three one-to-one links cannot reuse one temperature structure'
    )


def test_actual_independent_example_fit_reaches_published_moment_values(tmp_path):
    source = ROOT / 'docs/user/cli' / CASE / 'project'
    assert (source / 'project.edi').is_file(), (
        'Unit 9: fitting starts from the real committed example'
    )
    destination = tmp_path / 'project'
    shutil.copytree(source, destination)
    project = edi.Project.load(destination)
    assert project.analysis.fitting_mode == 'independent', (
        'Unit 9: the fitted example uses independent mode'
    )
    starting = json.loads(project.report.model().to_json())['parameters']
    moment_start = [row for row in starting if 'atom_site_moment' in row['unique_name']]
    assert len(moment_start) == 4 and all(row['free'] for row in moment_start), (
        'Unit 9: all four independent Table 4 moment components participate in the actual fit'
    )
    project.analysis.fit()
    rows = json.loads(project.report.model().to_json())['parameters']
    fitted = []
    for label, component, value, su in [
        ('Co1', 'x', 1.20, 0.03),
        ('Co1', 'y', 3.64, 0.02),
        ('Co1', 'z', 0.57, 0.09),
        ('Co2', 'y', 3.35, 0.02),
    ]:
        matches = [
            row
            for row in rows
            if label in row['unique_name']
            and 'moment' in row['unique_name']
            and row['unique_name'].endswith('crystalaxis_' + component)
        ]
        assert len(matches) == 1, (
            'Unit 9: each Table 4 moment component has one low-temperature fitted result'
        )
        fitted.append(matches[0]['value'])
        assert np.isfinite(matches[0]['value']) and abs(abs(matches[0]['value']) - value) <= su, (
            'Unit 9: fitted moments agree with external BP5024 Table 4 within i'
            'ts stated standard uncertainty, allowing the global spin-reversal '
            'gauge'
        )

    assert abs(float(np.linalg.norm(fitted[:3])) - 3.87) <= 0.03, (
        'Unit 9: the fitted Co1 moment length agrees with Table 4 3.87(3) muB'
    )
    assert all(value > 0 for value in fitted) or all(value < 0 for value in fitted), (
        'Unit 9: only a coherent global spin reversal is equivalent to the Table 4 moment signs'
    )


@pytest.mark.parametrize('extension', ['py', 'ipynb'])
def test_python_tutorial_explicitly_loads_and_links_three_datasets_in_stages(  # noqa: PLR0914 - one ordered teaching boundary
    extension, monkeypatch, tmp_path
):
    path = ROOT / 'docs/user/tutorials' / (CASE + '.' + extension)
    assert path.is_file(), 'Unit 9: the three-temperature tutorial exists as script and notebook'
    source = (
        path.read_text()
        if extension == 'py'
        else '\n'.join(
            text(cell)
            for cell in json.loads(path.read_text())['cells']
            if cell['cell_type'] == 'code' and text(cell) != INSTALL_CELL
        )
    )
    source = python_syntax(source)
    plan = observe(source)
    assert_teaching_stages(plan)
    tree = ast.parse(source)
    calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert any(name.endswith('.structures.add_from_cif_path') for name in calls), (
        'Unit 9: Python visibly loads three collection CIF structures rathe'
        'r than only opening a complete project'
    )
    assert any(name.endswith('.experiments.add_from_data_path') for name in calls), (
        'Unit 9: Python visibly loads all three measured datasets'
    )
    assert any(name.endswith('.linked_structures.create') for name in calls), (
        'Unit 9: Python teaches all three explicit structure-to-dataset links'
    )
    compact = source.replace(' ', '')
    assert "fitting_mode='independent'" in compact or 'fitting_mode="independent"' in compact, (
        'Unit 9: Python explicitly selects independent fitting'
    )

    first_fit_line = next(event['line'] for event in plan['events'] if event['kind'] == 'fit')
    assert not any(
        isinstance(node, ast.Call)
        and node.lineno < first_fit_line
        and ast.unparse(node.func).endswith('.Project.load')
        for node in ast.walk(tree)
    ), 'Unit 9: Python builds the three datasets from collection inputs before fitting'
    partner = ROOT / 'docs/user/tutorials' / (CASE + ('.py' if extension == 'ipynb' else '.ipynb'))
    assert partner.is_file(), 'Unit 9: notebook and script both carry the three-temperature lesson'
    partner_source = (
        partner.read_text()
        if extension == 'ipynb'
        else '\n'.join(
            text(cell)
            for cell in json.loads(partner.read_text())['cells']
            if cell['cell_type'] == 'code' and text(cell) != INSTALL_CELL
        )
    )
    partner_source = python_syntax(partner_source)
    partner_tree = ast.parse(partner_source)

    def teaching_code(module):
        module.body = [
            node
            for node in module.body
            if not (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            )
        ]
        return ast.dump(module, include_attributes=False)

    assert teaching_code(tree) == teaching_code(partner_tree), (
        'Unit 9: script and notebook execute the same inputs, links and stage sequence'
    )
    magnetic_events = [
        i
        for i, event in enumerate(plan['events'])
        if event['kind'] == 'free' and event['group'] == 'magnetic moments'
    ]
    assert (
        magnetic_events
        and sum(event['kind'] == 'fit' for event in plan['events'][: magnetic_events[0]]) >= 2
    ), 'Unit 9: the tutorial performs nuclear fit stages before freeing magnetic moments'

    if extension == 'ipynb':
        from tests.fixtures.tutorial_cases import notebook_fit  # noqa: PLC0415

        prelude = """
import hashlib as _stage_hashlib
_stage_patterns = []
_stage_display_type = type(_stage_edi.Project(name='observer').display)
_stage_original_pattern = _stage_display_type.pattern
def _stage_record_pattern(self, *args, **kwargs):
    result = _stage_original_pattern(self, *args, **kwargs)
    project = self._project
    project.analysis.calculate()
    parameters = _stage_json.loads(project.report.model().to_json())['parameters']
    shown = args[0] if args else kwargs.get('expt_name')
    for experiment in project.experiments:
        if shown is not None and experiment.name != shown:
            continue
        data = experiment.refln
        indices = list(zip(data.index_h, data.index_k, data.index_l))
        if (1, 0, 0) in indices:
            index = indices.index((1, 0, 0))
        else:
            index = None
        measured = [[int(h), int(k), int(l), float(y)] for h,k,l,y in zip(
            data.index_h, data.index_k, data.index_l, data.intensity_meas)]
        fingerprint = _stage_hashlib.sha256(_stage_json.dumps(measured).encode()).hexdigest()
        _stage_patterns.append({
            'fits': len(_stage_fits),
            'fingerprint': fingerprint,
            'structures': len(project.structures),
            'experiments': len(project.experiments),
            'links': [list(link.structure_id for link in bank.linked_structures)
                      for bank in project.experiments],
            'moments': [row for row in parameters if 'atom_site_moment' in row['unique_name']],
            'calc100': float(data.intensity_calc[index]) if index is not None else None,
            'meas100': float(data.intensity_meas[index]) if index is not None else None,
        })
    return result
_stage_display_type.pattern = _stage_record_pattern
"""
        postlude = "_stage_fits[-1]['patterns'] = _stage_patterns\n"
        with monkeypatch.context() as context:
            context.setattr(notebook_fit, 'PRELUDE', notebook_fit.PRELUDE + prelude)
            context.setattr(notebook_fit, 'POSTLUDE', postlude + notebook_fit.POSTLUDE)
            collection = notebook_fit.local_collection(tmp_path / 'collection')
            observations = notebook_fit.execute(CASE, tmp_path / 'kernel', collection)
        patterns = observations[-1]['patterns']
        expected_digests = {
            hashlib.sha256(
                json.dumps([row[:3] + [row[4]] for row in reference['rows']]).encode()
            ).hexdigest(): temp
            for temp, reference in REFERENCE['cases'].items()
        }
        order = list(dict.fromkeys(item['fingerprint'] for item in patterns))
        assert [expected_digests.get(value) for value in order] == ['300K', '55K', '2.5K'], (
            'Unit 9: actual displayed data are the unchanged published measurements, '
            'first 300 K, then 55 K, then 2.5 K'
        )
        final = patterns[-1]
        assert (
            final['structures'] == final['experiments'] == 3
            and all(len(link) == 1 for link in final['links'])
            and len({link[0] for link in final['links']}) == 3
        ), (
            'Unit 9: the actual notebook builds three distinct structures '
            'and three one-to-one linked datasets'
        )
        low_digest = next(value for value, temp in expected_digests.items() if temp == '2.5K')
        patterns = [item for item in patterns if item['fingerprint'] == low_digest]
        assert any(
            not item['moments'] and item['meas100'] > 0 and abs(item['calc100']) < 1e-12
            for item in patterns
        ), (
            'Unit 9: the real notebook shows measured magnetic-only (100) '
            'with zero nuclear intensity before adding moments'
        )
        assert any(item['moments'] and item['calc100'] > 100 for item in patterns), (
            'Unit 9: a later real notebook chart shows the added magnetic contribution at (100)'
        )
        assert any(
            not any('atom_site_moment' in row['unique_name'] for row in step['before'])
            for step in observations
        ), 'Unit 9: the real notebook fits the nuclear model before adding magnetic structure'
        assert any(
            any('atom_site_moment' in row['unique_name'] and row['free'] for row in step['before'])
            for step in observations
        ), 'Unit 9: a later real notebook stage actually fits magnetic moments'
