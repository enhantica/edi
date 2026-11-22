"""Freeze the unconstrained writer regression and renew its shipped project block."""

import argparse
import hashlib
import importlib
import json
import re
import runpy
import tempfile
from pathlib import Path

from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.fitting_modes.historical_bytes import historical_analysis
from tests.fixtures.project_categories.historical_bytes import prior_digest
from tests.fixtures.report_units.iucr_reference import without_default_rule
from tests.fixtures.table_display.stored_id_bytes import ordinal_copy
from tests.fixtures.weight_fractions.single_phase_bytes import historical_single_fraction


def snapshot(root, *, historical_fractions=False, order_reference=None):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if not path.is_file():
            continue
        content = original_tokens(path.read_bytes())
        if historical_fractions:
            content = historical_single_fraction(path.relative_to(root).as_posix(), content)
        if path.name == 'project.edi':
            content = re.sub(
                rb'(?m)^(_metadata\.(?:created|last_modified)\s+).+$', rb'\1<CLOCK>', content
            )
        name = path.relative_to(root).as_posix()
        result[name] = (
            hashlib.sha256(content).hexdigest()
            if order_reference is None
            else prior_digest(content, order_reference.get(name), name=name)
        )
    return result


def legacy_writer_copy(source, saved, destination):
    legacy = ordinal_copy(source, saved, destination)
    analysis = legacy / 'analysis/analysis.edi'
    analysis.write_bytes(historical_analysis(source, analysis.read_bytes()))
    record = legacy / 'project.edi'
    record.write_bytes(without_default_rule('project.edi', record.read_bytes()))
    return legacy


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine')
    parser.add_argument('--project-block-only', action='store_true')
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parent
    pin = fixture / 'unconstrained_regression.json'
    engine = importlib.import_module(args.engine)
    materialize = runpy.run_path(str(fixture / 'project.py'))['materialize']
    with tempfile.TemporaryDirectory(prefix='constraint-writer-') as scratch:
        work = Path(scratch)
        source = materialize(work / 'input')
        project = engine.Project.load(source)
        project.save_as(work / 'saved')
        if args.project_block_only:
            expected = json.loads(pin.read_text())
            legacy = legacy_writer_copy(source, work / 'saved', work / 'ordinal-pin')
            result = snapshot(legacy, historical_fractions=True, order_reference=expected)
            block = 'project.edi'
            if block not in result or (
                {name: digest for name, digest in result.items() if name != block}
                != {name: digest for name, digest in expected.items() if name != block}
            ):
                raise ValueError('The project-block renewal requires every other pin to match')
        else:
            result = snapshot(work / 'saved')
    pin.write_text(json.dumps(result, indent=2) + '\n', newline='\n')
