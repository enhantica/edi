"""Materialize literal ADR-0111 app witnesses without invoking either product."""

from pathlib import Path

from tests.fixtures.magnetic_pnma.uncertainty_states import STATES, texts


def generate():
    root = Path(__file__).parent / 'uncertainty-states'
    root.mkdir(exist_ok=True)
    for kind in STATES:
        structure, analysis = texts(kind)
        (root / (kind + '-structure.edi')).write_text(structure)
        (root / (kind + '-analysis.edi')).write_text(analysis)


if __name__ == '__main__':
    generate()
