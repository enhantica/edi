"""Execute one real page; observe its unchanged assertions and serialized model."""

import dataclasses
import hashlib
import json
import runpy
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from edi import StructureFactory, verification

ROOT = Path(__file__).resolve().parents[3]
PAGE = sys.argv[1]
PIN = json.loads((ROOT / 'tests/fixtures/c14_t4_neutron/page_pins.json').read_text())['pages'][
    PAGE
]
AGREEMENT = verification.assert_patterns_agree
observed = []
input_maps = []
STRUCTURE_DICT = StructureFactory.from_dict


def make_structure(spec):
    input_maps.append(dict(spec.get('scattering_lengths_fm', {})))
    return STRUCTURE_DICT(spec)


def compare(*args, **kwargs):
    observed.append(dataclasses.asdict(kwargs['tolerances']))
    return AGREEMENT(*args, **kwargs)


for filename, digest in PIN['files'].items():
    path = ROOT / 'knowledge/verification/fullprof' / PIN['reference_directory'] / filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
        ' migration must retain the independent FullProf reference bytes'
    )
with (
    patch.object(verification, 'assert_patterns_agree', side_effect=compare),
    patch.object(StructureFactory, 'from_dict', side_effect=make_structure),
):
    namespace = runpy.run_path(
        str(ROOT / 'docs/dev/verification' / (PAGE + '.py')), run_name='__main__'
    )
project = namespace['project']
replacement = PAGE == 'pd-neut-cwl_PbSO4_beba-asymmetry'
if replacement:
    # ADR-0080 retires the TCH + BeBa subject whose historical bounds remain
    # in page_pins.json. Npr5 is independently gated by the profile family and
    # the real page's disabled-asymmetry escape, not by a repin of those bounds.
    peak = project.experiment.peak
    assert type(peak).__name__ == 'CwlPseudoVoigtBerarBaldinozzi', (
        'The replacement page must select the owner-declared Npr5 BeBa shape'
    )
    assert all(
        getattr(peak, name, None) is None for name in ('broad_lorentz_x', 'broad_lorentz_y')
    ), 'The replacement page must not reconstruct the retired TCH BeBa combination'
    assert all(
        getattr(peak, name, None) is not None for name in ('mixing_eta_0', 'mixing_eta_1')
    ), 'The replacement page must carry both declared Npr5 mixing slots'
else:
    assert observed == PIN['tolerances'], (
        'Every retained-model page must execute all original agreement pins without widening'
    )
all_maps = input_maps + [dict(structure.scattering_lengths_fm) for structure in project.structures]
for overrides in all_maps:
    if PAGE.endswith('_11B'):
        assert not overrides or overrides == {'11B': 6.65}, (
            ' isotope override may be removed only when its source reproduces the PCR pin'
        )
    else:
        assert not overrides, (
            ' migrated natural-element page must not retain a scattering override map'
        )
with tempfile.TemporaryDirectory() as directory:
    project.save_as(directory)
    emitted = '\n'.join(p.read_text() for p in (Path(directory) / 'experiments').glob('*.edi'))
    assert '_scattering_source.neutron_scattering_length' in emitted, (
        ' page must carry its neutron source on the actual experiment'
    )
message = 'replacement-model checks' if replacement else 'unchanged agreement pins'
print(' page migration and ' + message + ' verified: ' + PAGE)
