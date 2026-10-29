# 0053. A unified public website with user-focused documentation

- **Status:** Proposed
- **Date:** 2026-10-29
- **Implementation:** 🟡 Partially implemented — isolated Zensical concepts in `website-concepts/`; production publication and documentation migration remain pending.
- **Priority:** High

## Context

The public EasyDiffraction landing page, library documentation and application documentation have
separate navigation and overlapping scientific explanations. The current edi documentation combines
user and developer material in one navigation tree. Its subtle audience-switching link does not
separate navigation or search.

The prior implementations this proposal extends are `mkdocs.yml`,
`docs/assets/javascripts/audience.js`, ADR-0002's two-audience source layout and ADR-0023's combined
documentation/web-app publication. The visual and content references are recorded in
`website-concepts/README.md`.

The owner requested working alternatives built with Zensical, a screenshot-led introduction with a
web-app action, horizontal main navigation, grouped left navigation and a right-hand page outline.
The owner confirmed EasyDiffraction as the public brand and `edi` for code.

## Proposal for discussion

Use one public EasyDiffraction website for the landing page, desktop and browser application,
Python library and command line. Keep scientific concepts, the project model, formats, parameters,
examples and interpretation shared. Split setup, interface operations and API/command reference
where the interfaces differ. Desktop and browser are two ways to use the application.

Two working prototypes explore the remaining navigation choice:

- **Surface-oriented:** Application, Python and CLI are primary sections; Learn holds shared material.
- **Workflow-oriented:** Guides, Tutorials and Reference are primary sections; scientific guides
  show interface-specific instructions within the shared explanation.

Contributor architecture, development builds, internal gates and ADRs stay outside primary user
navigation. The production design should give contributor content its own navigation and search
through a separate build, linked quietly from the user site. A Python API user is still a product
user, not automatically a contributor.

The concepts use Zensical 0.0.73, the existing branding and real repository screenshots. They are
built separately from the production documentation and do not alter its publication workflow.
They illustrate navigation and presentation, not completion of the content migration.

## Production migration requirements

The MkDocs-to-Zensical migration must preserve the behaviour of the existing integrations:

- Generate user feature pages from the existing developer catalogues before rendering, retaining
  the single source and refusing invalid input.
- Keep Jupytext sources and independent notebook execution; export executed notebooks through
  nbconvert into searchable pages, assets and downloadable notebooks.
- Run crysta's Doxygen generation explicitly and require its output before publication.
- Replace checks that inspect MkDocs internals with checks of the declared navigation and final
  artifact. A successful Zensical strict build alone does not prove generated content exists.
- Preserve or redirect existing public links, scope user/contributor search, and assemble the
  browser app with the documentation without changing the existing app URL.
- Check desktop and mobile navigation, keyboard access, headings, contrast, downloads and
  interactive scientific figures in a browser before switching publication.

## Consequences

Visitors get one product entry point and a consistent documentation shell. Shared concepts have
one authored home. Interface-specific instructions remain discoverable without implying that
every feature is available identically on every surface.

The choice between surface- and workflow-oriented primary navigation remains open for owner
review. No prototype choice is an accepted production decision.

## Alternatives considered

| Alternative | Assessment |
| --- | --- |
| Keep the separate historical sites | Retains duplicated concepts and disconnected entry points. |
| Put contributor documentation in the main navigation | Conflicts with the intended user-focused entry and quiet audience switch. |
| Replace only the build command | Loses unsupported hooks and notebook rendering without proving their outputs exist. |
| Surface-oriented sections | Implemented as concept A for comparison. |
| Workflow-oriented sections | Implemented as concept B for comparison. |
