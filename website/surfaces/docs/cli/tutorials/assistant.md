# Fit with your own AI assistant

ChatGPT or Claude, in their desktop apps or command-line tools, can write an
EasyDiffraction project that `edi fit` fits. This page gives a prompt for the La₀.₅Ba₀.₅CoO₃
example of the [La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial.
The prompt links the documentation and the Command line tutorials, so the assistant can read how
EasyDiffraction is used, and it names the fit stages, so the project is fitted in the same order as
the tutorial.

## Get the two files

Download the structure and the measured pattern from EasyDiffraction's collection into one folder:

- [tutorial-lbco.cif](https://raw.githubusercontent.com/enhantica/edi-data/main/structures/tutorial-lbco.cif):
  the cubic perovskite, La and Ba sharing the corner site.
- [tutorial-hrpt.xye](https://raw.githubusercontent.com/enhantica/edi-data/main/data/tutorial-hrpt.xye):
  the HRPT pattern, 2θ in degrees, the counts and their standard uncertainties.

## Ask for the project

Start the assistant in that folder, or attach the two files to the chat, and give it this prompt:

```text
Fit the crystal structure of La0.5Ba0.5CoO3 to neutron powder diffraction data with
EasyDiffraction (edi).

Documentation: DOCS_BASE/ (a short index for assistants:
DOCS_BASE/llms.txt).
Worked examples: DOCS_BASE/cli/tutorials/ (choose the one closest to this task).

The two input files are in this folder:
- tutorial-lbco.cif: the structure, space group P m -3 m, La and Ba sharing one site.
- tutorial-hrpt.xye: the measured pattern, constant-wavelength neutrons on HRPT at PSI, wavelength
  1.494 Å; columns 2θ (degrees), counts and their standard uncertainties.

Create an EasyDiffraction project, ready for edi fit, that loads both files and fits the structure
in stages.
Each stage frees one more group of parameters and keeps the ones freed before it free:
1. the scale, the 2θ zero and the cell length a;
2. the background points;
3. the peak widths U, V, W and Y;
4. the isotropic displacements (B iso) of La, Ba, Co and O.
After stage 4, show the correlations. La's and Ba's B iso should move together almost exactly.
Constrain Ba's B iso to equal La's, and fit again.

After every fit, show the fitted parameters. At the end, give the reduced χ², Rwp and each fitted
value with its standard uncertainty.
```

The project it returns should fit with `edi fit`, from the
[standalone executable](../standalone.md) or the [<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python package</span>](../python.md){ .ed-icon-label .ed-interface-link }. Compare its final
values with the [La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial's: an assistant can pick other
starting values or miss a step, and the tutorial shows what each stage should give.

The same prompt, asking for a Jupyter notebook, is on the
[<span class="ed-interface-icons" aria-hidden="true">:simple-python:</span> <span class="ed-icon-text">Python</span>](../../python/tutorials/assistant.md){ .ed-icon-label .ed-interface-link } tutorials. The application has an
[AI assistant](../../user-guide/ai-assistant/index.md) built in.
