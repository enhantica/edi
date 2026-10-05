"""The owner's up/down scan is preserved as a CLI project, byte for byte."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_cli_scan_contains_the_original_inputs():
    expected = json.loads((ROOT / 'tests/fixtures/c11_t62/scan-inputs.json').read_text())['files']
    project = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project'
    extension = json.loads(
        (ROOT / 'tests/fixtures/constraint_expressions/byte-pins.json').read_text()
    )['cases']['repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project']
    public = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/saved-metadata.json').read_text()
    )['repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project']
    assert public['prior_input_sha256'] == expected, (
        'the metadata witness must retain every original owner scan identity'
    )
    assert extension['before']['input_sha256'] == public['input_sha256'], (
        'the relation extension must retain the complete reviewed metadata-only witness'
    )
    for relative, digest in expected.items():
        path = project / relative
        assert path.is_file(), f' scope 1: vendored CLI scan is missing original input {relative}'
        adaptations = json.loads(
            (ROOT / 'tests/fixtures/e04_t12_public_release/project-metadata.json').read_text()
        )
        adaptation = adaptations.get(path.relative_to(ROOT).as_posix())
        expected_digest = digest
        if relative in {'analysis/analysis.edi', 'structures/cosio.edi'}:
            expected_digest = extension['after_input_sha256'][relative]
        if adaptation:
            assert adaptation['before_sha256'] == digest, (
                'the scan metadata adaptation must retain the original owner input identity'
            )
            expected_digest = adaptation['after_sha256']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest, (
            f' scope 1: original owner scan bytes must be preserved: {relative}'
        )


def test_cli_full_scan_has_every_reversed_temperature_pair():
    project = ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project'
    files = sorted((project / 'experiments/d20_scan').glob('*.dat'))
    assert len(files) == 324, ' directional acceptance needs every original scan file'
    seen = []
    for index, (down, up) in enumerate(zip(files[:162], reversed(files[162:]), strict=True)):
        assert (down.name[:6], up.name[:6]) == (f'01_{index + 1:03}', f'02_{162 - index:03}'), (
            ' directional pairing must preserve the uninterrupted down/up file order'
        )
        content = down.read_bytes()
        assert content == up.read_bytes(), (
            f' compare the same observations in both directions: {down.name}/{up.name}'
        )
        temperatures = re.findall(rb'(?m)^TEMP\s+([0-9.]+)', content)
        assert len(temperatures) == 1, ' each paired input needs one temperature'
        seen.append(temperatures[0])
    assert len(set(seen)) == 162, ' no ambiguous or omitted temperature pair is allowed'
