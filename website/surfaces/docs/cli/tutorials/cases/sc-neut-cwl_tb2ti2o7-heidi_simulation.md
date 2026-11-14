# Calculation without data: Tb₂Ti₂O₇, HEiDi

Nothing to fit: edi calculates from the model as the project holds it, as the Python tutorial does.

Calculate the single-crystal neutron reflections of the pyrochlore Tb₂Ti₂O₇ on HEiDi at MLZ
without any measured data. The structure, the wavelength and the extinction are in the project,
and edi calculates every reflection up to the project's sin θ/λ limit.

The project is the catalogue case `sc-neut-cwl_tb2ti2o7-heidi_simulation`: the files the command
line calculates with
`python -m edi calc docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_simulation/project` and the app
opens from its Examples.

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
