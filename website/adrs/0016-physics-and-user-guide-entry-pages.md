# ADR-0016: Physics and User guide entry pages

Date: 2026-11-07
Status: accepted

## Prior art

ADR-0002 and ADR-0015 give the interface sections one shape: the top tab opens the first group's page, and every group row opens a page. The User guide had a landing page outside its menu plus a Foundations page covering the same ground. Physics had a long index and five groups, some with no page behind them and one repeating a page as its own first entry.

## Decision

The User guide tab opens Foundations at `/user-guide/`, which merges the two pages. `/user-guide/foundations/` redirects there.

Physics has two groups. Start here opens `/physics/` and holds the lookup pages: conventions, model catalogue and parameter explanations. Physical models has an overview listing every model, with five expandable rows in the order a calculation runs: Diffraction model, Peak profiles, Intensity corrections, Experiment model, Refinement and statistics. Each row opens its own overview page, and every page has an icon. `_check_navigation` enforces the two groups.

An entry page's title matches its menu entry, and `html_title` keeps browser tabs specific (ADR-0015 and the Start here change). The template now lives in `main.html`, so every template shares it.
