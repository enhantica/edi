"""Independent bank-category reader; unrelated large correlation loops stay opaque."""

import gemmi

from tests.fixtures.cif2 import read_block

REQUIRED = {
    '_fit_result_bank.experiment_id',
    '_fit_result_bank.n_data_points',
    '_fit_result_bank.prof_wr_factor',
    '_fit_result_bank.prof_r_factor',
    '_fit_result_bank.prof_wr_expected',
    '_fit_result_bank.prof_cr_factor',
    '_fit_result_bank.prof_cwr_factor',
    '_fit_result_bank.chi_square',
}


def read_banks(path):
    block = read_block('data_analysis\n' + path.read_text())
    result = []
    for item in block:
        loop = item.loop
        if loop is None or not any(t.startswith('_fit_result_bank.') for t in loop.tags):
            continue
        tags, values = list(loop.tags), loop.values
        assert set(tags) >= REQUIRED, 'Every bank result must retain its declared metric columns'
        assert len(tags) == len(set(tags)), 'Bank metric column identities must be unique'
        for offset in range(0, len(values), len(tags)):
            row = [gemmi.cif.as_string(t) for t in values[offset : offset + len(tags)]]
            assert len(row) == len(tags), 'Persisted bank rows must have complete cardinality'
            result.append(dict(zip(tags, row, strict=True)))
    return result
