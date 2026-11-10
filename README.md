<p>
  <picture>
    <!-- light mode logo -->
    <source media='(prefers-color-scheme: light)' srcset='https://raw.githubusercontent.com/easyscience/assets-branding/refs/heads/master/easydiffraction/logos/light.svg'>
    <!-- dark mode logo -->
    <source media='(prefers-color-scheme: dark)' srcset='https://raw.githubusercontent.com/easyscience/assets-branding/refs/heads/master/easydiffraction/logos/dark.svg'>
    <!-- default logo == light mode logo -->
    <img src='https://raw.githubusercontent.com/easyscience/assets-branding/refs/heads/master/easydiffraction/logos/light.svg' alt='EasyDiffraction'>
  </picture>
</p>

**EasyDiffraction** is software for calculating diffraction patterns
from a structural model and fitting its parameters to measured
data, for powder and single-crystal neutron and X-ray diffraction.

**EasyDiffraction** comes with three interfaces that share one
calculation engine and one project format, so a project started in one
opens in the others:

- 🖥️ **Application**, a graphical interface:
  - in your browser, with nothing to install;
  - on your desktop, for macOS (Apple silicon) and Linux (x86-64).
- 🐍 **Python**, the `easydiffraction` package:
  - in your own scripts;
  - in Jupyter notebooks.
- ⌨️ **Command line**, for saved projects without writing code:
  - the standalone `edi` executable, with no Python needed;
  - `python -m edi` from the Python package.

The application also includes an 🤖 **AI assistant** that explains and
carries out analysis steps in the open project.

### Licences

- **Source code**: [BSD 3-Clause License](LICENSE).
- **Application** built from it: [GNU General Public License version 3](COPYING).
- **Third-party components**: their own licences, listed in
  [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES).

## Useful Links

### For Users

- 📖 [Documentation](https://enhantica.github.io/edi/)
- 🌐 [Web app](https://enhantica.github.io/edi/webapp/)
- 🖥️ [Desktop app](https://enhantica.github.io/edi/application/desktop/)
- 🐍 [Python package](https://enhantica.github.io/edi/python/setup/)
- ⌨️ [Command line](https://enhantica.github.io/edi/cli/standalone/)
- 🤖 [AI assistant](https://enhantica.github.io/edi/user-guide/ai-assistant/)
- 🧪 [Tutorials](https://enhantica.github.io/edi/user-guide/tutorials/)
- ⬇️ [Releases](https://github.com/enhantica/edi/releases)
- 💬 [Get in Touch](https://enhantica.github.io/edi/about/community/)
- 🧾 [Citation](https://enhantica.github.io/edi/about/citation/)

### For Contributors

- 🧑‍💻 [Source Code](https://github.com/enhantica/edi)
- 🐞 [Issue Tracker](https://github.com/enhantica/edi/issues)
- 🛠️ [Developer Documentation](https://enhantica.github.io/edi/dev/)
