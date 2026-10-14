"""Verify the nightly paired adaptive scan's complete Start-through-Reset evidence."""

import json
import os
from pathlib import Path

from tests.fixtures.scan_pair.measure import context
from tests.fixtures.scan_pair.oracle import paired


def test_adaptive_162_file_end_to_end_time_is_within_five_percent_of_c22_t26():
    location = os.environ.get('EDI_SCAN_PAIR_EVIDENCE')
    assert location, (
        'Nightly scan timing must supply the actually produced paired evidence artifact'
    )
    path = Path(location)
    assert path.is_file(), (
        'Missing paired timing evidence must fail instead of skipping performance'
    )
    document = json.loads(path.read_text(encoding='utf-8'))
    paired(document, context())
