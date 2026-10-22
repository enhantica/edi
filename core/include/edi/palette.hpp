// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <string_view>

// The colour schemes (data/palettes, PROVENANCE.md beside them; ADR-0038): the datasets', structures' and chart roles'
// colours, the only source of them in edi. The app's charts and icons, the pattern presentation and the report read
// these functions.

namespace edi {

/// The five Edi palettes, in the order Preferences lists them. Each has light and dark colours: five measured-data
/// colours, five structure colours and three role colours.
enum class ColourScheme {
    EdiNatural,
    EdiCoast,
    EdiGarden,
    EdiStudio,
    EdiContrast,
};

/// The scheme of a new user, and of a preference naming none or one no longer offered.
inline constexpr ColourScheme kDefaultColourScheme = ColourScheme::EdiNatural;

/// How many colours each scheme lists for measured data and for structures; more items than this take a gradient.
inline constexpr std::size_t kGroupColourCount = 5;

/// The colours of a chart that belong to no dataset or structure.
enum class ChartRole {
    TotalCalculation,
    Background,
    Difference,
};

/// The schemes' preference tokens, in ColourScheme's order: "ediNatural", "ediCoast", "ediGarden", "ediStudio",
/// "ediContrast".
std::span<const std::string_view> colour_scheme_names();

/// The scheme a token names; nullopt for any other name, the eighteen schemes before the Edi palettes included.
std::optional<ColourScheme> colour_scheme_from_name(std::string_view name);

/// The scheme a stored preference names, or the default scheme for an unknown or removed name.
ColourScheme colour_scheme_or_default(std::string_view name);

/// The scheme's name as Preferences show it: "Edi Natural", "Edi Coast", "Edi Garden", "Edi Studio", "Edi Contrast".
std::string_view colour_scheme_title(ColourScheme scheme);

/// The colour, `#RRGGBB`, of the dataset at `place` among `count`. Up to five datasets take the first `count` measured
/// colours in order; more take a gradient from the first measured colour to the second, the dataset at `place` at
/// t = place / (count - 1), mixed in Oklab. A place past the end takes the last one's colour. `dark` gives the dark
/// theme's colours.
std::string pattern_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark);

/// The colour of the structure at `place` among `count`, assigned as pattern_colour assigns datasets but from the
/// structure colours.
std::string structure_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark);

/// The colour of a chart role in the scheme and theme.
std::string role_colour(ColourScheme scheme, ChartRole role, bool dark);
/// The colour `t` of the way from `from` to `to` (both `#RRGGBB`), mixed in Oklab as the gradients are; `t` is clamped
/// to [0, 1] and the ends are the colours themselves.
std::string mix_colours(const std::string& from, const std::string& to, double t);

}  // namespace edi
