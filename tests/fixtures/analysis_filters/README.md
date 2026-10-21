The project contains two triclinic P1 structures with one and two general sites,
and two CW experiments with two and three polynomial coefficients. P1 leaves
all six cell parameters and all five listed parameters per site independent.
The links and background rows use distinct string ids. Free and fixed fields
coexist in every block.

`python tests/fixtures/analysis_filters/generate.py` parses the saved files with
Python's tokeniser and an explicit list of their physical parameter fields.
It imports neither engine nor app. `expected.json` records every identity and
free flag, rather than copying app counts. Background order, polynomial origin,
peak cutoff and measured samples are settings or observations, not fit parameters.

The file parser yields the following counts (`expected.json`, reproduced by the
command above). Each structure has six cell parameters plus five per site. Each
experiment has five peak coefficients, two instrument parameters, two structure
scales and its declared background coefficients.

| Datablock | Parameters | Free |
| --------- | ---------: | ---: |
| amber     |         11 |    2 |
| violet    |         16 |    3 |
| east      |         11 |    4 |
| west      |         12 |    5 |

The same parser writes `ncaf.json` from the committed `fit_tables/five` project.
Its declared I 21 3 setting has one independent cubic cell length. The saved
Wyckoff forms of Ca1, Al1, Na1 and F3 each have one coordinate; F1 and F2 have
three. Those forms leave ten coordinates, six occupancies, six isotropic
displacements and one cell length: 23 structure parameters. The explicit
fixture-specific constraints omit dependent y/z and cell fields before counting;
neither engine supplies a count. Each bank retains its declared TOF profile,
calibration, absorption, structure scale and background-intensity fields.
