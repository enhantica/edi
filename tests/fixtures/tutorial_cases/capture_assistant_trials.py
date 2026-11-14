"""Export committed, authoring-time prompt trial evidence for portable passenger checks."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hub', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pending', action='store_true')
    parser.add_argument('--source-document', type=Path)
    args = parser.parse_args()
    document = {'source': None, 'records': []}
    if not args.pending:
        if (
            args.source_document is None
            or args.source_document.is_absolute()
            or '..' in args.source_document.parts
        ):
            parser.error('a relative --source-document is required unless --pending')
        relative = args.source_document.as_posix()
        source = subprocess.check_output(['git', '-C', str(args.hub), 'show', 'HEAD:' + relative])
        assert source == (args.hub / relative).read_bytes(), (
            'Trial evidence must be committed before export'
        )
        blocks = re.findall(r'```json\s*\n(.*?)\n```', source.decode(), re.DOTALL)
        records = [record for block in blocks for record in json.loads(block)]
        document = {
            'source': {
                'document': 'assistant-prompt-trials',
                'sha256': hashlib.sha256(source).hexdigest(),
                'commit': subprocess.check_output(
                    ['git', '-C', str(args.hub), 'rev-parse', 'HEAD'], text=True
                ).strip(),
            },
            'records': records,
        }
    args.output.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
