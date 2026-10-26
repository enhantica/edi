"""Update LATP origin fields only after proving the complete prior input digest."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    path = HERE / 'oracle.js'
    text = path.read_text()
    oracle = json.loads(text.split('var frozen = ', 1)[1].removesuffix(';\n'))
    for row in oracle['projects']:
        if row['id'] not in {'pd-xray-cwl_latp_scan-4f', 'pd-xray-cwl_latp-bm01_scan'}:
            continue
        current = (ROOT / row['path'] / 'project.edi').read_bytes()
        previous = current
        for new, old in (
            (b'BM01 @ ESRF', b'BM01 @ SNBL'),
            (b'_metadata.facility "ESRF"', b'_metadata.facility "SNBL"'),
        ):
            if previous.count(new) != 1:
                raise ValueError('The LATP origin must have one exact title and facility')
            previous = previous.replace(new, old, 1)
        old_digest = hashlib.sha256(previous).hexdigest()
        if row['files']['project.edi'] != old_digest or text.count(old_digest) != 1:
            raise ValueError('Only the two declared metadata values may change before rebinding')
        text = text.replace(old_digest, hashlib.sha256(current).hexdigest(), 1)
    text = text.replace('BM01 @ SNBL', 'BM01 @ ESRF')
    text = text.replace('"_metadata.facility": "SNBL"', '"_metadata.facility": "ESRF"')
    path.write_text(text)


if __name__ == '__main__':
    main()
