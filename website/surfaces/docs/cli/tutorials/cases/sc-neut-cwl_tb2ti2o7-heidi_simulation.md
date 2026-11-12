# Calculation without data: Tb₂Ti₂O₇, HEiDi

Nothing to fit: edi calculates from the model as the project holds it, as the Python tutorial does.

## Get the project

=== "Standalone executable"

    ```console
    edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation
    ```

=== "Python package"

    ```console
    python -m edi download-data sc-neut-cwl_tb2ti2o7-heidi_simulation
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
