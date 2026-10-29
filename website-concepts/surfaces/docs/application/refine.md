# Refine a diffraction pattern

Start with a project whose structure and experiment describe your measurement. The refinement adjusts the parameters you choose so that the calculated pattern approaches the measured pattern.

## Load a project

Use **Project** to open a saved project or an included example. An example includes the structure, measured data and starting conditions for that case.

## Inspect the experiment

On **Experiment**, compare the measured and calculated patterns. Check the peak profile, background, excluded regions and linked structures before fitting.

![Measured and calculated diffraction patterns](../assets/edi-app.png)

## Select free parameters

On **Analysis**, inspect the parameter table. Enable variation for the parameters you intend to refine. A parameter fixed by symmetry or tied to another value should be understood before trying to change it.

## Run the fit

Start fitting and review the result. Look at the pattern and residual as well as the reported agreement factors. Parameter uncertainties and correlations help explain what the data constrain.

## Review and save

Save the project to keep its updated values. Use the **Report** page to prepare a separate document for sharing.

## Continue in another interface

The same saved project can be [loaded in Python](../python/fit.md) or [run from the command line](../cli/fit.md). The structures and experiments do not need to be recreated.
