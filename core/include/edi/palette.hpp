// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

// The colour schemes (data/palettes, PROVENANCE.md beside them): the experiments' and structures' colours, the only
// source of them in edi. The app's charts and icons, the pattern presentation and the report read these functions.

namespace edi {

/// The two schemes: the default one, and one whose colours stay apart for colour-blind readers.
enum class ColourScheme { Default, ColourBlindSafe };

/// "default" or "colourBlindSafe" (the preference's tokens); nullopt for any other name.
std::optional<ColourScheme> colour_scheme_from_name(std::string_view name);

/// The colour, `#RRGGBB`, of the experiment at `place` among `count`: up to the scheme's number of pattern colours,
/// the place's own; beyond it, the gradient between the last two, sampled at place / (count - 1). `dark` gives the
/// dark theme's colours.
std::string pattern_colour(ColourScheme scheme, std::size_t place, std::size_t count, bool dark);

/// The colour of the structure at `place`, its scheme's short palette taken round again past its end.
std::string structure_colour(ColourScheme scheme, std::size_t place, bool dark);

/// The number of pattern colours a scheme lists, before the gradient takes over.
std::size_t pattern_colour_count(ColourScheme scheme);

}  // namespace edi
