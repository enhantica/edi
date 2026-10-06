"""Append explicit Npr profile and linked-structure collection routes; preserve every prior row."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLASSES = {
    'CwlGaussian': 'CWL_GAUSSIAN',
    'CwlLorentzian': 'CWL_LORENTZIAN',
    'CwlPseudoVoigt': 'CWL_PSEUDO_VOIGT',
}
COMMON = (
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'cutoff_fwhm',
    'parameters',
    'show_supported',
    'type',
)

if __name__ == '__main__':
    path = ROOT / 'tests/unit/py/e09_t58_public_routes.txt'
    old = path.read_text()
    rows = dict(line.split('\t') for line in old.splitlines() if line and not line.startswith('#'))
    additions = []
    for owner, enum in CLASSES.items():
        members = COMMON + (('mixing_eta_0', 'mixing_eta_1') if owner == 'CwlPseudoVoigt' else ())
        for route in (
            owner,
            *(f'{owner}.{name}' for name in members),
            f'PeakProfileTypeEnum.{enum}',
        ):
            if route in rows and rows[route] != 'other-public':
                message = f'{route}: conflicting existing route classification'
                raise ValueError(message)
            if route not in rows:
                additions.append(f'{route}\tother-public\n')
    # Collection management is other-public, as with Structures/Experiments.
    collection_routes = (
        'LinkedStructures',
        *(
            f'LinkedStructures.{name}'
            for name in ('add', 'clear', 'create', 'items', 'keys', 'names', 'remove', 'values')
        ),
    )
    additions.extend(
        f'{route}\tother-public\n' for route in collection_routes if route not in rows
    )
    path.write_text(old + ''.join(additions))
