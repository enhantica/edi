"""Capture historical input pins before ; these do not claim correctness.

Run at the main fork point, with origin/vendor-yap-multiphase-reference present.
No branch commit identifier is retained: blobs survive squash independently.
"""

import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'layout', ROOT / 'tests/integration/py/test_c34_t25_fullprof_layout.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base = ROOT / 'knowledge/verification/fullprof'
result = {}
for path in sorted(base.rglob('*.pcr')):
    name = path.parent.name
    name = name.replace('lab6-11b_', 'lab6-11b-echidna_').replace('lbco_', 'lbco-hrpt_')
    name = name.replace('cecoal_', 'cecoal-polaris_').replace('si_', 'si-sepd_')
    name = name.replace('ncaf_', 'ncaf-wish_').replace('diamond_dream', 'diamond-dream_basic')
    if name == 'pd-neut-cwl_lab6':
        variant = {'baseline': 'basic', '11B': '11b', 'absorption': 'absorption'}[
            path.stem.rsplit('_', 1)[1]
        ]
        name = 'pd-neut-cwl_lab6-echidna_' + variant
    text = path.read_text()
    result[name] = module.parse_pcr(text) | {'pcr': text, 'source': str(path.relative_to(ROOT))}
text = subprocess.check_output(
    [
        'git',
        '-C',
        str(ROOT),
        'show',
        'origin/vendor-yap-multiphase-reference:knowledge/verification/fullprof/refine-yap-3k/yap_3k.pcr',
    ],
    text=True,
)
result['pd-neut-cwl_yap-spodi_3k'] = module.parse_pcr(text) | {'pcr': text, 'source': 'edi PR #75'}
Path(__file__).with_name('baseline.json').write_text(json.dumps(result, indent=2) + '\n')
ralf = base / 'pd-neut-tof_ceo2-pearl_polynomial/Ceo2_PEARL.dat'
Path(__file__).with_name('Ceo2_PEARL.ralf').write_bytes(ralf.read_bytes())
