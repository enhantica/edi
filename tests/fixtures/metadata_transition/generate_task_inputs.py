"""Archive the exact committed C18 input edits without replacing older byte oracles."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
# f0c571c13 / e49ae39ac: one owner-declared exception, exact scalar replacement.
YALO3 = 'docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project/analysis/analysis.edi'
DECISIONS = {
    '3f7ec02e4': ('docs/user/cli/*/project/analysis/analysis.edi', 'declared Shift/s.u. start'),
    'b9bdbf9a2': ('docs/user/cli/*/project/experiments/d20.edi', 'declared fixed scan Y'),
}


def committed(revision, name):
    return subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)


def main():
    rows = {}
    content = {}
    for revision, (pattern, reason) in DECISIONS.items():
        names = subprocess.check_output(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', revision, '--', pattern],
            cwd=ROOT,
            text=True,
        ).splitlines()
        for name in names:
            before, after = (committed(r, name) for r in (revision + '^', revision))
            if revision == '3f7ec02e4':
                added = b'_minimizer.stop_rule shift_su\n'
                assert after.count(added) == 1 and after.replace(added, b'', 1) == before, (
                    'The stop-rule transition adds only its declared scalar and no other byte'
                )
            else:
                old = b'0.017548()' if '_scan-213f/' in name else b'0.01()'
                old = b'_peak.broad_lorentz_y ' + old + b'\n'
                new = b'_peak.broad_lorentz_y 0.0114\n'
                assert before.count(old) == 1 and before.replace(old, new, 1) == after, (
                    'The scan transition changes only its declared Y value and free flag'
                )
            source_revision, source_reason = revision, reason
            if name == YALO3:
                returned = committed('e49ae39ac', name)
                assert (
                    after.replace(
                        b'_minimizer.stop_rule shift_su\n',
                        b'_minimizer.stop_rule chi_square_change\n',
                        1,
                    )
                    == returned
                ), 'The yalo3 exception changes only its exact stop-rule scalar'
                after = returned
                source_revision = 'e49ae39ac'
                source_reason = 'f0c571c13: yalo3 retains the chi-square-change stop rule'
            assert (ROOT / name).read_bytes() == after, (
                'Only the complete committed current replacement can enter this input archive'
            )
            hashes = [hashlib.sha256(data).hexdigest() for data in (before, after)]
            rows[name] = {
                'before_sha256': hashes[0],
                'after_sha256': hashes[1],
                'source_commit': source_revision,
                'reason': source_reason,
            }
            content.update(zip(hashes, (before, after), strict=True))
    with zipfile.ZipFile(HERE / 'task-inputs.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, data in sorted(content.items()):
            info = zipfile.ZipInfo(digest, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    (HERE / 'task-inputs.json').write_text(json.dumps({'files': rows}, indent=2) + '\n')
    print('Archived exact committed input transitions:', len(rows))


if __name__ == '__main__':
    main()
