# Documentation sources and adaptation

The interface-first site is the selected working design. Its content draws from the earlier
EasyDiffraction website, library and application documentation while describing current edi
behaviour. Source links appear at the end of the substantive guides.

## Source inventory

| Source | Revision inspected | Material used |
| --- | --- | --- |
| `easyscience/EasyDiffractionWww` | `c01095953d9be3d7c02ca67d231ab1b180385ed0` | `content/home.yaml` and `content/footer.yaml`: product introduction, scientific purpose, readable files and user entry points |
| `easyscience/diffraction-lib` | local documentation snapshot `0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf`; upstream master `c0654956a1281f1ea3f3467c3367167f93edee18` also inspected | `docs/docs/user-guide/`, workflow, glossary, parameters and formats; `quick-reference/` and introduction for the user-documentation progression |
| `easyscience/EasyDiffractionBeta` | `ec1d04ee36036dd092fdd8b779e99767afca6e5d` | README and earlier application workflow: visual analysis, model/pattern inspection, reporting and user-oriented entry points |
| `enhantica/edi` | `cea605412f4844abb9463ee2a01ba7cd97fd75ab`, also contained in the design baseline recorded by `EDI_SOURCE_COMMIT`; shipped-feature statements rechecked at `4c5946eae8679644cd7ab9680fc88b90d10113c8` (2026-11-01) | Current user guides, Python facade and bindings, argument parser, application controls and checked example catalogue |

Repository references:

- <https://github.com/easyscience/EasyDiffractionWww>
- <https://github.com/easyscience/diffraction-lib>
- <https://github.com/easyscience/EasyDiffractionBeta>
- <https://github.com/enhantica/edi>

The local library snapshot supplies conceptual material; the linked public guides may evolve on
master. Current edi instructions are checked against the recorded product snapshot, not inferred
by renaming the earlier library's import package.

## What was adapted

- **Home and Get started:** a screenshot-led product introduction, direct browser entry, interface
  selection, a first refinement and truthful setup/availability information.
- **Application:** the shared project-to-report progression, with actual current controls for
  structures, experiments, data intake, background, exclusions, fitting modes, scans and files.
- **Python:** the library guide's progression from a project to its structures, experiments,
  calculation, fit and results; examples use current factories, facade calls and report methods.
- **Command Line:** the same project-driven workflow, with the current `fit`, `calc`, `export`, `undo` and
  `report` commands and their persistence/reporting options.
- **User guide:** the generic introduction, concepts, glossary, formats, parameters and full
  Project → Structure → Experiment → Analysis → Report workflow, before the interface sections;
  fitting modes, interpretation and example selection are shared as well.
- **About:** product background, current licensing, support, contribution and citation guidance.

## Generation differences resolved

- The current calculation engine is crysta; the earlier CrysPy/CrysFML backend selection is not
  described as a current edi feature.
- Earlier downloadable releases and `pip install easydiffraction` instructions are not used to
  promise a distribution of the new `edi` library.
- The application calls its structural page **Structure**; older **Model** terminology is
  adapted to the current navigation.
- Browser persistence is described by browser and project origin: selected local writes in
  Chrome/Edge, browser-held projects and zip copies where those local handles are unavailable.
- `fit --dry` and `calc --dry` execute without saving; `undo --dry` previews a restoration.
  Archive inputs and output folders are explained separately.
- A Python calculation stores results on experiments; it does not return a new pattern object.
- PDF reporting is an application capability; Python/CLI report instructions describe the
  formats and methods they actually support.
- A historical release's DOI is not presented as a DOI for the current edi preview.

## Attribution and scope

The text is adapted and expanded for the current product. The library and Beta source licences
are retained in `third-party/`; branding provenance and its licence are recorded separately in
`DESIGN.md` and `BRANDING-LICENSE`. Website messaging is attributed to its source file; obsolete
download links, backend descriptions and release metadata are not reproduced as current claims.

Python examples have been checked against the source and parsed for syntax. They have not all
been executed against a newly built native edi environment as part of this documentation-only
preview. This is an expanded documentation draft, not a claim that every historical API page or
tutorial has been migrated or independently revalidated.

## Shared-guide adaptation — 2026-10-29

The user supplied the published `diffraction-lib/dev/introduction/` and `dev/user-guide/` pages.
The introduction was read online; the guide subroutes could not be fetched by the web reader,
so the Markdown source in the library snapshot above supplied the chapters.

| Earlier source | Current shared destination | Interface material retained elsewhere |
| --- | --- | --- |
| Introduction | `user-guide/introduction.md`; licensing/support/citation remain in About | Setup stays in Get started and the interface setup pages |
| Concept | `user-guide/concepts.md` | Buttons, methods and commands stay outside this page |
| Glossary | `user-guide/glossary.md` | No package-specific interpretation of the scientific terms |
| Data Format | `user-guide/data-formats.md` | Reader diagnostics and write-back rules remain with each interface |
| Parameters | `user-guide/parameters.md` and workflow Structure/Experiment/Analysis | Current Python access examples stay under Python; old access-path/key tables are not blindly ported |
| Analysis Workflow / Project | `user-guide/analysis-workflow/project.md` | App project controls, Python persistence and command output paths |
| Analysis Workflow / Structure | `user-guide/analysis-workflow/structure.md` | App fields and Python factories/parameter access |
| Analysis Workflow / Experiment | `user-guide/analysis-workflow/experiment.md` | Import actions, Python constructors and saved-project commands |
| Analysis Workflow / Analysis | `user-guide/analysis-workflow/analysis.md` | Fit controls, Python dispatch/callbacks and command flags |
| Analysis Workflow / Report | `user-guide/analysis-workflow/report.md` | Export controls, report methods and report command options |

The report chapter is corrected for current edi: saving a project does not write a report.
The earlier engine/plugin and Bayesian capability lists are not treated as current features.
This is a conceptual adaptation; it does not claim migration of every historical parameter
reference table, image or API tutorial.

## Homepage simplification — 2026-10-29

Home retains the product promise adapted from `EasyDiffractionWww/content/home.yaml` and the
existing unmodified edi application screenshot. It now contains only the introduction, web-app
and Get started actions, and screenshot. Interface selection remains in Get started; the common
workflow and task explanations remain in User guide; licensing and product background remain in
About. The composition takes inspiration from <https://zensical.org/> while using the requested
light design and real application image.

The native palette toggle and official dark-background wordmark were added with the landing
page update. The wordmark comes unchanged from `easydiffraction/logos/dark.svg` at branding
revision `46ab481bfe6d3b196f9609b17cd46cda7a0fadd8`; the existing branding licence covers it.
The application screenshot remains the original light-mode product image in both site modes.

The single adaptive wordmark is derived from the official light SVG: all geometry, gradient
colors and blue-symbol shapes are retained. Only the lettering group inherits `currentColor`;
gradient IDs are scoped to the header/drawer instances. The original light/dark source assets
are retained unchanged. The mobile drawer's separate site-name text is removed.

## Page-level authoring provenance

These source notes are retained for authors; they are not part of the published user pages.

- `user-guide/fit-quality.md`: [edi fit-quality definitions, comparison method and references](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md), [report guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md), [scan guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/sequential-fitting-in-the-app.md).

- `user-guide/fitting-modes.md`: [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), [scan workflow](https://github.com/enhantica/edi/blob/main/docs/user/guides/sequential-fitting-in-the-app.md).

- `user-guide/glossary.md`: [earlier glossary](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/glossary.md), [edi example catalogue](https://github.com/enhantica/edi/blob/main/docs/user/cli/index.md), [edi fitting workflow](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `user-guide/concepts.md`: [earlier library concepts](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/concept.md), [edi project model](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), [edi fit-quality guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md).

- `user-guide/examples/index.md`: [edi catalogue](https://github.com/enhantica/edi/blob/main/docs/user/cli/index.md), [LBCO example](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/index.md), [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py), [tutorial execution declaration](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/execution-exclusions.yml).

- `user-guide/parameters.md`: [earlier parameter guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/parameters.md), [edi project loading and free-set contract](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), [current example tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `user-guide/index.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/index.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `user-guide/data-formats.md`: [earlier data-format guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/data-format.md), [edi input workflow](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md), [complete-project contract](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), [opening and saving](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `user-guide/introduction.md`: [earlier introduction](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/introduction/index.md), [current product overview](https://github.com/enhantica/edi/blob/main/README.md), [complete-project model](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `python/reports.md`: adapted from [edi's report guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md) and verified against the [Report facade](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py). The separation between project and report follows the [earlier report workflow](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/report/).

- `python/calculate.md`: conceptual distinction adapted from the [earlier analysis guide](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/analysis/); current calls from [edi.Analysis](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py) and the [LBCO simulation tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco_simulation.py).

- `python/projects.md`: [opening, saving and exporting](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md) and [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md). Organization adapted from the [earlier project workflow](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/project/).

- `python/setup.md`: [edi package metadata](https://github.com/enhantica/edi/blob/main/pyproject.toml), [Pixi tasks](https://github.com/enhantica/edi/blob/main/pixi.toml), and [native extension loading](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py). The introductory progression follows the [earlier library first steps](https://docs.easydiffraction.org/lib/latest/user-guide/first-steps/).

- `python/examples/index.md`: [current example catalogue](https://github.com/enhantica/edi/blob/main/docs/user/cli/index.md), [LBCO example](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/index.md), and [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `python/index.md`: organization adapted from the [earlier library quick reference](https://docs.easydiffraction.org/lib/latest/quick-reference/); current calls checked against [edi's Python facade](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py) and [LBCO tutorial source](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `python/results.md`: current result access copied from the [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py), with interpretation adapted from [fit-quality guidance](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md) and the [earlier analysis workflow](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/analysis/).

- `python/reference.md`: layout adapted from the [earlier quick reference](https://docs.easydiffraction.org/lib/latest/quick-reference/); members checked against [edi's declared API](https://github.com/enhantica/edi/blob/main/data/python-surface.json), [Python facade](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py), and [project input/output guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `python/experiments.md`: organization adapted from the [earlier experiment guide](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/experiment/); current behavior from [ExperimentFactory](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py) and [projects from scratch](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md).

- `python/structures.md`: conceptual grouping adapted from the [earlier structure workflow](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/model/); examples checked against [edi factories](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py), [binding declarations](https://github.com/enhantica/edi/blob/main/lib/src/bindings.cpp), and the [LBCO example](https://github.com/enhantica/edi/blob/main/examples/fit_lbco_hrpt.py).

- `python/fit.md`: adapted from the [earlier analysis guide](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/analysis/), with current behavior from [edi.Analysis](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py), [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), and the [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `about/index.md`: [edi overview](https://github.com/enhantica/edi/blob/main/README.md), [product architecture](https://github.com/enhantica/edi/blob/main/docs/dev/adrs/0009-cpp-product-core-thin-bindings.md), [earlier library introduction](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/introduction/index.md).

- `about/licence.md`: [edi README licence statement](https://github.com/enhantica/edi/blob/main/README.md), [BSD 3-Clause licence](https://github.com/enhantica/edi/blob/main/LICENSE), [GPL version 3 text](https://github.com/enhantica/edi/blob/main/COPYING).

- `about/citation.md`: [earlier library citation guidance](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/introduction/index.md), [current project format](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [report contents](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md), [example comparisons and provenance](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md).

- `about/community.md`: [current source and issue tracker](https://github.com/enhantica/edi), [earlier project contribution guidance](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/introduction/index.md).

- `application/reports.md`: [current report guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md).

- `application/fitting-modes.md`: [current fitting-mode controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Analysis/FittingModeGroup.qml), [current scan guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/sequential-fitting-in-the-app.md), [current project-analysis contract](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `application/projects.md`: [current opening, saving and exporting guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `application/examples/index.md`: [current example catalogue](https://github.com/enhantica/edi/blob/main/docs/user/cli/index.md), [LBCO example](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/index.md), and [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `application/index.md`: [current project creation guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md), [current open/save guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [earlier workflow](https://github.com/easyscience/diffraction-lib/blob/develop/docs/docs/user-guide/analysis-workflow/index.md).

- `application/background.md`: [current background guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/background-estimate.md), [background controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Experiment/BackgroundGroup.qml), [excluded-region controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Experiment/ExcludedRegionsGroup.qml).

- `application/desktop.md`: [current desktop project-file guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [current application build tasks](https://github.com/enhantica/edi/blob/main/pixi.toml).

- `application/experiments.md`: [current experiment and data-import guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md), [current experiment controls](https://github.com/enhantica/edi/tree/main/app/qml/Pages/Experiment), [linked-structure controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Experiment/LinkedStructureGroup.qml), [earlier experiment concepts](https://github.com/easyscience/diffraction-lib/blob/develop/docs/docs/user-guide/analysis-workflow/experiment.md).

- `application/structures.md`: [current structure controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Structure/StructuresGroup.qml), [current space-group controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Structure/SpaceGroupGroup.qml), [current linked-structure controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Experiment/LinkedStructureGroup.qml), [earlier structure concepts](https://github.com/easyscience/diffraction-lib/blob/develop/docs/docs/user-guide/analysis-workflow/model.md).

- `application/workspace.md`: [earlier analysis workflow](https://github.com/easyscience/diffraction-lib/blob/develop/docs/docs/user-guide/analysis-workflow/index.md), [current fitting controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Analysis/FittingGroup.qml), [current project controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Project/GetStartedGroup.qml).

- `application/first-refinement.md`: [LBCO example and starting conditions](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/index.md), [Project page and examples](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Project/ProjectPage.qml), [saving projects](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `application/new-project.md`: [current create-project guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md), [structure file controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Structure/StructuresGroup.qml), [project file guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `application/browser.md`: [current web-project storage and file guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [current report guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md).

- `application/scans.md`: [current sequential-fitting guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/sequential-fitting-in-the-app.md).

- `application/refine.md`: [current parameter controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Analysis/ParametersGroup.qml), [current fitting controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Analysis/FittingGroup.qml), [current fitting-mode controls](https://github.com/enhantica/edi/blob/main/app/qml/Pages/Analysis/FittingModeGroup.qml), [current fit-quality guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/fit-quality.md).

- `get-started/interfaces.md`: [edi overview](https://github.com/enhantica/edi/blob/main/README.md), [opening, saving and exporting](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [Python facade](https://github.com/enhantica/edi/blob/main/lib/edi/__init__.py), [Command Line entry point](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py).

- `get-started/setup.md`: [edi platforms and licence](https://github.com/enhantica/edi/blob/main/README.md), [package metadata](https://github.com/enhantica/edi/blob/main/pyproject.toml), [Pixi tasks and SDK pin](https://github.com/enhantica/edi/blob/main/pixi.toml), [native SDK design](https://github.com/enhantica/edi/blob/main/docs/dev/adrs/0017-prebuilt-crysta-sdk.md).

- `get-started/first-refinement.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/index.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `cli/reports.md`: [current report guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md) and [report parser/execution](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py). The report's role follows the [earlier report workflow](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/report/).

- `cli/calculate.md`: [calc implementation and options](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py), [opening and output rules](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), and the calculation/refinement distinction from the [earlier analysis guide](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/analysis/).

- `cli/examples/index.md`: [current example catalogue](https://github.com/enhantica/edi/blob/main/docs/user/cli/index.md), [LBCO example](https://github.com/enhantica/edi/blob/main/docs/user/cli/pd-neut-cwl_lbco-hrpt/index.md), and [LBCO tutorial](https://github.com/enhantica/edi/blob/main/docs/user/tutorials/pd-neut-cwl_lbco-hrpt.py).

- `cli/index.md`: current commands and defaults from [edi's argument parser](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py), [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), and [project input/output](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `cli/batch.md`: the shell composition is new for this preview; command behavior is checked against [edi's Command Line](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py). Scan semantics come from [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `cli/reference.md`: syntax, defaults and behavior checked directly against [the current edi parser and command implementations](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py). This is a selected user reference; the installed command's help remains the version-specific option listing.

- `cli/files.md`: [project input/output guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md), [current Command Line input handling](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py), and [project-output design](https://github.com/enhantica/edi/blob/main/docs/dev/adrs/0039-project-output.md).

- `cli/fit.md`: [fit parser and execution](https://github.com/enhantica/edi/blob/main/lib/edi/__main__.py), [complete-project loading](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md), and [project archives](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md). The model-driven workflow follows the [earlier analysis guide](https://docs.easydiffraction.org/lib/latest/user-guide/analysis-workflow/analysis/).

- `user-guide/analysis-workflow/project.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/project.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/open-save-and-export.md).

- `user-guide/analysis-workflow/index.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/index.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `user-guide/analysis-workflow/analysis.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/analysis.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/complete-project-loading.md).

- `user-guide/analysis-workflow/structure.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/model.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md).

- `user-guide/analysis-workflow/experiment.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/experiment.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/projects-from-scratch-in-the-app.md).

- `user-guide/analysis-workflow/report.md`: [earlier library guide](https://github.com/easyscience/diffraction-lib/blob/master/docs/docs/user-guide/analysis-workflow/report.md), [current edi guide](https://github.com/enhantica/edi/blob/main/docs/user/guides/the-report.md).

## Public Physics and standalone presentation — 2026-10-29

The public Physics pages use IUCr's Bragg-law and structure-factor definitions, published
peak-profile explanations, IUCr displacement-parameter definitions and edi's documented
agreement-factor equations. Scientific references remain visible on their topic pages. The
public navigation and prose describe EasyDiffraction directly; historical authoring provenance
is retained here instead of in per-page migration or source footers.

Nunito was identified from the live easydiffraction.org `css/style.min.css`, whose font import
requests Nunito 400, 500, 600, 700 and 800. The selected homepage uses the same Google Fonts
family; the font is not vendored or republished in this repository.

## Physics and interface availability snapshot (2026-10-29)

- Inspected edi source: `56457f29c82d0209e7845a0b4658155938cb5630`; its platform SDK declarations pin crysta `188234833fe069d760ea6b59c372c2740461b09f`. Production `data/dictionary/parameters.tsv`, `include/crysta/peaks/`, `src/core/{cwl_profile,tof_profile,cwl_absorption,extinction_formula}.hpp`, `structure_factor.cpp`, `weight_fraction.cpp`, `fit_quality.cpp`, `single_crystal.cpp` and the residual/minimizer code fix the documented equations and conventions. A research description is not a capability claim.
- Refreshed 2026-11-01: edi `4c5946eae8679644cd7ab9680fc88b90d10113c8` and crysta `f202da63edf4bd128c91dbe12908107712aa2e4f`, which has the same source tree as the SDK build `build-8ba9537cc90857afeedf768693f70635f607ee36` that edi pins. The public catalogue records these two commits. Every catalogue parameter was compared with crysta `data/dictionary/parameters.yaml`; only `extinction.crystal_radius` changed, now `refinable: false`. CIF import of structures and experiments, the fittability rule, CIF reports, the status-bar Fit button, the scan views, the Text tab and report write-back were checked against edi `lib/`, `core/src/`, `app/qml/`, `app/src/` and `docs/user/guides/`.
- Interface coverage: edi `lib/edi/__init__.py`, `lib/edi/__main__.py`, QML Experiment groups (`PeakGroup`, `InstrumentGroup`, `AbsorptionGroup`, `ExtinctionGroup`, `PreferredOrientationGroup`), Structure ADP controls, Analysis/Report controls and current `docs/user/guides/`. Distinguish explicit editing from executing a saved project. The product-side `docs/dev/features.md` is stale and was not used as a status source. Static source inspection does not replace runtime validation of each platform/model combination.
- Planned/proposed states: the project's roadmap as of 2026-10-29, which lists them as planned or draft. No in-progress claim was inferred from a planned entry.
- Formula provenance: scientific papers and IUCr definitions are cited on their topic pages. The knowledge book supplied authoring context, not a current support declaration. No private book corpus or PDFs are published. The implemented finite limits and units take precedence over differently parameterised comparison libraries.
- MathJax 3.2.2 `tex-svg-full.js` is vendored from the official npm distribution; Apache-2.0 notice is retained in `third-party/MathJax-LICENSE`. Only Physics pages load the renderer. The plain Markdown export is derived from the same authored pages during the build; it does not establish a completed chat integration.

## Feature-page navigation references

The owner requested smaller hierarchical capability tables and checkbox/icon states, following the former diffraction-lib feature-page organization. The 2026-10-29 redesign uses Structure model, Experiment model, Analysis and refinement, Projects and results, and Planned work, with topic subsections. Native Zensical table/TOC styling is retained. PhaseSmith's workflow-versus-model reference organization and RietX's task-oriented feature summaries were inspected as information-architecture references (https://phasesmith.readthedocs.io/en/latest/ and https://rietx.org/); no competitor capabilities were copied into the EasyDiffraction support claims.

The full local MathJax bundle includes TeX extensions needed by the reference, including boldsymbol. The smaller bundle attempted to fetch unvendored extension files and prevented ADP-page typesetting; the rendering check now covers every Physics page and every math wrapper. Bibliographies use numbered entries, separate from related documentation links.

Feature status icons reuse the filled Twemoji artwork from the [original library Features page](https://easyscience.github.io/diffraction-lib/dev/features/). The checked/limited/calendar graphics are the same Twemoji 16.0.1 SVGs; the matching proposed/work-in-progress graphics use that version too. Local unchanged copies live under `surfaces/overrides/.icons/status`, including the upstream CC BY 4.0 graphics licence. The existing Zensical emoji extension inlines these SVGs, so there is no CDN or emoji-font dependency. Unavailable uses Zensical's bundled Material cancel icon, as on the original page. Status meanings, accessible qualifications and scientific links are preserved.

## Owner-supplied animated network (2026-10-29)

Source: `easydiffraction-network-handoff.zip`, supplied in this conversation. The approved SVG is inlined in `surfaces/overrides/partials/network.svg`, with accessibility/class attributes added at its root. Its path definitions, stroke values and opacity attributes are preserved. The supplied `network-pulse-engine.js` is the starting implementation of `surfaces/docs/assets/network-pulse-engine.js`; integration adds offscreen suspension, full-width/responsive bank placement and component lifecycle cleanup. The CSS is scoped to the homepage. The preview HTML/GIF are authoring references, not shipped page content or runtime dependencies.

Home hero screenshot replaced with the owner-supplied `Screenshot 2026-10-29 at 19.14.21.png`, copied unchanged to `assets/edi-analysis-hero.png`. The previous experiment screenshot remains in the relevant documentation pages.

The global accent `#0084C7` is the dominant non-antialiased blue sampled from the owner-supplied colour reference `Screenshot 2026-10-29 at 19.15.49.png` using a read-only browser Canvas pixel count (`/tmp/edi-sample-accent.py`). No image recolouring was performed.
