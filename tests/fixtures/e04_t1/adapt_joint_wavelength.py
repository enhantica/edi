"""Keep the joint example's source oracle aligned with its fixed reference wavelength."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
PROJECT = 'docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project'
RELATIVE = 'experiments/d1a.edi'


def main():
    name = PROJECT + '/' + RELATIVE
    before, after = [
        subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        for commit in ('09a40bdc^', '09a40bdc')
    ]
    assert before.count(b'_instrument.setup_wavelength 1.91()\n') == 1, (
        'The committed joint correction has one explicit free wavelength'
    )
    assert (
        before.replace(
            b'_instrument.setup_wavelength 1.91()\n', b'_instrument.setup_wavelength 1.91\n'
        )
        == after
        == (ROOT / name).read_bytes()
    ), 'The joint reference correction changes only the wavelength free flag'
    old_hash, new_hash = [hashlib.sha256(data).hexdigest() for data in (before, after)]
    for filename in ('oracle.js', 'display_oracle.js'):
        path = HERE / filename
        header, data = path.read_text().split('var frozen = ', 1)
        frozen = json.loads(data.removesuffix(';\n'))
        if filename == 'oracle.js':
            corpus = next(
                row
                for row in frozen['corpus']
                if row['project'] == PROJECT and row['experiment'] == 'd1a'
            )
            project = next(row for row in frozen['projects'] if row['path'] == PROJECT)
            assert corpus['sha256'] == project['files'][RELATIVE] == old_hash, (
                'The source adaptation starts at the frozen pre-correction joint bytes'
            )
            wavelength = corpus['scalars']['_instrument.setup_wavelength']
            assert wavelength == {'value': 1.91, 'free': True, 'uncertainty': None}, (
                'The old wavelength witness agrees with the independently committed input'
            )
            wavelength.update(free=False, uncertainty=0.0)
            corpus['sha256'] = project['files'][RELATIVE] = new_hash
        else:
            assert frozen['sources'][name] == old_hash, (
                'The display source adaptation starts at the exact old joint source hash'
            )
            frozen['sources'][name] = new_hash
        path.write_text(
            header
            + 'var frozen = '
            + json.dumps(frozen, indent=2, ensure_ascii=filename == 'display_oracle.js')
            + ';\n'
        )


if __name__ == '__main__':
    main()
