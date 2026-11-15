# No Windows pre-change reference

The original engine `b9f2267451adf1896463c706a87fea20790d28ac` fails to build with
MSVC 14.44 on hosted Windows 2022: `embedded_data.cpp`, error `C2026`, string too big.
[The original-source capture attempt](https://github.com/enhantica/edi/actions/runs/43692035939)
provides the build evidence.

No Windows predecessor output exists and no Windows reference is required. The
rename guarantee uses the authentic Linux and Darwin pre-change references only.
The seven Windows parametrisations record this absence and cite the failed build
in their JUnit properties; they are neither skipped nor supplied a replacement pin.
Linux and Darwin numerical assertions and references remain unchanged.

`windows-predecessor.json` retains the original product/engine identities and
failure evidence. Its reader rejects changed evidence and a fabricated Windows
reference. The former capture recipe is retired; a later engine, a patched old
build or a relabelled Unix capture is not requested.
