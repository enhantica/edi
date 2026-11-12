# Calculation without data: La₀.₅Ba₀.₅CoO₃, HRPT

Nothing to fit: edi calculates from the model as the project holds it, as the Python tutorial does.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data pd-neut-cwl_lbco_simulation
    ```

=== "Python package"

    ```console
    python -m edi download-data pd-neut-cwl_lbco_simulation
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
