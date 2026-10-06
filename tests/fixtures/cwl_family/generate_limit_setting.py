"""Record the fixed-angle contract from FullProf inputs and tagged upstream metadata.

Usage: python -m tests.fixtures.cwl_family.generate_limit_setting UPSTREAM OWNER_PCR
Neither product engine is imported; no expected scientific output is generated.
"""

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    upstream = Path(sys.argv[1])
    sha = '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf'
    path = 'src/easydiffraction/datablocks/experiment/categories/peak/cwl_mixins.py'
    source = subprocess.check_output(['git', 'show', sha + ':' + path], cwd=upstream)
    cls = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == 'BerarBaldinozziAsymmetryMixin'
    )
    fields = [
        node.target.attr.removeprefix('_')
        for node in ast.walk(cls)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Attribute)
        and isinstance(node.annotation, ast.Name)
        and node.annotation.id == 'Parameter'
    ]
    assert fields == ['asym_beba_a0', 'asym_beba_b0', 'asym_beba_a1', 'asym_beba_b1']
    pcr = Path(sys.argv[2])
    lines = pcr.read_text().splitlines()
    setting_line = next(i for i, line in enumerate(lines) if 'AsyLim' in line)
    limit = float(lines[setting_line + 1].split()[7])
    assert limit == 160
    asy_line = next(i for i, line in enumerate(lines) if 'Pref1' in line and 'Asy4' in line)
    header = lines[asy_line].removeprefix('!').split()
    codes = lines[asy_line + 2].split()
    codewords = [float(codes[header.index(name)]) for name in ['Asy1', 'Asy2', 'Asy3', 'Asy4']]
    record = {
        'kind': 'independent-contract-reference',
        'limit_item': 'asym_beba_limit',
        'limit_is_fit_coefficient': False,
        'limit_units': 'degrees',
        'fullprof_manual': {
            'url': 'https://www.psi.ch/sites/default/files/import/lns-diffraction/LinuxEN/fullprof-manual.pdf',
            'pdf_pages': [75, 76],
            'line': 8,
            'classification': 'fixed powder-data setup; separate from the four asymmetry fit coefficients',
        },
        'owner_pcr': {
            'path': 'edi/knowledge/fitting/fullprof/pd-neut-cwl_yap-spodi_3k/yap_3k.pcr',
            'sha256': hashlib.sha256(pcr.read_bytes()).hexdigest(),
            'header_line_1based': setting_line + 1,
            'AsyLim': limit,
            'asymmetry_codewords': codewords,
        },
        'upstream_peak_metadata': {
            'repository': 'https://github.com/easyscience/diffraction-lib',
            'commit': sha,
            'path': path,
            'sha256': hashlib.sha256(source).hexdigest(),
            'tagged_parameter_fields': fields,
            'limit_entry_present': False,
            'scope': 'Pinned per-category metadata defines four coefficients; it does not expose a limit entry or an explicit false flag for the limit',
        },
    }
    Path(__file__).with_name('limit_setting.json').write_text(json.dumps(record, indent=2) + '\n')
