"""Generate independent saved-token hash projections; keep historical bytes unchanged."""

import json
from pathlib import Path

from tests.fixtures.report_units.saved_iucr import build_projections, projection_sources


def main():
    record = {
        'claim': 'Independent decimal save-token projection of immutable archived writer bytes',
        'sources': projection_sources(),
        'projections': build_projections(),
    }
    Path(__file__).with_name('saved-projections.json').write_text(
        json.dumps(record, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
