// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SYMMETRY_HPP
#define EDI_SYMMETRY_HPP

// ADR-0019: what the space group leaves of a structure's cell and coordinates. A parameter is
// INDEPENDENT (a fit can vary it), FOLLOWS another (a cubic `b` follows `a`; the `y` of a site on
// `x,x,x` follows its `x`) or is FIXED to a constant (a cubic angle is 90, a coordinate on a mirror
// plane is 0). The rule is crysta's own — `crysta::cell_freedom` for the cell and
// `crysta::Structure::positional_constraints` for the coordinates, the two calls the symmetric
// completion (io.hpp) already reads — so what a page offers to vary is what a fit accepts.
// Implemented in the adapter (the one crysta-touching TU; edi-only signature, ADR-0003).

#include <array>
#include <functional>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace edi {

enum class TieKind { Independent, Follows, Fixed };

struct ParameterTie {
    const Parameter* parameter = nullptr;
    TieKind kind = TieKind::Independent;
    const Parameter* leader = nullptr;  // Follows: the independent parameter it tracks
    std::optional<double> fixed_value{};  // Fixed: the constant symmetry gives it
};

// One row per cell parameter (a, b, c, alpha, beta, gamma), then one per atom site's fract_x,
// fract_y and fract_z, in the structure's own order, then, for each anisotropic site, one per
// tensor component and one for its adp_iso. A tensor component the site symmetry ties to others
// FOLLOWS the first of them (its value is a sum over them, crysta::adp_ties), and an anisotropic
// site's adp_iso FOLLOWS its tensor's adp_11 (it is the tensor's equivalent value). Occupancy and an
// isotropic ADP are not symmetry quantities and have no row. A setting crysta cannot resolve, or a
// site it cannot place, reports that part independent: the calculation refuses such a structure
// with its own message, and a page that could not edit the offending field could not repair it.
std::vector<ParameterTie> structure_ties(const Structure& structure);

// An edit of one component of a site's moment in a display form (edi ADR-0078): `form` is
// "crystal_axes", "cartesian" or "spherical", component `k` takes `value` and the other two keep
// theirs. The edit is tried on a copy of `project` (which holds `structure` and its `moment`): the
// independent components are written, every relation of the project is applied, and the moment
// that results, read in the copy's own final cell, must be the one asked for; no value from before
// the trial enters that comparison. On success `writes` lists the components to write (0, 1,
// 2 for a, b, c) with their values; otherwise `refusal` says why and nothing is to be written: a
// direction the site symmetry or a declared constraint does not allow, a component they set, a
// negative modulus or a polar angle outside 0 to 180 degrees.
// Every magnetic operation and centring vector of the structure read by crysta's one grammar for
// them (the triplet and its time-reversal sign), so a malformed one refuses where the file is read
// rather than at its first calculation. Throws std::invalid_argument naming `where` and the
// operation. The group's closure and the rest of its checks stay with the calculation.
void check_magnetic_operations(const Structure& structure, const std::string& where);

struct MomentEdit {
    std::vector<std::pair<std::size_t, double>> writes;
    std::string refusal;
};
MomentEdit moment_edit(const Project& project, const Structure& structure,
                       const AtomSiteMoment& moment, const std::string& form, std::size_t k,
                       double value);

// One Wyckoff position of a structure's space group, from crysta's table: its letter, its multiplicity, its
// representative coordinates as the table spells them ("0,0,0", "1/2,y,z") and the coordinates it gives with x, y and
// z at 0, a point on the position.
struct WyckoffOption {
    std::string letter;
    int multiplicity = 0;
    std::string coordinates;
    std::array<double, 3> origin{};
};
// The structure's Wyckoff positions, a to z then the capital letters; none when crysta cannot resolve its space
// group.
std::vector<WyckoffOption> wyckoff_positions(const Structure& structure);

// Whether a site of `structure` takes a Wyckoff letter: false when crysta decides its symmetry
// comes from magnetic operators that form no table setting (edi ADR-0078); then there is no
// letter to show or choose.
bool takes_wyckoff_letter(const Structure& structure);

// Where a site's Wyckoff letter comes from (crysta ADR-0137 B.1.6): the ordinary table (editable),
// crysta's type IV derivation (read-only; `.` until the group verifies), or none (a type I-III
// structure whose operators form no table setting).
enum class LetterSource { Table, Magnetic, None };
LetterSource letter_source(const Structure& structure);

// crysta's one acceptance rule for a magnetic structure, on `structure` as it is (the signed group,
// the exact family, k, the moment ties, the anisotropic refusal, the metric). Throws
// std::invalid_argument naming what refuses; changes nothing.
void check_magnetic_acceptance(const Structure& structure);

// The moments as crysta's load completes them (its acceptance rule): each component the site
// symmetry ties or fixes set from the free ones, and the symmetry form crysta derives; crysta
// reports each value it replaces.
// `restore`: a load, or an edit that changes no symmetry: each type IV site whose letter is stated keeps it and is
// restored from it, and only a site without one is detected (owner decision 2026-11-27, addendum 2).
void complete_atom_site_moments(Structure& structure, bool restore = false);

// The covariance of moment `site`'s crystal-axis components and its structure's cell that every
// displayed form's s.u. comes from: crysta's mapping of the fit's seeds through the project's
// relation graph (crysta's rule for an undefined s.u.; edi ADR-0078). Before a fit, the s.u. the
// file gives, uncorrelated.
std::array<double, 81> moment_input_covariance(const Project& model, std::size_t structure,
                                               const std::string& site);

// Every dependent's s.u. again from its relation and the held fit's seeds and correlations, as a
// load of a project holding a fit restores them (crysta's rule); none without a held fit.
void restore_dependent_uncertainties(Project& project);

// A new atom site for `structure` (the owner, 2026-10-11): an element crysta computes for neutrons and for X-rays,
// preferring one the structure does not hold yet, labelled by its element and the next free number; on the space
// group's general position (its highest-multiplicity letter) at random fractional coordinates rounded to three
// decimals, drawn again while a symmetry operation other than the identity maps them onto themselves. `random`
// returns numbers in [0, 1): the caller's random source, so a test can fix it. A space group crysta cannot resolve
// leaves the site without a letter.
AtomSite new_atom_site(const Structure& structure, const std::function<double()>& random);

// The atom types a site of `structure` may take: the types crysta's scattering table holds for the probe and source of
// each experiment linking it (isotopes with neutrons, ions with X-rays), sorted and without repeats. With no
// experiment linking it, the elements a new atom may take.
std::vector<std::string> atom_types(const Project& project, const Structure& structure);
// Fills the tables' type lists atom_types reads, for the default sources: called once off the GUI thread at start.
void warm_atom_types();

// Sets a site's ADP type and converts its values, through crysta's conversion (ADR-0027):
// to an isotropic type the site keeps its equivalent isotropic value; to an anisotropic one it
// gets a tensor row holding the tensor of its current values, and a row it no longer needs is
// removed. Throws std::invalid_argument for a type that is not Biso, Uiso, Bani, Uani or beta.
void change_adp_type(Structure& structure, AtomSite& site, const std::string& adp_type);
// The structure's propagation vectors replaced by `rows` (id, `kx,ky,kz`), each id given and
// unique, once crysta's rule admits them all (I7: a vector the cell and the signed group can carry,
// no two alike); a refusal throws its reason and leaves the vectors as they were (edi ADR-0078).
void set_propagation_vectors(Structure& structure, std::vector<std::pair<std::string, std::string>> rows);
// The structure's magnetic operators and centring vectors replaced by `operations` and `centerings` (id, triplet with
// its sign) and, when given, its group names, once crysta's rule admits the signed group and the propagation vectors
// with it; a refusal throws its reason and leaves the structure as it was.
void set_magnetic_symmetry(Structure& structure, std::vector<std::pair<std::string, std::string>> operations,
                           std::vector<std::pair<std::string, std::string>> centerings,
                           const std::optional<crysta::MagneticGroupName>& group = std::nullopt);
// The same with a group from crysta's table of the 1651 magnetic space groups, by BNS number, in its BNS setting.
void set_magnetic_space_group(Structure& structure, const std::string& number_bns);
// A magnetic structure read without `_space_group` (edi ADR-0078, site symmetry from the magnetic group): for types
// I-III the family group (the operations with time reversal ignored) is a table setting of the IT number its parent or
// its BNS number names. That setting becomes the structure's space group, so Wyckoff letters, multiplicities and
// coordinate ties come from the table and the cell and positions stay fittable. False, and nothing changed, when no
// setting matches (a type IV group, a setting the table does not hold): the symmetry then comes from the operators.
bool adopt_magnetic_family_setting(Structure& structure, bool reinfer_letters = false);
// Whether the structure's BNS transform, when it parses and the family is a table setting, maps the BNS standard onto
// its operations (edi ADR-0078). A transform that does not parse is descriptive text and claims nothing.
bool bns_transform_consistent(const MagneticDescription& magnetic);
// Crystal or Magnetic (edi ADR-0078). Magnetic: a structure whose symmetry is a magnetic space group.
bool structure_magnetic(const Structure& structure);
// Makes a Crystal structure Magnetic with the grey group of its space group (every moment zero by symmetry until a
// magnetic subgroup is chosen), or a Magnetic one Crystal with its family space group, its moments and other
// magnetic data dropped. A refusal throws its reason and leaves the structure as it was.
void set_structure_magnetic(Structure& structure, bool magnetic);
// A site's element (the owner, 2026-11-19): a moment the new element has no magnetic ion for goes, and a magnetic
// form-factor row for an element no site has any more goes, so no ion of the former element stays offered or saved.
void set_site_type(Structure& structure, AtomSite& site, const std::string& type_symbol);
// A form-factor coefficient the type's approximation does not use, or whose term its ion's table (or its given
// coefficients) does not carry, keeps its value and is fixed: a fit cannot vary it (the owner, 2026-11-19).
void fix_unusable_coefficients(Structure& structure, const std::string& type_symbol);
// A magnetic structure read with a declared `_space_group` and no BNS number: its group is named from that declared
// family setting (not from a parent), so a save, which writes no `_space_group`, keeps the family.
void identify_declared_magnetic_family(Structure& structure);
// The tabulated settings of a Magnetic structure's own space group (time reversal ignored), each as its transform from
// the BNS standard, `a,b,c;0,0,0` first (the owner, 2026-11-19).
std::vector<std::string> magnetic_setting_transforms(const Structure& structure);
// The setting the Setting field shows: the BNS transform a file or an edit gave, else the held table setting's own
// transform; empty for an operators-only structure without one.
std::string held_magnetic_setting(const Structure& structure);
// One of those settings: the BNS table group's operations in it, the transform kept as the transforms loop's BNS row. A
// setting not in the list is refused.
void set_magnetic_setting(Structure& structure, const std::string& transform);

// One tensor row for each anisotropic site and none for any other (diffraction-lib's
// _sync_atom_site_aniso): a missing row holds the tensor of the site's isotropic value, through
// crysta's conversion; a row no anisotropic site names is removed. Each tensor is then completed
// (complete_atom_site_aniso).
void sync_atom_site_aniso(Structure& structure);

// Each anisotropic site's tensor as its site symmetry ties it, through crysta (a fixed component 0, a tied one its
// expression over the free ones), and its adp_iso the tensor's equivalent value. Only values that change are
// written. Every public edit of a tensor or a site, a load and sync_atom_site_aniso end with it, so a read never
// sees followers or an equivalent from an earlier tensor.
void complete_atom_site_aniso(Structure& structure);

// The part of sync_atom_site_aniso that adds a tensor row for each anisotropic site without one,
// leaving every other row and each site's adp_iso as they are. A component that comes out exactly
// 0 carries no uncertainty.
void add_missing_aniso_rows(Structure& structure);

// An anisotropic site's tensor as U* (the CIF U scaled by the reciprocal lengths)
// at the structure's symmetry-completed cell, or nullopt for an isotropic site, a site with no
// tensor row or a cell crysta refuses.
std::optional<std::array<double, 6>> site_u_star(const Structure& structure, const AtomSite& site);

}  // namespace edi

#endif  // EDI_SYMMETRY_HPP
