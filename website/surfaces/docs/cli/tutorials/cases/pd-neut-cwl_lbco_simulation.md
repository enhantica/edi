# Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT

Nothing to fit: edi calculates from the model as the project holds it, as the Python tutorial does.

Calculate a constant-wavelength neutron pattern of the cubic perovskite La₀.₅Ba₀.₅CoO₃ without
any measured data. The structure comes from EasyDiffraction's collection; the tutorial describes the
HRPT instrument, the peak profile, the background and the 2θ range, and edi calculates the pattern.

It builds the catalogue case `pd-neut-cwl_lbco_simulation` step by step: the same project the
command line calculates and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p pd-neut-cwl_lbco_simulation/structures pd-neut-cwl_lbco_simulation/experiments pd-neut-cwl_lbco_simulation/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name pd-neut-cwl_lbco_simulation
_metadata.title "La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI"
_metadata.description "Cubic perovskite · Simulated pattern without measured data"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lbco_simulation-lbco
    mv data/pd-neut-cwl_lbco_simulation-lbco.edi pd-neut-cwl_lbco_simulation/structures/lbco.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lbco_simulation-lbco
    mv data/pd-neut-cwl_lbco_simulation-lbco.edi pd-neut-cwl_lbco_simulation/structures/lbco.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lbco_simulation-hrpt
    mv data/pd-neut-cwl_lbco_simulation-hrpt.edi pd-neut-cwl_lbco_simulation/experiments/hrpt.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lbco_simulation-hrpt
    mv data/pd-neut-cwl_lbco_simulation-hrpt.edi pd-neut-cwl_lbco_simulation/experiments/hrpt.edi
    ```

Then write how the project is fitted in `analysis/analysis.edi`:

```edi
_edi.schema_version 3

_fitting_mode.type single

_minimizer.type crysta
```

## Calculate

Calculate the project without writing the result back (drop `--dry` to save it into the project). The output names what was calculated and a checksum of it; the time it took is left out here.

=== "Standalone executable"

    The standalone executable fits measured data only; use the Python package.

=== "Python package"

    ```console
    python -m edi calc pd-neut-cwl_lbco_simulation --dry
    ```

```text
schema=9
record=calc
n_points=3001
checksum=306349.4362
```

## Report

Write the HTML report of the project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report pd-neut-cwl_lbco_simulation --output pd-neut-cwl_lbco_simulation.html
    ```
