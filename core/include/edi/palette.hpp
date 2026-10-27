// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

// The figure palettes (data/palettes, PROVENANCE.md beside them; ADR-0038): the colours of experiments, structures and
// chart roles, the only source of them in edi. The app's charts, legends, icons and Preferences, the pattern
// presentation and the report read these functions.

namespace edi {

/// The five figure palettes, in the order Preferences lists them. Each has eleven figure colours and three role
/// colours, in a light and a dark theme.
enum class ColourScheme {
    Earth,
    Classic,
    Soft,
    Natural,
    ColourBlindSafe,
};

/// The palette of a new user, and of a preference naming none.
inline constexpr ColourScheme kDefaultColourScheme = ColourScheme::Earth;

/// How many colours each palette lists; positions past them take shades of the first two.
inline constexpr std::size_t kPaletteColourCount = 11;

/// The colours of a chart that belong to no experiment or structure.
enum class ChartRole {
    TotalCalculation,
    Background,
    Difference,
};

/// The palettes' preference tokens, in ColourScheme's order: "earth", "classic", "soft", "natural", "colourBlindSafe".
std::span<const std::string_view> colour_scheme_names();

/// The palette a token names; nullopt for any other name, the earlier palettes' included.
std::optional<ColourScheme> colour_scheme_from_name(std::string_view name);

/// The palette a stored preference names: a current token, an earlier palette's token read as its nearest new palette
/// ("ediNatural" and "ediCoast" as Natural, "ediGarden" and "ediStudio" as Classic, "ediContrast" as Colour-blind
/// safe), or the default palette for any other name.
ColourScheme colour_scheme_or_default(std::string_view name);

/// The palette's name as Preferences show it: "Earth", "Classic", "Soft", "Natural", "Colour-blind safe".
std::string_view colour_scheme_title(ColourScheme scheme);

/// Whether the palette keeps its first two colours for experiments (Earth only); the others are one pool.
bool reserves_experiment_colours(ColourScheme scheme);

/// An experiment or a structure, the two kinds of item a palette colours.
enum class FigureKind {
    Experiment,
    Structure,
};

/// An item in a palette's colour order: its kind and the position it already holds, if any.
struct FigureItem {
    FigureKind kind = FigureKind::Experiment;
    std::optional<std::size_t> position;
};

/// Every item's position, from 0, in a palette's colour order. An item keeps the position it holds when its kind may
/// take it there and no earlier item holds it; every other item, in the order given, takes the lowest free position its
/// kind may take. In Earth a structure never takes position 0 or 1; in the other palettes any item takes any position.
/// Pass the items in the order they were added, so each new one takes the next free colour.
std::vector<std::size_t> colour_positions(ColourScheme scheme, std::span<const FigureItem> items);

/// The positions `count` new items of `kind` take beside items already holding `taken`: in order, the lowest free
/// positions their kind may take. A scan's datasets take these beside the project's structures, so no dataset shares a
/// structure's colour.
std::vector<std::size_t> free_positions(ColourScheme scheme, FigureKind kind, std::size_t count,
                                        std::span<const std::size_t> taken);

/// The positions of a project's experiments and structures when none holds one yet: the experiments in their order,
/// then the structures in theirs. The first `experiments` values are the experiments', the rest the structures'.
std::vector<std::size_t> colour_positions(ColourScheme scheme, std::size_t experiments, std::size_t structures);

/// The colour, `#RRGGBB`, at `position` in the palette, in the dark theme's colours with `dark`. Positions 0 to 10 take
/// the palette's colours; a later one takes a shade of its first two: the colour (position - 10) / (count - 10) of the
/// way from the first to the second, mixed in Oklab, where `count` is one past the last position in use (raised to
/// position + 1 when smaller).
std::string figure_colour(ColourScheme scheme, std::size_t position, std::size_t count, bool dark);

/// The colour of a chart role in the palette and theme. The total calculation is the same crimson in every palette.
std::string role_colour(ColourScheme scheme, ChartRole role, bool dark);

/// The colour `t` of the way from `from` to `to` (both `#RRGGBB`), mixed in Oklab as the gradients are; `t` is clamped
/// to [0, 1] and the ends are the colours themselves.
std::string mix_colours(const std::string& from, const std::string& to, double t);

/// The distance between two `#RRGGBB` colours in Oklab, from 0 (the same colour) to about 1 (black and white).
double oklab_distance(const std::string& a, const std::string& b);

/// The WCAG 2 contrast ratio of two `#RRGGBB` colours, from 1 to 21.
double contrast_ratio(const std::string& a, const std::string& b);

/// `colour` as it is drawn on `background` (both `#RRGGBB`) in 2D: with at least `ratio` contrast against it, 2:1 by
/// default (edi ADR-0047). A colour with enough contrast is returned byte for byte. Otherwise its Oklab lightness moves
/// towards black or white, whichever the background contrasts with more, by as little as reaches the ratio, keeping
/// its hue, and its chroma where sRGB can show it at that lightness; where it cannot, the most chroma it can. If even
/// black or white falls short, that end is returned.
std::string readable_colour(const std::string& colour, const std::string& background, double ratio = 2.0);

/// The same for a colour drawn on any of several backgrounds of one theme (a table's alternating rows and its hover
/// tint): it reads on each of them. Lightness moves the same way for all, so the result is the one that moved furthest;
/// a colour that already reads on all is returned byte for byte.
std::string readable_colour(const std::string& colour, const std::vector<std::string>& backgrounds, double ratio = 2.0);

}  // namespace edi
