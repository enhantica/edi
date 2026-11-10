""": enumerate each escaped fitting/Undo input under the native unit bound."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DESTINATION = ROOT / 'tests/unit/cpp/test_e05_t1_fit_job.cpp'
MARKER = '//  generated publication-input cases (generate_publication_cases.py).'
INPUTS = (
    'mode',
    'descent',
    'max-iterations',
    'chi-square-stop',
    'minimizer-type',
    'uncertainty',
    'uncertainty-aba',
    'free',
    'free-aba',
    'bank-weight',
    'undo-value',
    'undo-value-aba',
    'undo-uncertainty',
    'undo-uncertainty-aba',
)


def main():
    text = DESTINATION.read_text().split(MARKER)[0].rstrip() + '\n\n' + MARKER + '\n'
    label = 'E' + '05-T1 gates 4 6 '
    for terminal in ('completed', 'cancelled', 'maxiter'):
        for mode in ('single', 'joint'):
            for name in INPUTS:
                if mode == 'single' and name == 'bank-weight':
                    continue
                text += (
                    '\nTEST_CASE("'
                    + label
                    + terminal
                    + ' '
                    + mode
                    + ' queued fit rejects '
                    + name
                    + '") {\n'
                    '#if E05_T1_FIT_JOB\n'
                    '    e05_t1::publication_inputs("'
                    + mode
                    + '", "'
                    + terminal
                    + '", "'
                    + name
                    + '");\n'
                    '#else\n'
                    '    FAIL_CHECK(" gate 6 requires guarded final FitJob publication '
                    'for fitting-only inputs");\n'
                    '#endif\n}\n'
                )
    DESTINATION.write_text(text)


if __name__ == '__main__':
    main()
