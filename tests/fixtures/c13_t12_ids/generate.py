"""authoring-only frozen fork-point saves, including all tracked directories."""

import hashlib
import importlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

BASES = {'crysta': '3b977af215ac9f04bba483426a9ea64ff181a183', 'edi': 'HEAD'}


def main():
    name = sys.argv[1]
    root = Path(__file__).resolve().parents[3] if len(sys.argv) == 2 else Path(sys.argv[2])
    destination = root / 'tests/fixtures/c13_t12_ids'
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'baseline.json').exists():
        message = ' baseline is a write-once fork-point freeze'
        raise RuntimeError(message)
    base = subprocess.check_output(
        [shutil.which('git'), '-C', str(root), 'rev-parse', BASES[name]], text=True
    ).strip()
    subprocess.run(
        [
            shutil.which('git'),
            '-C',
            str(root),
            'merge-base',
            '--is-ancestor',
            base,
            'main' if name == 'edi' else 'refs/remotes/origin/main',
        ],
        check=True,
    )
    engine = importlib.import_module(name)
    report = {
        'base': base,
        'engine': name,
        'command': 'python tests/fixtures/c13_t12_ids/generate.py ' + name,
        'artifact_sha256': hashlib.sha256(
            Path(sys.modules[name + '._' + name].__file__).read_bytes()
        ).hexdigest(),
        'candidates': [],
        'accepted': [],
    }
    with tempfile.TemporaryDirectory() as scratch:
        tree = Path(scratch) / 'input'
        tree.mkdir()
        with tarfile.open(
            fileobj=io.BytesIO(
                subprocess.check_output([shutil.which('git'), '-C', str(root), 'archive', base])
            )
        ) as source:
            source.extractall(tree, filter='data')
        # Enumerate ALL tracked directories, not only directories named project.
        directories = [tree, *sorted(p for p in tree.rglob('*') if p.is_dir())]
        with zipfile.ZipFile(
            destination / 'baseline.zip', 'x', compression=zipfile.ZIP_DEFLATED
        ) as frozen:
            for directory in directories:
                relative = directory.relative_to(tree).as_posix()
                try:
                    project = engine.Project.load(directory)
                except (RuntimeError, ValueError) as error:
                    report['candidates'].append({
                        'path_sha256': hashlib.sha256(relative.encode()).hexdigest(),
                        'load_error': str(error).replace(str(directory), '<candidate>'),
                    })
                    continue
                number = str(len(report['accepted']))
                row = {'path': relative, 'archive': number}
                report['candidates'].append({
                    'path_sha256': hashlib.sha256(relative.encode()).hexdigest(),
                    'accepted': True,
                })
                for path in sorted(p for p in directory.rglob('*') if p.is_file()):
                    frozen.write(path, number + '/input/' + path.relative_to(directory).as_posix())
                output = Path(scratch) / ('saved-' + number)
                try:
                    project.save_as(output)
                except (RuntimeError, ValueError) as error:
                    row['save_error'] = (
                        str(error).replace(str(tree), '<input>').replace(str(output), '<output>')
                    )
                else:
                    row['files'] = {}
                    for path in sorted(p for p in output.rglob('*') if p.is_file()):
                        filename = path.relative_to(output).as_posix()
                        row['files'][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
                        frozen.write(path, number + '/saved/' + filename)
                report['accepted'].append(row)
                print(name, relative, 'saved' if 'files' in row else row['save_error'], flush=True)
    (destination / 'baseline.json').write_text(json.dumps(report, indent=2) + '\n')
    print(
        'POPULATION',
        name,
        len(report['candidates']),
        'accepted',
        len(report['accepted']),
        flush=True,
    )


if __name__ == '__main__':
    main()
