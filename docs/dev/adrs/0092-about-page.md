# 0092. About page

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** ✅ Implemented
- **Priority:** Low

## Context

The public site's About page (`website/surfaces/docs/about/index.md`) is the project's personal introduction: who
started EasyDiffraction, why, and how to take part. EasyDiffraction grew out of earlier repositories
(easydiffraction/easyDiffraction, easyscience/EasyDiffractionApp, EasyDiffractionLib, EasyDiffractionBeta,
diffraction-lib and the library documentation) in which other people took part with code, ideas and work. None of that
code is in edi, but the page should name them.

## Decision

**Text.** The page is written by Andrew Sazonov in the first person: where he works, how the project began in 2019,
the design feedback from Design Psychology, the contributors, testers and users, and an invitation to take part (write
directly, the feedback form, the survey). Links to the rest of the site follow under "Where to start" and "More about
the project".

**Signature card.** Below the text: the photo in a 72 px circle, the name, "ESS · DMSC", and the
links "Show e-mail" and "Feedback form". The styles are in `assets/about/about.css`, loaded by the site's `extra_css`.

**Protected e-mail.** The address never appears in the page's HTML. Each `.ed-email` element holds it as base64 of the
reversed address in `data-mail`; `assets/about/email-link.js` adds a link that shows the address as a `mailto:` link
when clicked. Its text is the element's `data-label` (the text says "show e-mail"), or "Show e-mail". Without
JavaScript the element's noscript text shows the address in words.

**Contributors.** To the right of the name, the earlier projects' contributors: Piotr Rozyczko, Simon Ward, Mads
Bertelsen, Eric Lindgren, Erik Fransson, Andrew McCluskey, Celine Durniak and Mridul Seth, in that order. They are
presented as people who took part in the project with code, ideas and work, not ranked by any figure.

- Each is an avatar at the photo's height (72 px), overlapping the previous one by 44 px so the row fits right of the
  name in the desktop content column, with a thin border in the tooltip's border grey. Each links to the person's
  GitHub profile, with the name as its accessible label. The text "and / contributors" stands on two lines after the
  last avatar, as far from it as the name from the photo.
- On hover the avatar comes to the top; the avatars left of it step 12 px left and those right of it 12 px right; all
  others fade under a half-transparent layer of the background colour. Avatars right of the hovered one stack the other
  way, so none is overlapped from both sides. A tooltip below shows the name in the weight and size of the owner's
  name. The tooltip, its border and the fade layer take the theme's colours, so they are light in the light theme and
  dark in the dark theme.
- On a narrow screen the row wraps below the card, its first avatar aligned with the photo's left edge. The text above
  is as far from the photo as the card from the wrapped row.
- `website/contributors.yml` is the one list: name and GitHub login per person. `website/build.py` writes the row in
  place of the page's `<!-- contributors -->` line while it builds, and restores the page afterwards.

**Avatars.** They are stored with the site in `assets/about/contributors/<login>.png`, so the site builds offline and
never loads from GitHub. They are PNG or JPEG files from `https://github.com/<login>.png?size=144` (browsers read
both under the `.png` name), replaced by hand when one changes. A command that refreshes them at deploy is a
follow-up change (the owner, 2026-11-17).

### Measured contributions

Measured on 2026-11-16 over bare clones of the full history, every branch, of the six repositories:
easydiffraction/easyDiffraction, easyscience/EasyDiffractionApp, easyscience/EasyDiffractionLib,
easyscience/EasyDiffractionBeta, easyscience/diffraction-lib and easyscience/to_be_removed__EasyDiffractionLibDocs.

Method: `git log --all --no-merges` in each repository, so work on branches never merged into the default branch counts
too. Authors are grouped by name and e-mail, since each person used several. A commit whose subject starts with
"Revert" counts as a revert, not a commit. Bots (easyscience[bot], github-actions, dependabot) are left out.

| Contributor | GitHub | Commits | Reverts | Repositories (commits) |
|---|---|---:|---:|---|
| Andrew Sazonov | AndrewSazonov | 2737 | 5 | easyDiffraction 892, EasyDiffractionApp 656, diffraction-lib 619, EasyDiffractionLib 350, LibDocs 120, Beta 100 |
| Piotr Rozyczko | rozyczko | 801 | 3 | EasyDiffractionLib 300, EasyDiffractionApp 281, Beta 132, easyDiffraction 83, LibDocs 3, diffraction-lib 2 |
| Simon Ward | wardsimon | 472 | 3 | easyDiffraction 235, EasyDiffractionLib 148, EasyDiffractionApp 89 |
| Mads Bertelsen | mads-bertelsen | 23 | 0 | easyDiffraction 23 |
| Eric Lindgren | elindgren | 20 | 0 | diffraction-lib 20 |
| Erik Fransson | erikfransson | 12 | 0 | LibDocs 12 |
| Andrew McCluskey | arm61 | 2 | 2 | EasyDiffractionApp 1, EasyDiffractionLib 1 |
| Celine Durniak | celinedurniak | 1 | 0 | EasyDiffractionLib 1 |
| Mridul Seth | MridulS | 1 | 0 | diffraction-lib 1 |

Caveats: a commit count is a rough measure only. It says nothing about the size or weight of a change, and ideas,
testing and discussion leave no commits. No figure for lines of code that survive is used, since none of that code is
in edi. GitHub's contributor pages differ: they count only the default branch and only commits linked to an account, so
Mads Bertelsen (all on other branches) and Simon Ward's unlinked commits are missing there.

## Consequences

The page credits the earlier contributors without loading anything from GitHub at view time. Adding a person is one
entry in `contributors.yml` and their avatar file. A changed GitHub avatar reaches the site when its file is replaced.
The row and this ADR are site content only, so they ship with a site rebuild from
`main` and need no app release.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Load avatars from GitHub at view time | Rejected: the page would depend on GitHub and tell it who reads the page. |
| Rank or size contributors by commits | Rejected: commits are a rough measure; the page names people, it does not score them. |
| Count only the default branches, as GitHub does | Rejected: it leaves out work on unmerged branches and unlinked commits. |
