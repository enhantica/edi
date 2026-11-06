# ADR-0014: Font Awesome 5.15.4 as the site's icon set

Date: 2026-11-07
Status: accepted

## Prior art

The application draws its symbols from Font Awesome 5 Free Solid 5.15.4, loaded from its GUI components base; on 2026-11-07 that font and the site's copy had the same SHA-1 (`1fb67360`). The site mixed three sets: Lucide for interfaces and setup pages, Material Design for workflow stages (ADR-0002) and page groups, and the Font Awesome 5.15.4 font for parameter and category icons (ADR-0010). The same step could therefore look different on the site and in the application; Structure was a puzzle piece on the site and `layer-group` in the application.

## Decision

Use Font Awesome 5.15.4 Solid for every symbol the site chooses, and use the application's symbol wherever the application has one. This replaces the icon choices of ADR-0002 and is the current choice; moving to a newer Font Awesome would be a later decision made together with the application.

The font `assets/gui-icons/fontawesome-5-solid.otf` remains the single source. `render_fa5_icons.py` extracts the needed glyphs as SVG files into `overrides/.icons/fa5/`, so navigation, diagrams and page text keep using the theme's ordinary icon mechanism (`:fa5-name:` and `fa5/name`). ADR-0010's direct font glyphs stay as they are, as they draw the same font. The SVG files are committed because the site build does not depend on fontTools.

Zensical also bundles Font Awesome 7.3.1 as SVG. It is not used: names mostly match, but `vector-square` is missing and drawings may differ from the application's, and a theme update could change them.

## Exceptions

- Brand logos stay in their own sets, because Solid has none: Python and Jupyter (`simple`), browsers and download platforms (`fontawesome/brands`).
- Theme controls that belong to Zensical, such as the light and dark toggle, are not site symbols and are unchanged.

## Mapping

| Where | Symbol | In the application |
| --- | --- | --- |
| Project, Experiment, Analysis | `archive`, `microscope`, `calculator` | The same page tabs |
| Structure, Report | `layer-group`, `clipboard-list` | The same page tabs |
| Home | `home` | Page tab |
| Web application | `globe` | Used |
| AI assistant | `robot` | The assistant button |
| Application layout, sidebar area | `columns` | Used |
| Filter, compare, download | `filter`, `exchange-alt`, `download` | Used |
| Desktop application and main area | `desktop` | Not used; closest meaning |
| Command Line | `terminal` | Not used; closest meaning |
| Navigation and status areas | `window-maximize`, `window-minimize` | Not used; closest meaning |
| Foundations pages | `clipboard-check`, `lightbulb`, `file-code`, `sliders-h`, `book` | Not used; closest meaning |
| Physics groups, reference pages | `chart-area`, `chart-line`, `sliders-h`, `book`, `book-open`, `route` | Partly used |
| Unavailable feature | `times-circle` | Used |

## Validation

`_check_icons` in `build.py` fails on a Material, Lucide, Octicons or non-brand Font Awesome icon in the site's pages, menu configuration or release-note labels (`data/release-interfaces.json`), and on an `fa5` name that has no SVG file.
