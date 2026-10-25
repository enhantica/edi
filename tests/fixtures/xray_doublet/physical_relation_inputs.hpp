#pragma once
#include <array>
namespace physical_relation_inputs {
struct Input {
    const char* name;
    const char* target;
    const char* structure;
    const char* experiment;
    const char* analysis;
};
inline const std::array<Input, 5> inputs{{
    {R"input(ratio)input", R"input(instrument.setup_wavelength_2_to_1_ratio)input",
     R"input(data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Li Biso 0.125() 0.125 0.3 0.7 0.125
)input",
     R"input(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2 1.6732
_instrument.setup_polarization_coefficient 0.37
_instrument.setup_monochromator_twotheta 41
_instrument.setup_wavelength_2_to_1_ratio 0.5
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
20 1 1
40 1 1
60 1 1
)input",
     R"input(_edi.schema_version 3
_minimizer.max_iterations 2
loop_
_alias.id
_alias.parameter_unique_name
source phase.atom_site.X.fract_x
target bank.instrument.setup_wavelength_2_to_1_ratio
middle bank.instrument.calib_twotheta_offset

loop_
_constraint.id
_constraint.expression
_constraint.enabled
middle_relation "middle = 0.5 * source + 0.01" true
domain_relation "target = 4 * (2 * (middle - 0.01))" true
)input"},
    {R"input(second-line)input", R"input(instrument.setup_wavelength_2)input",
     R"input(data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Li Biso 0.125() 0.125 0.3 0.7 0.125
)input",
     R"input(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2_to_1_ratio 0.375
_instrument.setup_polarization_coefficient 0.37
_instrument.setup_monochromator_twotheta 41
_instrument.setup_wavelength_2 1.25
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
20 1 1
40 1 1
60 1 1
)input",
     R"input(_edi.schema_version 3
_minimizer.max_iterations 2
loop_
_alias.id
_alias.parameter_unique_name
source phase.atom_site.X.fract_x
target bank.instrument.setup_wavelength_2
middle bank.instrument.calib_twotheta_offset

loop_
_constraint.id
_constraint.expression
_constraint.enabled
middle_relation "middle = 0.5 * source + 0.01" true
domain_relation "target = 2.5 - 10 * (2 * (middle - 0.01))" true
)input"},
    {R"input(polarization)input", R"input(instrument.setup_polarization_coefficient)input",
     R"input(data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Li Biso 0.125() 0.125 0.3 0.7 0.125
)input",
     R"input(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2 1.6732
_instrument.setup_wavelength_2_to_1_ratio 0.375
_instrument.setup_monochromator_twotheta 41
_instrument.setup_polarization_coefficient 0.5
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
20 1 1
40 1 1
60 1 1
)input",
     R"input(_edi.schema_version 3
_minimizer.max_iterations 2
loop_
_alias.id
_alias.parameter_unique_name
source phase.atom_site.X.fract_x
target bank.instrument.setup_polarization_coefficient
middle bank.instrument.calib_twotheta_offset

loop_
_constraint.id
_constraint.expression
_constraint.enabled
middle_relation "middle = 0.5 * source + 0.01" true
domain_relation "target = 4 * (2 * (middle - 0.01))" true
)input"},
    {R"input(monochromator)input", R"input(instrument.setup_monochromator_twotheta)input",
     R"input(data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Li Biso 0.125() 0.125 0.3 0.7 0.125
)input",
     R"input(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2 1.6732
_instrument.setup_wavelength_2_to_1_ratio 0.375
_instrument.setup_polarization_coefficient 0.37
_instrument.setup_monochromator_twotheta 62.5
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
20 1 1
40 1 1
60 1 1
)input",
     R"input(_edi.schema_version 3
_minimizer.max_iterations 2
loop_
_alias.id
_alias.parameter_unique_name
source phase.atom_site.X.fract_x
target bank.instrument.setup_monochromator_twotheta
middle bank.instrument.calib_twotheta_offset

loop_
_constraint.id
_constraint.expression
_constraint.enabled
middle_relation "middle = 0.5 * source + 0.01" true
domain_relation "target = 500 * (2 * (middle - 0.01))" true
)input"},
    {R"input(march-fraction)input", R"input(preferred_orientation.phase.march_random_fract)input",
     R"input(data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Li Biso 0.125() 0.125 0.3 0.7 0.125
)input",
     R"input(data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2 1.6732
_instrument.setup_wavelength_2_to_1_ratio 0.375
_instrument.setup_polarization_coefficient 0.37
_instrument.setup_monochromator_twotheta 41
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1

loop_
_preferred_orientation.structure_id
_preferred_orientation.march_r
_preferred_orientation.march_random_fract
_preferred_orientation.index_h
_preferred_orientation.index_k
_preferred_orientation.index_l
phase 0.73 0.5 1 0 0

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
20 1 1
40 1 1
60 1 1
)input",
     R"input(_edi.schema_version 3
_minimizer.max_iterations 2
loop_
_alias.id
_alias.parameter_unique_name
source phase.atom_site.X.fract_x
target bank.preferred_orientation.phase.march_random_fract
middle bank.instrument.calib_twotheta_offset

loop_
_constraint.id
_constraint.expression
_constraint.enabled
middle_relation "middle = 0.5 * source + 0.01" true
domain_relation "target = 4 * (2 * (middle - 0.01))" true
)input"},
}};
}  // namespace physical_relation_inputs
