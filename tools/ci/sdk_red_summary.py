# SPDX-License-Identifier: BSD-3-Clause
"""Say which SDK tests failed, without what they compare.

    python3 tools/ci/sdk_red_summary.py EVIDENCE OUTPUT

The C++ tier's own reports hold the compared expressions, which are source. This keeps each failed
case's name, file and line, how many of its checks failed, and how a run ended otherwise.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - the reports are this job's own
from pathlib import Path


def failed(report: Path) -> list[dict[str, object]]:
    """The failed cases of one report."""
    found = []
    for case in ET.parse(report).getroot().iter('TestCase'):  # noqa: S314 - this job's own
        checks = [e for e in case.iter('Expression') if e.get('success') == 'false']
        ended = [e.tag for e in case.iter() if e.tag in {'Exception', 'FatalErrorCondition'}]
        if checks or ended:
            found.append({
                'case': case.get('name'),
                'file': Path(str(case.get('filename'))).name,
                'line': case.get('line'),
                'checks': sorted({
                    f'{Path(str(e.get("filename"))).name}:{e.get("line")}' for e in checks
                }),
                'ended': ended,
            })
    return found


def main() -> int:
    """Write the summary; a report that cannot be read is named, not copied."""
    evidence, output = Path(sys.argv[1]), Path(sys.argv[2])
    summary: dict[str, object] = {}
    for report in sorted(evidence.rglob('*.xml')) if evidence.is_dir() else []:
        try:
            cases = failed(report)
        except ET.ParseError:
            cases = [{'report': 'unreadable'}]
        if cases:
            summary[report.name] = cases
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
