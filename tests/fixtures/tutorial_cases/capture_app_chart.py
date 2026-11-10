"""Capture app-only hover/style services as labelled UI regression pins, with input custody."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def tree_hash(root):
    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = subprocess.run(
        [str(args.probe.resolve()), str(args.project.resolve())],
        capture_output=True,
        text=True,
        check=True,
    )
    document = json.loads(result.stdout)
    root = Path(__file__).resolve().parents[3]
    sources = [
        'app/qml/Components/PatternChart.qml',
        'app/src/pattern_chart_controller.cpp',
        'app/qml/Style/AppColors.qml',
        'core/include/edi/presentation.hpp',
    ]
    document['source'] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources
    }
    document['project_tree_sha256'] = tree_hash(args.project)
    document['case'] = args.project.parent.name
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
