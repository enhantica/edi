# Example refinement from the Command Line

[Download the example project](../assets/interfaces/example-project.zip) and extract it. Open a terminal in the containing folder, using your [standalone executable](standalone.md) or [Python package environment](python.md).

## Run without saving

<!-- example:cli -->
=== "Standalone executable"

    ```console
    edi fit pd-neut-cwl_y2o3-spodi --dry
    ```

=== "Python package"

    ```console
    python -m edi fit pd-neut-cwl_y2o3-spodi --dry
    ```
<!-- /example -->

The supplied example converges with the following output:

```text
edi fit: project pd-neut-cwl_y2o3-spodi, 2509 pts fitted / 3060 loaded, 43 free
   iter   time (s)   Rwp (%)  reduced χ²   change
                       13.88      127.71
      1       0.03      1.45        1.39   98.9% ↓
      2       0.04      1.35        1.20   13.6% ↓
      3       0.09      1.34        1.20   0.1% ↓
      4       0.11      1.34        1.20
      5       0.15      1.34        1.20
  done · converged · 5 iters · reduced χ² 1.20 · Rwp 1.34 % · 0.2 s
```

`--dry` runs the refinement and leaves the starting files unchanged.

## Save the result

=== "Standalone executable"

    ```console
    edi fit path/to/project --output refined-project
    ```

=== "Python package"

    ```console
    python -m edi fit path/to/project --output refined-project
    ```

Replace `path/to/project` with the extracted example folder. See [Run a refinement](fit.md) for progress, output and cancellation options.
