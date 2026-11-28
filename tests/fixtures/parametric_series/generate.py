"""Write the authored three-experiment project consumed by the GUI actor."""

from pathlib import Path

from tests.fixtures.parametric_series.cases import model

if __name__ == '__main__':
    model(Path(__file__).parent / 'project')
