"""Check recorded authoring evidence without running an assistant answer in CI."""

import hashlib
import json
import math
import re

OFFICIAL = 'https://easydiffraction.org/'
FREE_COUNTS = [3, 8, 12, 16, 15]
INPUT_HASHES = {
    'tutorial-lbco.cif': '00d1adc78bc31fff2e5bb124127aab91eefc889e2065c51b378a51cad02778c6',
    'tutorial-hrpt.xye': '70dba3f642b394f0e7e7802a8637e0e287164562671993ee0701b813c902e360',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def captured(evidence, name):
    value = evidence['captures'][name]
    assert sha256(value['text'].encode()) == value['sha256'], (
        'Gate 3/5: captured authoring output retains its exact observed bytes'
    )
    return value['text']


def machine(text):
    fields = {}
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            assert key not in fields, 'Gate 3/5: machine evidence cannot overwrite duplicate keys'
            fields[key] = value
    return fields


def observed_stages(evidence, row):
    names = row['execution']['stage_captures']
    if row['interface'] == 'python':
        assert names == ['python-stages'], (
            'Gate 3/5: Python stages name their actual retained result capture'
        )
        stages = json.loads(captured(evidence, names[0]))
        assert all(stage['status'] == 'DONE' for stage in stages), (
            'Gate 3/5: every retained Python stage completed its real fit successfully'
        )
    else:
        assert names == ['cli-stage-' + str(i) for i in range(1, 6)], (
            'Gate 3/5: native evidence retains each completed cumulative stage'
        )
        stages = []
        for name in names:
            fields = machine(captured(evidence, name))
            assert fields['status'] == 'done' and fields['converged'] == 'true', (
                'Gate 3/5: every recorded native fit actually completed successfully'
            )
            values = {k: float(v) for k, v in fields.items() if k.endswith('.value')}
            uncertainties = {
                k.removesuffix('.uncertainty') + '.value': float(v)
                for k, v in fields.items()
                if k.endswith('.uncertainty')
            }
            stages.append({
                'free_count': int(fields['n_free']),
                'reduced_chi_square': float(fields['reduced_chi_square']),
                'rwp': float(fields['rwp']),
                'values': values,
                'uncertainties': uncertainties,
            })
    assert [stage['free_count'] for stage in stages] == FREE_COUNTS, (
        'Gate 3/5: all five cumulative fits retain their declared free parameter groups'
    )
    for stage in stages:
        assert len(stage['values']) == stage['free_count'] and set(stage['values']) == set(
            stage['uncertainties']
        ), 'Gate 3/5: every fitted value has its actual standard uncertainty'
        assert all(
            math.isfinite(value)
            for value in [stage['rwp'], stage['reduced_chi_square'], *stage['values'].values()]
        ) and all(
            math.isfinite(value) and value >= 0 for value in stage['uncertainties'].values()
        ), 'Gate 3/5: authoring evidence cannot substitute missing or nonfinite fit quantities'
    return stages


def observed_quantities(evidence, row):
    text = captured(evidence, row['execution']['result_capture'])
    if row['interface'] == 'cli':
        return {
            key: float(value)
            for key, value in machine(text).items()
            if key in {item['quantity'] for item in row['comparisons']}
        }
    raw = json.loads(text)
    assert raw['source_commit'] == row['execution']['edi_source'], (
        'Gate 3/5: raw Python results identify the library that actually executed them'
    )
    streams = json.loads(captured(evidence, 'python-stdout'))
    iterations = re.search(r'done.*? (\d+) iters', streams[-1])
    assert iterations, 'Gate 3/5: final iteration evidence comes from actual executed output'
    return {
        'n_free': raw['free_counts'][-1],
        'iterations': int(iterations[1]),
        'rwp': raw['rwp'],
        'reduced_chi_square': raw['reduced_chi_square'],
        'param.La.adp_iso.value': raw['Biso']['La'],
        'param.Co.adp_iso.value': raw['Biso']['Co'],
        'param.O.adp_iso.value': raw['Biso']['O'],
        'param.cell_length_a.value': raw['a'],
    }


def assert_comparisons(root, evidence, row):
    reference = evidence['scientific_reference']
    path = root / 'docs/user/cli/pd-neut-cwl_lbco-hrpt/expected.json'
    assert (
        reference['path'] == path.relative_to(root).as_posix()
        and sha256(path.read_bytes()) == reference['sha256']
    ), 'Gate 3/5: authoring comparisons preserve the independent scientific reference bytes'
    pins = json.loads(path.read_text())['quantities']
    rows = {item['quantity']: item for item in row['comparisons']}
    assert len(rows) == len(row['comparisons']) and rows.keys() == pins.keys(), (
        'Gate 3/5: authoring comparisons retain every reference and separate regression quantity'
    )
    actual = observed_quantities(evidence, row)
    for name, pin in pins.items():
        observed = rows[name]
        assert {key: observed[key] for key in pin} == pin and observed['actual'] == actual[name], (
            'Gate 3/5: every comparison keeps its original pin tolerance and actual raw result'
        )
        matched = math.isclose(
            actual[name],
            pin['value'],
            abs_tol=pin.get('tol_abs') or 0,
            rel_tol=pin.get('tol_rel') or 0,
        )
        assert observed['matches'] is matched, (
            'Gate 3/5: failed numerical comparisons remain failures instead of claimed passes'
        )
    for kind, field in [
        ('reference', 'scientific_reference_match'),
        ('regression-pin', 'single_fit_regression_match'),
    ]:
        assert row[field] is all(
            item['matches'] for item in rows.values() if item['kind'] == kind
        ), 'Gate 3/5: scientific references and single-fit trajectory comparisons stay distinct'
    assert reference['single_fit_workflow'] and row['findings'], (
        'Gate 3/5: trajectory differences and execution findings remain explicitly documented'
    )


def assert_published_trial(root, evidence, row, interface, digest):
    assert row['interface'] == interface and row['publication_route'] == 'published-release', (
        'Gate 3/5: current evidence identifies the actual official published route'
    )
    assert (
        row['site_base'] == OFFICIAL
        and row['prompt_url'] == (OFFICIAL + interface + '/tutorials/assistant/')
        and 'preview_ref' not in row
    ), 'Gate 3/5: published trials cannot masquerade as prerelease preview evidence'
    assert_recorded_trial(root, evidence, row, interface, digest)


def assert_recorded_trial(root, evidence, row, interface, digest):
    assert row['interface'] == interface and isinstance(row.get('execution'), dict), (
        'Gate 3/5: both publication routes require an actual recorded artifact execution'
    )
    assert row['prompt_sha256'] == digest == sha256(row['prompt_text'].strip().encode()) and row[
        'fetched_prompt_sha256'
    ] == sha256(row['prompt_text'].encode()), (
        'Gate 3/5: each actual trial covers the exact current copyable prompt'
    )
    assert row['model'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date']), (
        'Gate 3/5: independent authoring evidence names its real model and date'
    )
    assert isinstance(row.get('execution'), dict) and (
        row['status'] == 'completed-with-findings' and row['execution'].get('exit_code') == 0
    ), 'Gate 3/5: current authoring evidence proves execution without claiming every pin passed'
    artifact = row.get('artifact')
    assert isinstance(artifact, dict) and (
        '/' not in artifact.get('name', '/')
        and re.fullmatch(r'[0-9a-f]{64}', artifact.get('sha256', ''))
    ), 'Gate 3/5: the actual portable generated artifact has an exact content identity'
    actual_execution = json.loads(captured(evidence, interface + '-execution'))
    assert (
        artifact
        == {
            'name': actual_execution['artifact'],
            'sha256': actual_execution['artifact_sha256'],
        }
        and row['execution']['exit_code'] == actual_execution['execution_exit']
        and row['fetched_prompt_sha256'] == actual_execution['prompt_sha256']
        and row['publication_route'] == actual_execution['publication_route']
    ), 'Gate 3/5: artifact identity and execution match the actual retained authoring receipt'
    assert_sources(evidence, row)
    assert_acquisition(evidence, row)
    stages = observed_stages(evidence, row)
    reference = json.loads(captured(evidence, 'staged-reference'))
    assert reference['sha256'] == evidence['documentation']['published_notebook_sha256'], (
        'Gate 3/5: stage comparison names the exact actually fetched worked notebook'
    )
    assert len(reference['actual_published_fit_outputs']) == len(stages), (
        'Gate 3/5: every cumulative stage has its corresponding published worked output'
    )
    for stage, published in zip(stages, reference['actual_published_fit_outputs'], strict=True):
        display = re.search(r'done.*?reduced χ² ([\d.]+).*?Rwp ([\d.]+)', published['stream'])
        assert display and (f'{stage["reduced_chi_square"]:.2f}', f'{100 * stage["rwp"]:.2f}') == (
            display[1],
            display[2],
        ), 'Gate 3/5: staged display projection adds no scientific tolerance'
    actual = observed_quantities(evidence, row)
    assert all(
        actual[name] == stages[-1][field]
        for name, field in [
            ('n_free', 'free_count'),
            ('rwp', 'rwp'),
            ('reduced_chi_square', 'reduced_chi_square'),
        ]
    ), 'Gate 3/5: final raw results agree with the independently retained last-stage capture'
    assert_comparisons(root, evidence, row)
    assert_correlation(evidence, row)


def assert_sources(evidence, row):
    package = json.loads(captured(evidence, 'package-source'))
    runtime = evidence['runtime']
    assert (
        runtime['edi_source'] == package['source_head']
        and runtime['sdk_source'] == package['sdk_source']
        and runtime['sdk_library_sha256'] == package['sdk_library_sha256']
    ), 'Gate 3/5: trial execution binds actual Edi SDK and scientific library identities'
    execution = row['execution']
    assert all(execution[field] == runtime[field] for field in ['edi_source', 'sdk_source']) and (
        execution['binary_sha256']
        == runtime[('native' if row['interface'] == 'cli' else 'python') + '_binary_sha256']
    ), 'Gate 3/5: executed binary provenance cannot drift from its qualified source receipt'
    assert (
        execution['diagnostic_only'] is runtime['diagnostic_only'] is True
        and execution['claims_released_artifact'] is False
    ), 'Gate 3/5: diagnostic artifacts cannot claim released binary identity'
    documentation = evidence['documentation']
    assert re.fullmatch(r'[0-9a-f]{40}', documentation['source_commit']) and (
        documentation['notebook_source_url']
        == 'https://colab.research.google.com/github/enhantica/edi/blob/'
        + documentation['source_commit']
        + '/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.ipynb'
    ), 'Gate 3/5: documentation and diagnostic source identities remain distinct'


def assert_acquisition(evidence, row):
    acquisition = json.loads(captured(evidence, 'prompt-acquisition'))
    matches = [item for item in acquisition if item['interface'] == row['interface']]
    assert (
        len(matches) == 1
        and matches[0]['sha256'] == row['prompt_page_sha256']
        and (matches[0]['url'] == matches[0]['final_url'] == row['prompt_url'])
        and matches[0]['http_status'] == 200
    ), 'Gate 3/5: prompt provenance retains the literal successfully fetched official page'
    references = json.loads(captured(evidence, 'reference-acquisition'))
    for name, digest in INPUT_HASHES.items():
        inputs = [item for item in references if item['name'] == name]
        assert (
            len(inputs) == 1 and inputs[0]['sha256'] == digest and inputs[0]['http_status'] == 200
        ), 'Gate 3/5: both actual trial inputs retain their independent public content hashes'
    assert all(item['http_status'] == 200 for item in references), (
        'Gate 3/5: required worked references were fetched successfully before artifact authoring'
    )


def assert_history(root, evidence, historical=None):
    path = root / 'tests/fixtures/tutorial_cases/assistant_trials.json'
    raw = path.read_bytes() if historical is None else historical
    assert evidence['schema'] == 1 and evidence['summary_document'] == 'assistant-prompt-trials', (
        'Gate 3/5: current evidence keeps its declared portable public summary identity'
    )
    assert sha256(raw) == evidence['historical_export_sha256'], (
        'Gate 3/5: both original failed attempts and their exported provenance remain unchanged'
    )
    rows = json.loads(raw)['records']
    assert len(rows) == 2 and all(
        row['status'] == 'failed'
        and row['artifact'] is None
        and row['pin_comparison'] == 'not reached'
        for row in rows
    ), 'Gate 3/5: current execution cannot erase historical prerequisite failures'


def assert_correlation(evidence, row):
    if row['interface'] == 'cli':
        pairs = json.loads(captured(evidence, 'cli-correlations'))
        wanted = {'lbco.atom_site.La.adp_iso', 'lbco.atom_site.Ba.adp_iso'}
        matches = [pair for pair in pairs if set(pair[:2]) == wanted]
        assert len(matches) == 1, (
            'Gate 3/5: the real shared-site displacement correlation is explicitly retained'
        )
        correlation = float(matches[0][2])
    else:
        text = captured(evidence, 'python-correlation-display')
        match = re.search(r'lbco\.atom_site\.Ba\.adp_iso\s+(-?[\d.]+)', text)
        assert match, 'Gate 3/5: notebook evidence retains its actual correlation display'
        correlation = float(match[1])
    assert row['La_Ba_Biso_correlation'] == correlation and -1 <= correlation <= 1, (
        'Gate 3/5: displacement correlation retains its observed sign and finite range'
    )
