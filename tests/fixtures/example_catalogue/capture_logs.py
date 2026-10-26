"""Keep authoring logs publishable and bind their sanitized bytes in the receipts."""

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    'fullprof_public_scrub', ROOT / 'tools/public-release/scrub.py'
)
_SCRUB = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SCRUB)


def public_log(text):
    """Apply the canonical public-release rules without changing numerical output."""
    return _SCRUB.scrub_text(text.replace(str(ROOT), '<checkout>'), 'fullprof.log')


def copy_public_log(source, destination):
    """Publish an older or current capture through the same canonical scrub."""
    destination.write_text(public_log(source.read_text(errors='replace')))


def sanitize_references():
    """Sanitize retained logs and refresh only their log digests, without rerunning FullProf."""
    homes = [ROOT / f'knowledge/{kind}/fullprof' for kind in ['fitting', 'verification']]
    changed_logs = changed_receipts = 0
    for home in homes:
        for path in home.rglob('*.log'):
            original = path.read_text()
            sanitized = public_log(original)
            if sanitized != original:
                path.write_text(sanitized)
                changed_logs += 1
    for home in homes:
        for receipt in home.rglob('reference.json'):
            record = json.loads(receipt.read_text())
            changed = False
            for field in ['artifacts_sha256', 'twin_artifacts_sha256', 'fixed_twin_sha256']:
                if field not in record:
                    continue
                folder = receipt.parent
                if field in {'twin_artifacts_sha256', 'fixed_twin_sha256'}:
                    folder = homes[1] / folder.relative_to(homes[0])
                for name, previous in record.get(field, {}).items():
                    if not name.endswith('.log'):
                        continue
                    current = hashlib.sha256((folder / name).read_bytes()).hexdigest()
                    if current != previous:
                        record[field][name] = current
                        changed = True
            if changed:
                receipt.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
                changed_receipts += 1
    print(f'Sanitized {changed_logs} logs; refreshed {changed_receipts} receipts')


if __name__ == '__main__':
    sanitize_references()
