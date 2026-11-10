"""Record the original owner's scan bytes; does not fit or generate expected output."""

import hashlib
import json
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
record = {
    'source': str(source),
    'files': {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(source.rglob('*'))
        if p.is_file()
    },
}
(Path(__file__).resolve().parent / 'scan-inputs.json').write_text(
    json.dumps(record, indent=2) + '\n'
)
