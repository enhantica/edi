"""Generate the independent unequal-start shared-codeword FullProf witness."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

SOURCE_HASH = '9415ada4e3fac864f0269e5de8cb0859a84ff25df1e5f1bdf62fa65f373a211c'
DATA_HASH = '22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f'
ENGINE_HASH = 'b8cb5cdb00ef55f2fef9004ef070324a459f2fcc92ad5c4613f2ea06118c9f1f'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--fp2k', type=Path, required=True)
    args = parser.parse_args()
    source, out, engine = (p.resolve() for p in (args.source_dir, args.output_dir, args.fp2k))
    if digest(source / 'full-fit.inp') != SOURCE_HASH or digest(source / 'cosio.dat') != DATA_HASH:
        raise ValueError('requires the frozen independent FullProf source/data')
    if digest(engine) != ENGINE_HASH:
        raise ValueError('requires the declared native FullProf 8.40 binary')
    out.mkdir(parents=True, exist_ok=False)
    lines = (source / 'full-fit.inp').read_text().splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith('Co1 ')]
    if len(matches) != 1 or '0.98759' not in lines[matches[0]]:
        raise ValueError('independent Co1 starting value is not uniquely present')
    lines[matches[0]] = lines[matches[0]].replace('0.98759', '0.01000', 1)
    (out / 'affine.pcr').write_text('\n'.join(lines) + '\n')
    shutil.copyfile(source / 'cosio.dat', out / 'affine.dat')
    result = subprocess.run(
        [str(engine)],
        input=b'affine\n\n',
        cwd=out,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=25,
    )
    (out / 'native-run.log').write_bytes(result.stdout)
    if result.returncode not in {0, 24} or b'Normal end' not in result.stdout:
        raise RuntimeError('native FullProf did not reach Normal end; inspect native-run.log')
    files = ['affine.pcr', 'affine.dat', 'affine.new', 'affine.prf', 'affine.sum', 'affine.out']
    provenance = {
        'schema': 'independent-fullprof-affine/1',
        'engine_version': 'FullProf.2k 8.40 Feb2026-ILL JRC',
        'executable': str(engine),
        'executable_sha256': digest(engine),
        'source_sha256': SOURCE_HASH,
        'data_sha256': DATA_HASH,
        'source_edit': 'Co1 Biso start 0.98759 -> 0.01000; shared codeword181 unchanged',
        'process_exit': result.returncode,
        'completion': 'Normal end; final interactive EOF may return24',
        'files': {
            name: {'sha256': digest(out / name), 'bytes': (out / name).stat().st_size}
            for name in files
        },
    }
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    main()
