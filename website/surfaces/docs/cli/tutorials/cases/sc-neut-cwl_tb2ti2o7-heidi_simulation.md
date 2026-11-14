# Calculation without data: Tb₂Ti₂O₇, HEiDi

Nothing to fit: edi calculates from the model as the project holds it, as the Python tutorial does.

Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ
without any measured data. The structure, the wavelength and the extinction are in the project,
and edi calculates every reflection up to the project's sin θ/λ limit.

It builds the catalogue case `sc-neut-cwl_tb2ti2o7-heidi_simulation` step by step: the same
project the command line calculates and the app's Examples open.

## Define the project

Make a folder for the project, with a folder each for its structures, experiments and analysis.

```console
mkdir -p sc-neut-cwl_tb2ti2o7-heidi_simulation/structures sc-neut-cwl_tb2ti2o7-heidi_simulation/experiments sc-neut-cwl_tb2ti2o7-heidi_simulation/analysis
```

Write `project.edi` in it with a text editor such as VS Code:

```edi
_edi.schema_version 3

_metadata.name sc-neut-cwl_tb2ti2o7-heidi_simulation
_metadata.title "Tb₂Ti₂O₇ [Fd-3m] · HEiDi @ MLZ (FRM II)"
_metadata.description "Single crystal · Calculated reflections without measured data"
_metadata.authors .
```

## Define the structure

Download the structure from EasyDiffraction's collection into `structures`. Its CIF gives the space group, the cell and the atom sites.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation-tb2ti2o7
    mv data/sc-neut-cwl_tb2ti2o7-heidi_simulation-tb2ti2o7.edi sc-neut-cwl_tb2ti2o7-heidi_simulation/structures/tb2ti2o7.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation-tb2ti2o7
    mv data/sc-neut-cwl_tb2ti2o7-heidi_simulation-tb2ti2o7.edi sc-neut-cwl_tb2ti2o7-heidi_simulation/structures/tb2ti2o7.edi
    ```

## Define the experiment

Download the experiment into `experiments`: the file declares the instrument, the peak profile, the background, the structures it links and the measured data.

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation-heidi
    mv data/sc-neut-cwl_tb2ti2o7-heidi_simulation-heidi.edi sc-neut-cwl_tb2ti2o7-heidi_simulation/experiments/heidi.edi
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation-heidi
    mv data/sc-neut-cwl_tb2ti2o7-heidi_simulation-heidi.edi sc-neut-cwl_tb2ti2o7-heidi_simulation/experiments/heidi.edi
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
    python -m edi calc sc-neut-cwl_tb2ti2o7-heidi_simulation --dry
    ```

```text
schema=9
record=calc
n_points=211
checksum=85237.83541
```

## Report

Write the HTML report of the project and open it in a browser.

=== "Standalone executable"

    The standalone executable has no `report`; use the Python package.

=== "Python package"

    ```console
    python -m edi report sc-neut-cwl_tb2ti2o7-heidi_simulation --output sc-neut-cwl_tb2ti2o7-heidi_simulation.html
    ```
