"""Materialize the hand-authored fit-policy inputs for native and app consumers."""

from pathlib import Path

from inputs import materialize


def main():
    root = Path(__file__).resolve().parent / 'projects'
    cases = {
        'single': {},
        'cubic': {'cubic': True},
        'mixed': {'cubic': True, 'mixed': True},
        'powder': {'single': False},
        'unused': {'single': False, 'other': True},
        'disabled': {'single': False, 'enabled': False},
        'constrained': {'constraint': True},
        'cubic-constrained': {'cubic': True, 'constraint': True},
    }
    for name, options in cases.items():
        materialize(root / name, **options)


if __name__ == '__main__':
    main()
