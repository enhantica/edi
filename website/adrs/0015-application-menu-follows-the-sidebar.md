# ADR-0015: The Application menu follows the app's sidebar

Date: 2026-11-07
Status: accepted

## Prior art

ADR-0002 gave every interface the five workflow stages and ADR-0010 put the app's symbols on pages that match a category. The stages' Application pages were still organised by topic, so a page such as Symmetry and cell covered two sidebar groups, some pages had a symbol and some did not, and a user had to translate between the menu and the app.

## Decision

In the Application section, a stage is one app page and an entry under it is one sidebar group, in the app's order: Main, then Extra, then Settings. Each group page has the group's name and the app's symbol. A category with parts on two tabs, such as Peak profile and its cutoff, is one page.

Each stage also has an overview page, which opens from the stage row and lists the stage's groups. It holds what belongs to no single group: the main-area views, guidance that spans groups, and general topics such as what saving keeps. Work with a scan is a guide across several pages and a worked example, so it sits under Examples.

`application-groups.json` records each group's page, title, tab, symbol, app identifiers and when it appears. The menu's symbols, page titles' symbols and overview tables come from it. Page URLs changed, so `redirects.json` keeps the earlier ones working. Their section anchors are not preserved.

Python and Command Line have no sidebar, so they keep their task pages under the same stages. The User guide is unchanged.

## Known gaps

- The magnetic groups (Magnetic space group, Propagation vectors, Magnetic moments, Magnetic form factors) have no pages. Their categories are not in the published parameter dictionary and no capture shows them, so nothing could be written from evidence yet. They are listed under `undocumented`.
- Calculation range, Extinction, Observed reflections, Data source, Performance and Fitted reflections are short text pages without a screenshot, because the capture runs do not reach those groups. Their text comes from the dictionary's descriptions and the app's source.
- Read-only output tables that the app does not show as groups, such as symmetry operators, have no pages.

## Validation

`_check_application_groups` in `build.py` compares the menu with `application-groups.json`, and that file with the group components in each `*Page.qml` and the categories placed in `category_list_model.cpp`. A new group in the app fails the build until it has a page or is listed as undocumented. The check does not compare the order or the titles with the running app, because the app builds its groups at run time. `gui_topics.py` requires each page in the menu to declare its screenshots; an empty declaration marks a text-only page.
