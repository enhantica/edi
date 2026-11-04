# JKQtMathText

The formula renderer the desktop app's AI assistant uses for the mathematics in its messages: the `jkqtcommon`
and `jkqtmathtext` libraries of JKQtPlotter 5.0.0 by Jan W. Krieger, at upstream commit
`9e9f0af8b140192e3de7ff866a0013e7da5e1e93` (https://github.com/jkriege2/JKQtPlotter), with the XITS fonts the
renderer draws with.

Only what the two libraries need is kept: `lib/jkqtcommon/`, `lib/jkqtmathtext/` without its examples, tests,
tools and documentation, the XITS fonts (`lib/jkqtmathtext/resources/xits/`), `cmake/jkqtplotter_macros.cmake`,
`VERSION` and `LICENSE`. The files are upstream's, unchanged. `cmake/EdiAssistantMath.cmake` builds the two
libraries as static targets with edi's own compiler and Qt; they are not part of the web build, which carries no
assistant.

Licences: the libraries are LGPL-2.1-or-later (`LICENSE`); the XITS fonts are under the SIL Open Font License 1.1
(`lib/jkqtmathtext/resources/xits/OFL.txt`). Both notices ship with the app.
