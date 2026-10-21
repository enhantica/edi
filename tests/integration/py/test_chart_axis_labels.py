"""Pattern names are the axis-title names in the tooltip and legend too."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_tooltip_and_legend_names_follow_the_axis_vocabulary():
    source = (ROOT / 'core/src/presentation.cpp').read_text()
    for old in ('Imeas', 'Icalc', 'Ibkg'):
        present = '"' + old in source or '(' + old in source
        assert not present, 'Chart labels must use meas, calc and bkg without the I prefix'
    for label in (
        'Measured (meas)',
        'Total calculated (calc)',
        'Background (bkg)',
        'Residual (meas \u2212 calc)',
    ):
        assert '"' + label + '"' in source, 'The legend uses the stated axis-title name: ' + label


def test_data_table_declares_named_component_columns():
    sources = '\n'.join(path.read_text() for path in (ROOT / 'app/src').glob('*data*model*'))
    sources += '\n'.join(path.read_text() for path in (ROOT / 'app/src').glob('*experiment*'))
    exposed = 'component_intensities_net' in sources
    assert exposed, 'The data table shows each core component as a named numeric column'
