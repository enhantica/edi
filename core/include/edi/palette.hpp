// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <string_view>

// The colour schemes (data/palettes, PROVENANCE.md beside them): the experiments' and structures' colours, the only
// source of them in edi. The app's charts and icons, the pattern presentation and the report read these functions.

namespace edi {

/// The schemes (PROVENANCE.md): edi's own, published palettes designed for data and app themes' accents. Each has light
/// and dark colours for measured data, a two-colour gradient for more datasets than its set holds, and structure colours.
enum class ColourScheme {
    Coast,
    Garden,
    Peaceful,
    FogForest,
    Sage,
    OkabeIto,
    PaulTolBright,
    PaulTolMuted,
    Tableau,
    Observable,
    Carbon,
    Dark2,
    Petroff,
    Vivid,
    Nord,
    Solarized,
    Catppuccin,
    Apple,
};

/// The scheme of a new user, and of a preference naming none.
inline constexpr ColourScheme kDefaultColourScheme = ColourScheme::Coast;

/// The schemes' preference tokens, in ColourScheme's order: "coast", "garden", "peaceful", "fogForest", "sage",
/// "okabeIto", "paulTolBright", "paulTolMuted", "tableau", "observable", "carbon", "dark2", "petroff", "vivid", "nord",
/// "solarized", "catppuccin", "apple".
std::span<const std::string_view> colour_scheme_names();

/// The scheme a token names; nullopt for any other name.
std::optional<ColourScheme> colour_scheme_from_name(std::string_view name);

/// The colour, `#RRGGBB`, of the experiment at `place` among `count`: up to the scheme's number of pattern colours,
/// the place's own; beyond it, the scheme's gradient sampled at place / (count - 1), mixed in Oklab between the two
/// stops around it. `dark` gives the dark theme's colours.
std::string pattern_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark);

/// The colour of the structure at `place`, its scheme's short palette taken round again past its end.
std::string structure_colour(ColourScheme scheme, std::size_t place, bool dark);

/// The number of pattern colours a scheme lists, before the gradient takes over.
std::size_t pattern_colour_count(ColourScheme scheme);

/// The number of structure colours a scheme lists; structure_colour takes them round again past it.
std::size_t structure_colour_count(ColourScheme scheme);

}  // namespace edi
