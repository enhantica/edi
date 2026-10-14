"""Copy a scan without saved start rows/results and print its common input digest."""

import hashlib
import pathlib
import shutil
import sys

src, dest = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
shutil.copytree(src, dest)
for name in ('results.csv', 'results-provenance.csv', 'scan-notes.csv', 'scan-run.json'):
    (dest / 'analysis' / name).unlink(missing_ok=True)
analysis = dest / 'analysis' / 'analysis.edi'
lines, out, i = analysis.read_text(encoding='utf-8').splitlines(keepends=True), [], 0
while i < len(lines):
    if (
        lines[i].strip() == 'loop_'
        and i + 1 < len(lines)
        and lines[i + 1].startswith('_fit_parameter.')
    ):
        i += 1
        while i < len(lines) and lines[i].strip():
            i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        continue
    out.append(lines[i])
    i += 1
analysis.write_text(''.join(out), encoding='utf-8')
digest = hashlib.sha256()
for path in sorted(p for p in dest.rglob('*') if p.is_file()):
    digest.update(path.relative_to(dest).as_posix().encode() + b'\0' + path.read_bytes())
print(digest.hexdigest())
