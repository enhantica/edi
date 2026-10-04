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
assert observed == PIN['tolerances'], (
    ' every page must execute all of its original agreement pins without widening'
)
project = namespace['project']
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
print(' page migration and unchanged agreement pins verified: ' + PAGE)
