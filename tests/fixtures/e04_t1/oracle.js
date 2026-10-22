// Independent category oracle. Regenerate only with generate.py.
var frozen = {
  "source": "diffraction-lib 0ffba46f declarations +  §2b D-a..D-j + CLI files",
  "profiles": {
    "cwl-gaussian": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w"
    ],
    "cwl-lorentzian": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w"
    ],
    "cwl-pseudo-voigt": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w",
      "mixing_eta_0",
      "mixing_eta_1"
    ],
    "cwl-tch-pseudo-voigt": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w",
      "broad_lorentz_x",
      "broad_lorentz_y"
    ],
    "cwl-tch-pseudo-voigt-fcj": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w",
      "broad_lorentz_x",
      "broad_lorentz_y",
      "asym_fcj_1",
      "asym_fcj_2"
    ],
    "cwl-pseudo-voigt-berar-baldinozzi": [
      "broad_gauss_u",
      "broad_gauss_v",
      "broad_gauss_w",
      "mixing_eta_0",
      "mixing_eta_1",
      "asym_beba_a0",
      "asym_beba_b0",
      "asym_beba_a1",
      "asym_beba_b1",
      "asym_beba_limit"
    ],
    "tof-jorgensen": [
      "rise_alpha_0",
      "rise_alpha_1",
      "decay_beta_0",
      "decay_beta_1",
      "broad_gauss_sigma_0",
      "broad_gauss_sigma_1",
      "broad_gauss_sigma_2",
      "broad_gauss_size",
      "broad_gauss_strain"
    ],
    "tof-jorgensen-von-dreele": [
      "rise_alpha_0",
      "rise_alpha_1",
      "decay_beta_0",
      "decay_beta_1",
      "broad_gauss_sigma_0",
      "broad_gauss_sigma_1",
      "broad_gauss_sigma_2",
      "broad_gauss_size",
      "broad_gauss_strain",
      "broad_lorentz_gamma_0",
      "broad_lorentz_gamma_1",
      "broad_lorentz_gamma_2",
      "broad_lorentz_size",
      "broad_lorentz_strain"
    ],
    "tof-pseudo-voigt": [
      "broad_gauss_sigma_0",
      "broad_gauss_sigma_1",
      "broad_gauss_sigma_2",
      "broad_gauss_size",
      "broad_gauss_strain",
      "broad_lorentz_gamma_0",
      "broad_lorentz_gamma_1",
      "broad_lorentz_gamma_2",
      "broad_lorentz_size",
      "broad_lorentz_strain"
    ]
  },
  "instrument": {
    "cwl": [
      "setup_wavelength",
      "calib_twotheta_offset",
      "calib_sample_displacement",
      "calib_sample_transparency"
    ],
    "tof": [
      "setup_twotheta_bank",
      "calib_d_to_tof_offset",
      "calib_d_to_tof_linear",
      "calib_d_to_tof_quadratic",
      "calib_d_to_tof_reciprocal"
    ]
  },
  "examples": [
    {
      "id": "pd-neut-cwl_lbco-hrpt_start-2",
      "structure": "lbco",
      "experiment": "hrpt",
      "rows": 42,
      "free": 17,
      "atoms": 4,
      "background": 5,
      "excluded": 2,
      "texture": 1,
      "spaceGroup": "P m -3 m",
      "code": "1",
      "system": "cubic",
      "range": [
        10.0,
        164.85,
        0.05,
        3098
      ],
      "structureScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.length_a": {
          "value": 3.88,
          "free": true,
          "uncertainty": null
        },
        "_cell.length_b": {
          "value": 3.88,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.length_c": {
          "value": 3.88,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_alpha": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_beta": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_gamma": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_space_group.name_h_m": "P m -3 m",
        "_space_group.coord_system_code": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_geom.min_bond_distance_cutoff": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_geom.bond_distance_inc": {
          "value": 0.25,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structureLoops": {
        "atom_site": [
          {
            "id": "La",
            "type_symbol": "La",
            "fract_x": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "a",
            "multiplicity": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "Ba",
            "type_symbol": "Ba",
            "fract_x": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "a",
            "multiplicity": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "Co",
            "type_symbol": "Co",
            "fract_x": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "b",
            "multiplicity": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "O",
            "type_symbol": "O",
            "fract_x": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.5,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "c",
            "multiplicity": {
              "value": 3.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          }
        ]
      },
      "projectScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "lbco_hrpt_s2",
        "_metadata.title": " graded start s2 of refine-lbco-hrpt",
        "_metadata.description": "?"
      }
    },
    {
      "id": "pd-neut-tof_si-sepd_start-2",
      "structure": "si",
      "experiment": "sepd",
      "rows": 45,
      "free": 23,
      "atoms": 1,
      "background": 14,
      "excluded": 0,
      "spaceGroup": "F d -3 m",
      "code": "2",
      "system": "cubic",
      "range": [
        2000.0,
        29995.0,
        5.0,
        5600
      ],
      "structureScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.length_a": {
          "value": 5.431,
          "free": true,
          "uncertainty": 0.001
        },
        "_cell.length_b": {
          "value": 5.431,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.length_c": {
          "value": 5.431,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_alpha": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_beta": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_gamma": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_space_group.name_h_m": "F d -3 m",
        "_space_group.coord_system_code": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_geom.min_bond_distance_cutoff": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_geom.bond_distance_inc": {
          "value": 0.25,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structureLoops": {
        "atom_site": [
          {
            "id": "Si",
            "type_symbol": "Si",
            "fract_x": {
              "value": 0.125,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.125,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.125,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "a",
            "multiplicity": {
              "value": 8.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": 0.1
            },
            "adp_type": "Biso"
          }
        ]
      },
      "projectScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "si_sepd_s2",
        "_metadata.title": " graded start s2 of refine-si-sepd",
        "_metadata.description": "?"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_start-1",
      "structure": "cosio",
      "experiment": "d20",
      "rows": 58,
      "free": 43,
      "atoms": 6,
      "background": 14,
      "excluded": 0,
      "texture": 0,
      "spaceGroup": "P n m a",
      "code": "abc",
      "system": "orthorhombic",
      "range": [
        8.0953,
        150.0953,
        0.10021171489061398,
        1418
      ],
      "structureScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.length_a": {
          "value": 10.3,
          "free": true,
          "uncertainty": null
        },
        "_cell.length_b": {
          "value": 6.0,
          "free": true,
          "uncertainty": null
        },
        "_cell.length_c": {
          "value": 4.8,
          "free": true,
          "uncertainty": null
        },
        "_cell.angle_alpha": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_beta": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_cell.angle_gamma": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_space_group.name_h_m": "P n m a",
        "_space_group.coord_system_code": "abc",
        "_geom.min_bond_distance_cutoff": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_geom.bond_distance_inc": {
          "value": 0.25,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structureLoops": {
        "atom_site": [
          {
            "id": "Co1",
            "type_symbol": "Co",
            "fract_x": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_y": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "wyckoff_letter": "a",
            "multiplicity": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "Co2",
            "type_symbol": "Co",
            "fract_x": {
              "value": 0.279,
              "free": true,
              "uncertainty": null
            },
            "fract_y": {
              "value": 0.25,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.985,
              "free": true,
              "uncertainty": null
            },
            "wyckoff_letter": "c",
            "multiplicity": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "Si",
            "type_symbol": "Si",
            "fract_x": {
              "value": 0.094,
              "free": true,
              "uncertainty": null
            },
            "fract_y": {
              "value": 0.25,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.429,
              "free": true,
              "uncertainty": null
            },
            "wyckoff_letter": "c",
            "multiplicity": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "O1",
            "type_symbol": "O",
            "fract_x": {
              "value": 0.091,
              "free": true,
              "uncertainty": null
            },
            "fract_y": {
              "value": 0.25,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.771,
              "free": true,
              "uncertainty": null
            },
            "wyckoff_letter": "c",
            "multiplicity": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": true,
              "uncertainty": null
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "O2",
            "type_symbol": "O",
            "fract_x": {
              "value": 0.448,
              "free": true,
              "uncertainty": null
            },
            "fract_y": {
              "value": 0.25,
              "free": false,
              "uncertainty": 0.0
            },
            "fract_z": {
              "value": 0.217,
              "free": true,
              "uncertainty": null
            },
            "wyckoff_letter": "c",
            "multiplicity": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": true,
              "uncertainty": null
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          },
          {
            "id": "O3",
            "type_symbol": "O",
            "fract_x": {
              "value": 0.164,
              "free": true,
              "uncertainty": null
            },
            "fract_y": {
              "value": 0.032,
              "free": true,
              "uncertainty": null
            },
            "fract_z": {
              "value": 0.28,
              "free": true,
              "uncertainty": null
            },
            "wyckoff_letter": "d",
            "multiplicity": {
              "value": 8.0,
              "free": false,
              "uncertainty": 0.0
            },
            "occupancy": {
              "value": 1.0,
              "free": true,
              "uncertainty": null
            },
            "adp_iso": {
              "value": 0.5,
              "free": true,
              "uncertainty": null
            },
            "adp_type": "Biso"
          }
        ]
      },
      "projectScalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_s1",
        "_metadata.title": " graded start s1 of refine-cosio-d20",
        "_metadata.description": "?"
      }
    }
  ],
  "projects": [
    {
      "id": "pd-neut-cwl_cosio-d20_start-1",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_s1",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Olivine structure and profile refinement · Starting model 1",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.3,
          "spaceGroup": "P n m a",
          "cell": [
            10.3,
            6.0,
            4.8,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "aa78efd1d198d70bcf767443289b59d2f8b062c7f739ab8906e6cf4d7b39e9e5",
        "structures/cosio.edi": "7ec9ca0fb52e1c29aa6a5aa68ca0e6a58db75ccc369a613f32d2036221994b48",
        "experiments/d20.edi": "c0ef1ce128acbcc94eda9294f6afd63fd80c059eb7f7e5f1c5981f3efb07fbca",
        "analysis/analysis.edi": "06acc049b2fdfd16e06af5c03634f364d62a2819d2bb2b0ea456cd4b79ba5061"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_start-4",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_s4",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Olivine structure and profile refinement · Starting model 4",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.3,
          "spaceGroup": "P n m a",
          "cell": [
            10.3,
            6.0,
            4.8,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "323236eceba657b425f9c512f5313e0a1bf944cd90b410d492d72d45ab2a8a22",
        "structures/cosio.edi": "7ec9ca0fb52e1c29aa6a5aa68ca0e6a58db75ccc369a613f32d2036221994b48",
        "experiments/d20.edi": "6b86e5db73f55ae128b14d5ab237595530483f4543886f7e8d4012d30e05e1be",
        "analysis/analysis.edi": "06acc049b2fdfd16e06af5c03634f364d62a2819d2bb2b0ea456cd4b79ba5061"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_scan-3f",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_scan",
        "_metadata.created": "09 Sep 2026 07:33:40",
        "_metadata.last_modified": "09 Sep 2026 07:34:27",
        "_metadata.timestamp": "2026-09-09T07:34:35+00:00",
        "_rendering_plot.type": "auto",
        "_report.cif": "false",
        "_report.html": "true",
        "_report.tex": "false",
        "_report.pdf": "false",
        "_report.html_offline": "false",
        "_rendering_table.type": "auto",
        "_rendering_structure.type": "auto",
        "_structure_view.show_labels": "false",
        "_structure_view.show_moments": "true",
        "_structure_view.range_a_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_a_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_view": "adp",
        "_structure_style.color_scheme": "jmol",
        "_structure_style.adp_probability": {
          "value": 0.99,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_scale": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_verbosity.fit": "short",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Temperature scan · 3 patterns at 52.3, 299.4 and 497.4 K",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_minimizer.type": "crysta (lm)",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.descent": "fast_descent",
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        },
        "_sequential_fit.data_dir": "experiments/d20_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "false"
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.31,
          "spaceGroup": "P n m a",
          "cell": [
            10.31,
            6.0,
            4.79,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [
        {
          "file": "all594687.dat",
          "sha256": "13d209575f8ddfeaa32183cbfe6ee457cdbff505763cdca09be1d7c801e8415d",
          "range": [
            0.0953,
            150.8953,
            0.10013280212483398,
            1507
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4066.526,
                27.949
              ]
            },
            {
              "index": 753,
              "values": [
                75.4953,
                405.145,
                8.572
              ]
            },
            {
              "index": 1506,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "all594791.dat",
          "sha256": "0ec0607b473b3f618d3f56d494eca9184e8f38751ffaabdb77172a45f3b3999f",
          "range": [
            0.0953,
            150.8953,
            0.10013280212483398,
            1507
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4081.598,
                27.952
              ]
            },
            {
              "index": 753,
              "values": [
                75.4953,
                429.041,
                8.806
              ]
            },
            {
              "index": 1506,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "all594842.dat",
          "sha256": "95656a5ee8468c3a012010831a05889c093d08d7779b1ac77d4918cb0e823590",
          "range": [
            0.0953,
            150.8953,
            0.10013280212483398,
            1507
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4024.358,
                31.828
              ]
            },
            {
              "index": 753,
              "values": [
                75.4953,
                442.251,
                10.252
              ]
            },
            {
              "index": 1506,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        }
      ],
      "loaderWarning": "Warning: unsupported _minimizer.type \"crysta (lm)\" - using crysta",
      "files": {
        "project.edi": "2df73c15c9ade1937ba7ab0729c7c4cf73331cf6b735ef80a40ab1a947221e31",
        "structures/cosio.edi": "1b3afde2d3a8184d6cb9789fa3fc8fa5dd026756a51e44a2cca6b80b9df8103a",
        "experiments/d20.edi": "89c14df4a88f6eeedc8d42647ad4bda32c52856d2fe58e6a64f041062e5d86c7",
        "analysis/analysis.edi": "fde9a40134aaf6794cde3e396a01067e1018d78871c394d4646c95052416f726"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_scan-162f",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_scan_162f",
        "_metadata.created": "09 Sep 2026 07:33:40",
        "_metadata.last_modified": "23 Sep 2026 14:06:27",
        "_metadata.timestamp": "2026-09-09T07:34:35+00:00",
        "_rendering_plot.type": "auto",
        "_report.cif": "false",
        "_report.html": "true",
        "_report.tex": "false",
        "_report.pdf": "false",
        "_report.html_offline": "false",
        "_rendering_table.type": "auto",
        "_rendering_structure.type": "auto",
        "_structure_view.show_labels": "false",
        "_structure_view.show_moments": "true",
        "_structure_view.range_a_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_a_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_view": "adp",
        "_structure_style.color_scheme": "jmol",
        "_structure_style.adp_probability": {
          "value": 0.99,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_scale": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_verbosity.fit": "short",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Cooling scan · 162 patterns from 497.4 to 50.4 K",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_sequential_fit.data_dir": "experiments/d20_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "false"
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.335842071204308,
          "spaceGroup": "P n m a",
          "cell": [
            10.335842071204308,
            6.029694577103228,
            4.797569862624058,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [
        {
          "file": "01_001_497p3790.dat",
          "sha256": "22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4024.358,
                31.828
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                442.251,
                10.252
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "01_002_497p3410.dat",
          "sha256": "ef3eaf0029ac15202d49952f66caf1d30a8d4ca3adf82e76f3a89ef4a843728d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_003_497p2280.dat",
          "sha256": "12df6cee20e6241e84a392053ef1ad6cb9cc153d96ddbd95b025ba79f4c22734",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_004_497p0360.dat",
          "sha256": "943ff86fb9bf5d264f4a2d41e64b1d5711f26ab76de4cb90c0545900e92c674e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_005_496p5900.dat",
          "sha256": "5f3023b3820eb243fe8186c8f9ff953e1325c0d767097174f77e94419f1d8094",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_006_495p3740.dat",
          "sha256": "f2025c68fdd8fc3de28b057382d9087ea6c0b92dbec0c1b9eca54dc0ef41f2d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_007_489p9560.dat",
          "sha256": "2898a2b6434c15f02eff1c1994fa8c896c6d92b93d15a15994854e75be060aef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_008_485p7350.dat",
          "sha256": "de3f00765f6765b80157d75947c7517e997dfea579adcc76251fe644a9a7ba70",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_009_481p2260.dat",
          "sha256": "021d76aad5f57879aefa516eefc96418536d0f42af793e6a0d47d6f407e05005",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_010_476p9800.dat",
          "sha256": "1dc012ecb202cb10c04d5a70be15c2a9734c2b37d547f564ecee9d2c9abedefa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_011_472p5840.dat",
          "sha256": "acd16e373fdfe9e3cc5c597be55ec304109578badf82df8743d69f07a58ca9c0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_012_468p2800.dat",
          "sha256": "f78b5d3d9da83a3f003535847f2610e52e7dfd8374ee5950a0c3c34109f56462",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_013_463p8850.dat",
          "sha256": "d5c22e9a92bfaf425cd6ab3633325319d7a62db6e65d3916e97447c6422fd30c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_014_459p2510.dat",
          "sha256": "dd07ea491ebb2a9fd37a9b0a6204e82367ea4a1954315778ceb2fe585d93bbd4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_015_454p8870.dat",
          "sha256": "48231f25702a2c8e550c09f6272b5305549297e7647b59b7a3d8d6b28810b1a4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_016_450p3320.dat",
          "sha256": "6e363f78be7d54a57830bca46b5bd0a18f768f6b15dd8a68ed6c1d292216fb03",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_017_446p0030.dat",
          "sha256": "89c898df19634d5672e76798c37bc9e8551bb5678767e988bc41d735173483e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_018_441p4020.dat",
          "sha256": "aca3572c999b8cf60592ea7b884f67ecc8a90664361f4e6aa15590b6ef8ea6e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_019_437p1320.dat",
          "sha256": "f6418e949ff522365390f777c197ab7fbd9d76cded8c04d7d4a509a51e8b877b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_020_433p0150.dat",
          "sha256": "a3d5a690e7a7b31263035b240181507e751f6b7f0ba35b77c29cd82d6bb535fd",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_021_428p4870.dat",
          "sha256": "b80cc00f57695d56589aa857d1c72fd921acc2ec2c45adecc4d2901e49e3bff4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_022_424p1020.dat",
          "sha256": "458d5d83a455d35efe65f3a9a518cf0b66d677b280be587868a6cb9e7af2db38",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_023_419p4530.dat",
          "sha256": "33611d2a5959694b1dbe9d228db99613afe5431bc35a43e61764267a73be83d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_024_415p1880.dat",
          "sha256": "7a9fdd55cf98f32e0ec00e042999c4555b5c818c9429d6daf41fc7a166bac478",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_025_410p7830.dat",
          "sha256": "d0e151a4805a8c29be88b33249f11e1f5414e9de25dffde20869b202cdeb72ec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_026_406p1830.dat",
          "sha256": "7fa18447b1981382d68d30c896b87af509f6bba264bc1013af1650cb5b34383e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_027_402p1390.dat",
          "sha256": "a68b8fae71666b66d6139375978379ab63ce7facb1f4c63a343262c47e81270b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_028_397p5640.dat",
          "sha256": "450d09ba353d52cf88805f153913f308ec51428aa279649911a5297dd4106f25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_029_393p2660.dat",
          "sha256": "6ebb10a745535d973fbaa3aa16bcf57f163ad99d67cedb123f6739cc0d19989a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_030_388p8760.dat",
          "sha256": "2fe4da899cfec93b4685f5ddf48cb98f639901dc2239bced310739522ed301ba",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_031_384p6000.dat",
          "sha256": "c051142ae04c23efe2323ca6ffbbdf39ee6571371d26dcc00c1cf592ff97ee55",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_032_380p2820.dat",
          "sha256": "e03e997f68637b4df7b60513c7845a260b01726f3f67fa804b355a71b94de8f5",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_033_375p8110.dat",
          "sha256": "a56ff8f5849e1e3fe67b6858352fcc88c24a53cfe579df98e97d48c2e2d9f055",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_034_371p4350.dat",
          "sha256": "76e2fd2646d8c37d1d357e4479b20e29a47c41ee357614f7d947a8c1fcbb7ce3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_035_362p8190.dat",
          "sha256": "424bea57f499991eb8aa7d224373a6bd73d0107c0977c06f0db15ed1eaab8ccc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_036_358p4140.dat",
          "sha256": "1006fc6e31bbd16528ac73eccd0e115148bcdfb75b397df5a11a5849d96131bc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_037_354p1160.dat",
          "sha256": "0e6a05e598dadc199dd04823bed2db908f96e104cbb5359fc824893a657adc1f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_038_349p8060.dat",
          "sha256": "206f085b19fa066d2b473479221c460287a40f19f5e7c1f0320c2979c8ffe32a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_039_345p2570.dat",
          "sha256": "5f1b51a111b63db9d3154dd6fa9e2dfc1c18cdaccfcd38a0f6cc97dae5e79615",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_040_340p7230.dat",
          "sha256": "7855c5f97795bcb99310acd974b65fc6aad8a5d157f41aec9bdf2802533414ac",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_041_336p6280.dat",
          "sha256": "10d3cb20af02ac533a17e0966dd41f3fb80f80bfdc5e2763d4e92b08485640f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_042_332p2660.dat",
          "sha256": "03fe53d66954d3935bbbca3c39dda6ec625c1f5627c6eb6d89e94d0364ade80e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_043_327p9190.dat",
          "sha256": "f8dbe59316ee34514cf8ddd5502b5b53609276ce3117e05d87ac7ac9afd97aec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_044_323p3350.dat",
          "sha256": "c038f2e38226ad3fd2281b55fbb39cf04a6ef2dc3d4f0276b5c8bf0ba393024f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_045_319p0710.dat",
          "sha256": "5c2058a222ef253a0f46235b9615cf957e6414b4e52f4138dfb64be5fd173af4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_046_314p8200.dat",
          "sha256": "08d4bf74090bd142686ba02fe36c6642f4117480d0f9026b3e3a307ca64b6ed8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_047_310p9350.dat",
          "sha256": "fec1490aaf6f59a7464c3b21cdedf6333cb3d764f8d9a13ac62478cb2d981afa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_048_306p6800.dat",
          "sha256": "29e6848c38f889e1bc839bac949c3b2404abe2f9a652a604fc4542fe55d52dc3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_049_303p0940.dat",
          "sha256": "70240b3346e701baaa43629897aeb121f54cd19aff707eabe45d2524844ca664",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_050_300p4240.dat",
          "sha256": "92e8342610fa5d0f5a749a9b4dc29479c3ac75b052db2c9a2393155bf354b28c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_051_299p3940.dat",
          "sha256": "dd2bf75b4d8e3ae22bf9643d3be77773d3b5317b6ab8a273b802bb3640059874",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_052_299p2050.dat",
          "sha256": "4565452f1baca8f389bcf7d8e47faef032fc945105c95923f74ddd4b6709c410",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_053_298p8330.dat",
          "sha256": "841b483ddd09b3c2e767db9bb9890c5ac2d1d3a937b51da72f3bc18871e3e79b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_054_298p0250.dat",
          "sha256": "eb716b2eecde0c12d3329a5651ab8d3945e07d0929a802c164b15868861dd689",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_055_296p4040.dat",
          "sha256": "acf75bbc5a6a1e60f2fec3d8e7d6101374ee8528af85817d84a816c2681eca6a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_056_290p7210.dat",
          "sha256": "940bcd89b8fe5ac1ac574ac558dcc921e82ea8b40238c76209b0bc786ad22eee",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_057_286p2140.dat",
          "sha256": "90525f159ad2e7b5dba17ba5e5a817b03e81b9bb850373e34de26fc30e00bd8d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_058_281p9010.dat",
          "sha256": "243f7d2144ece905f6de4f72acbff36fad21f42706937370f63b21afdd3ba325",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_059_277p4860.dat",
          "sha256": "7283650bc9654d294ddb40e2e97f293f9be346e04dc3b01ab80def0c379ddba1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_060_273p0910.dat",
          "sha256": "6e6045caf495e42b716d4a14b0544ae4465e7f61b9db4200b8740f2137c33043",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_061_268p6170.dat",
          "sha256": "56ae5f39aff745c323b4143c019c828b649dd24cb38b6dd995710f747cdea63b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_062_264p2270.dat",
          "sha256": "cac5e46d43612d7f3e44829e0b83606258443922c94ab58cf5f5da9767e1eef3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_063_259p8830.dat",
          "sha256": "7d831ef5c563487fead89e89d0b2f663265a34c8d8d1ca8615f7147fa88926d9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_064_255p4710.dat",
          "sha256": "9b7bee4d7bce1b21a6c949784dcc77cbe1c4f68dac20b6e1f5403d7e416892ff",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_065_250p8860.dat",
          "sha256": "5f1d25db589640730d6dfb7c267af35b6c0d108e30e927467c780335b65b711c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_066_246p4910.dat",
          "sha256": "1475795b475c580b6bebef7a47b544c125adb53e056c5e0234cc04943212fdda",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_067_242p0240.dat",
          "sha256": "a809c348dc88901c28d6a2bba6675fdcd92759739b52287aef810827d9350872",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_068_237p6280.dat",
          "sha256": "17bc9c32998fc52f5a707528e0bb34a5f5a3c758460c06a680106d7f8b15d509",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_069_233p1580.dat",
          "sha256": "353eb5a64530acc7d801ff266b4c26a28edf1f0d106cb53f31b1dabb0784cac1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_070_228p8500.dat",
          "sha256": "fa65084b98954849ab8c758c025c9d54844eccf44191b4a17f0af0048cc2aafb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_071_224p4280.dat",
          "sha256": "1d3a611527ac7c9e20d2630f570ba3d2501d06c203f30b135d59d71dc6c24607",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_072_220p0320.dat",
          "sha256": "b96c8d59b7f83d69264b2f0b9d788f510424ba4b05ab05877b3f378ea28971ea",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_073_215p5290.dat",
          "sha256": "2bb93ecf6d608b203a456fc6105f09a4da91fabdb918040bdca1f376e4eb20e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_074_211p2050.dat",
          "sha256": "de09bfbe03355eb1707e5a3f9782e5e8264b6306003ea3c43340853cd98378e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_075_206p8010.dat",
          "sha256": "b25f8a037ebda34163d413ad3f86663a10c2de1e16479dbcd0213318421cdb6b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_076_202p4320.dat",
          "sha256": "850dc3873eb6e1351365d111421a6dd56965d3f13096f8a99761fdaf45939b6f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_077_198p0270.dat",
          "sha256": "821331225f83ffebfd52964851dc3d87b99f2767afc0229014d755b2ad93961a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_078_193p7040.dat",
          "sha256": "0f3bd513597e7753ac9be045536f431e00616e13b7d4d7a69d94bf9bb5660ed6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_079_189p3940.dat",
          "sha256": "9fd207d48eb77ecf979aaaa1cfcb1efe09edfa7259a5b26150a9669a70b5ec86",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_080_184p9760.dat",
          "sha256": "be54656813c1d4be8e78e622770e4bbc63e2f78e8600097dbae0337a2ace7f15",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_081_180p6510.dat",
          "sha256": "a35ba186cfd2383fc5610becdcd625108a38e3606c48aab96cff1f1a6d49d0cb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_082_176p5080.dat",
          "sha256": "99e844a0e5fcf2cabb3afcb4e54e7b6685d3678191371241417600b878b78e9d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4113.21,
                28.022
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                433.118,
                8.835
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "01_083_172p2020.dat",
          "sha256": "adab65cb6294027bb3ae955a72eb27eec38f463125f8747d5ca95c22f6f7d7b2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_084_167p8070.dat",
          "sha256": "cccb96e06d3430b50321be31f750bce1d93c9577e8baf8fe6b5571e838e9d483",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_085_163p5550.dat",
          "sha256": "b49dda0e6f80077784a6e3075d6f3e5c277b2ea61c381fb54eeca92abcf088c3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_086_159p2290.dat",
          "sha256": "e0412cd8d7fc27c4a70276f921cf3bd2fc42216399bc37347529045cbabd3bf2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_087_154p8790.dat",
          "sha256": "786ec6d894d6c72e98bcd75a6f6d33f79e67380ecd6f1306518cd702ced85776",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_088_150p5940.dat",
          "sha256": "9bef7dde185a0e05295b7b2cfc571759148a38b5a9e7d20c2ebb7155ce77b9f6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_089_146p2570.dat",
          "sha256": "187774183b67a14b26fd9ca37fd2c83e1499c685aeacca49d269875e4f27fe21",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_090_142p0530.dat",
          "sha256": "2f52bfef144edebe852b12e23351f05f97e50a573181c1f2c14383444bd16987",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_091_137p9060.dat",
          "sha256": "9cbb27d5e6862e44010e27b37e2e6bc092eff833555d83a6bb40c2ff4ddc7b2c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_092_133p7450.dat",
          "sha256": "ed8e8a37b1b57b1ec606e2c5ee57d40d946d34249e879ab44fd5505c79f1da45",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_093_129p5840.dat",
          "sha256": "48b543ba633903102e0be89434ef4269cfec2faabddcc4209471a1228d63491e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_094_125p4340.dat",
          "sha256": "a5fc59c5920f766e8057cde53301488b64fb737f2fe69ea2db029d8a1d6c6124",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_095_121p3580.dat",
          "sha256": "31e9e79b02c15a215dfb9d25f79e69a9989b8f69413608a04954c3392733de27",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_096_117p1490.dat",
          "sha256": "1e9cd3e8c1ec347cb153e9cef1754912b90d64919206cba528ec107579b7f71b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_097_113p0630.dat",
          "sha256": "04e9db3d4b807c246171fa9efc761987edd89b8e4c0bbbc4db58149e2e21d61f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_098_109p2600.dat",
          "sha256": "fe318a1be180fe8bb36553072a06fcb914716f775e4178c57196c3f54bbe7440",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_099_105p6360.dat",
          "sha256": "a1db92e7f37ab2530b18f9c979e7626e81d320fdc62e0a99ad6b55257912ea08",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_100_103p0030.dat",
          "sha256": "2c963c020313193b28e64a42e7d217b52e3548dbd22e17a6bb1ce212b19ecc99",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_101_101p9130.dat",
          "sha256": "b60e169864b4fcc0a34c5cd18bdcda39eb73565319b70d1dcea644602e266bcf",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_102_101p8800.dat",
          "sha256": "fce7aae98c761517eab36c3435fad63f1b54b42cfeed5d9aa3dd6cc52507cade",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_103_101p8220.dat",
          "sha256": "380ec121a9e49a470b3cb567c66739ccba346c9959ea8ac3e7f5d5866d7aec8c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_104_101p6830.dat",
          "sha256": "660fd2627db86042128122ba1979627462e9787bed8746fb3683891a726bf9b4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_105_101p3630.dat",
          "sha256": "122de03f7e29f0ba58bfa1e62a16d21f1d70ac179f7150af95825078a1b377d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_106_100p5400.dat",
          "sha256": "2cdd6346481323006d05564bdd8c58cc7522e6440ef5333d785abf2def2f9efa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_107_099p5650.dat",
          "sha256": "28eaf543a7cc252ac4e9f82c0c449071c9892e3306483c929232a28efe10f4f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_108_098p5500.dat",
          "sha256": "6a23ea8bcc2c3014e7d5fb60d525105a6c1ba1d4908f6042535ee90192b77219",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_109_097p5340.dat",
          "sha256": "f1fb0335a3df055a0dd1d468f23c430aef3d41c33555c684d8e4ced5ed4ba78e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_110_096p4920.dat",
          "sha256": "bb9babfd6b49b4cb019f007ac4f9683a14c8dc9f89fc9eddd092677094bf41de",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_111_095p5170.dat",
          "sha256": "23e84372a799fba239ccc6e3c7beac018b9c17c73c3ebf43ccf1d332cddb677b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_112_094p4880.dat",
          "sha256": "fbb59687dfec327ef1368e073bdf04a3b61fc071a78f89803751235ea32ab9fb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_113_093p4840.dat",
          "sha256": "91e30e877319e41a9a13e9ea2171d71f9de992c31e9ec6bd063f92e7c9c3e228",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_114_092p4800.dat",
          "sha256": "341c1a1e0b27ed7b8182971ab13b4cf68657d5b9f40e78e9f68efea059fb3e67",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_115_091p4890.dat",
          "sha256": "d4b270af7d468e0cb960a7b8a1e821a7e5565e65c7f9cdd2596ac325e63ae415",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_116_090p4890.dat",
          "sha256": "fdff650c5d456acb17b8d145c38c0bc0929eccd291570e39d734711bfd2ccb35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_117_089p4800.dat",
          "sha256": "a9a99d3e263c724b28b8b945b30e7846101952a87cad1458138e43a8adca77fe",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_118_088p4620.dat",
          "sha256": "a5971a3ea8bd0c09c26df43e41f00ba736066fc4d8d052b74b7196f0658780ef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_119_087p4450.dat",
          "sha256": "6fe2f51b48a833d73b7be41dab21f6cda08a054dcb817a9601671c323f8d988e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_120_086p4230.dat",
          "sha256": "c69586ac805e3af61a33d90b87e635e7f895b724c78f32f02211b28203fe4a13",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_121_085p3880.dat",
          "sha256": "356f9e9f7f7d96f760a789bb577e15d5e42ede954fffaefb21fbc6cc8c8e1424",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_122_084p3500.dat",
          "sha256": "5546c302c3af0bd2bb86386677de6e13c30a8808fca1271631cb228a7f4d650f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_123_083p2780.dat",
          "sha256": "ab54111a4bad28e9b194ea9c79b824204b9fe57cd2e3592c9037d2217118e957",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_124_082p1890.dat",
          "sha256": "b5426601315463137a772b5a2f38cc75bfca98a567d576b24ca4cc53c2721933",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_125_081p1590.dat",
          "sha256": "0d8bfe903fe180e35e3ab9644d9ae95290807d660c0bd555186fc782091c9311",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_126_080p1810.dat",
          "sha256": "f436500faab79ac06a477f25279e666fc395aa1309f6206c4cfc370e5ab236dc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_127_079p2110.dat",
          "sha256": "565eb4a52e8001ab11d847cabe6c71db3de5288b55044202d1bead9792dc96aa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_128_078p2390.dat",
          "sha256": "32338a8411205faf0cdbb6c740df2867df4140f25564f687a87ed4f9e6b8457d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_129_077p2590.dat",
          "sha256": "9f6ed717261d3de98b96991b91ca1fb2b54eca19b47ec16838867caef8915dbb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_130_076p2370.dat",
          "sha256": "61a7e8264179201cf1419b47c7ae62cbea5ce243810c7415e974efee7f58948f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_131_075p2470.dat",
          "sha256": "641c94352867e68da1ac3169da18b4b95e5fcb04356bc23f6bcbcc2393546968",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_132_074p2460.dat",
          "sha256": "f8523d6cc3107326f4336d080b447d1ba2c6a065e51189ea14fa01401871f7da",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_133_073p2490.dat",
          "sha256": "0d2b0add7aa63374321bcadeb41c09b21b1619cba288b9595d6b0cd1abf3fdad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_134_072p2520.dat",
          "sha256": "d0591e7013ac0001709d1d1b21f9fa3d9be0ca6f0b0f2101ebecf861b4da3728",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_135_071p2550.dat",
          "sha256": "803b7a6ff8dd28c8f728105f00ca2cee7e73cc53137ba96de8974282143e975d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_136_070p2250.dat",
          "sha256": "798255d0b928feaead4de0698608821eb06915c5a4dd67b99a4815986b9557a1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_137_069p2340.dat",
          "sha256": "be0e5eabb2dcdf28b310958cda178b9777e974370c651e4f9d792adc049ef4b0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_138_068p2110.dat",
          "sha256": "0c9777ed8db46f31ebef1aa1c4b8ffb59f01208158e492151a65aa83770793d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_139_067p1860.dat",
          "sha256": "67e114cf9eb3ac20e1325b2271e20c9fa612ace8188d0056aecd232545054cf0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_140_066p2090.dat",
          "sha256": "29daac593288f93fb1c6f3c9633c3306571c1ab66bb37f3dcc64f606ab0a9e35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_141_065p2420.dat",
          "sha256": "fad943baa9b1621d072a1a2ffccc85e3091000062a45e2abf33637d5a002fc80",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_142_064p2810.dat",
          "sha256": "fd6f185b182b286b474bca2959a1a74c05125b7b6da907e1c1fc4f6b64119738",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_143_063p2750.dat",
          "sha256": "67f4d6e158ec69618c5be22eb762be95da14e754a0cfb5378dfa12518116d94e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_144_062p3420.dat",
          "sha256": "ed46ce55bfc090d19cff03c8583c977b76beea36d3ca9c73dc7fb443106c4dd0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_145_061p3970.dat",
          "sha256": "7a2da67d3d162992697ae55962ec0b05f4dc23df10a487fe3d3293e66d312779",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_146_060p4590.dat",
          "sha256": "6ae57bb627d9d02c5ff29b2c704252a8d3a6db30740e3c3ef15176f1b8df12d0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_147_059p5330.dat",
          "sha256": "795069a1c843c39047fa93a06d5470de4a455a1766ac46f3256dc969b10c6be4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_148_058p6120.dat",
          "sha256": "1b01909c754668e190702a9e431c1e6261ade0bde50c7c2ff2732b3c4c262e7b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_149_057p6970.dat",
          "sha256": "c669aa6aa7081b786c150c8f6b0ba3e85d25e637e907ba4f0b12ceee4b532d92",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_150_056p7860.dat",
          "sha256": "11d5df33f66162035b7475748d6f0eb50fef402628e35baef9527ccb86999dcc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_151_055p8750.dat",
          "sha256": "6d0fcc54e30995618e087169d843308e2edcf43198da06723237e67eb2bae203",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_152_054p9730.dat",
          "sha256": "fc0630582ea6a255ff3933ab0db9a5a6102dba721ccbf5edfb4727403790f15a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_153_054p0730.dat",
          "sha256": "f5cb618b08438919701e21e20051c3aa95cd3d48aadfdfedf5a2699b7f4da0e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_154_053p1720.dat",
          "sha256": "b1a9779c8a27da47bb1975645c7257101878758e16c1f5ea40b8a94f4f97f0a9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_155_052p3450.dat",
          "sha256": "c6ddfe0309c55ce450cdb1b9a0a009b1dd2a66b0616b3f39f911bc86fd64cc19",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_156_051p8630.dat",
          "sha256": "afd9c3153047f2348f032054326c34b7d00231e7a55be6ccafe0b9237c56602e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_157_051p8610.dat",
          "sha256": "811d12ff3ce0b8a2f0810233572120f3b7e4a9aa1f37dc1004b1caa498b0a2c8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_158_051p8530.dat",
          "sha256": "71fb1da8bf9ae6c13fb7e12305c7dbcdfab4eb55cb79c4bbd9fd679404bd9b25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_159_051p8480.dat",
          "sha256": "fa790d2e6485682af832719cf2c4072f4299677bffa67e71159b9ac4a1d754e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_160_051p7720.dat",
          "sha256": "f7de52240ea61be6602658e7ba18202c11c469cebb1c8cedca0b2184262d3b02",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_161_051p3070.dat",
          "sha256": "180edbe3e0f475f2238d43739ab946bacec6475c3e9286a81d66679128754cad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_162_050p4140.dat",
          "sha256": "145b3d0e82b0324eca2fc3da02ee15b890114e41a7883c7f70e0058a430f00f3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4137.396,
                28.207
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                418.492,
                8.717
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        }
      ],
      "loaderWarning": "",
      "files": {
        "project.edi": "13a55749dc2a65de3ff5d952d4009af27a5e882709c14747c59ca6aed6c6fd5b",
        "structures/cosio.edi": "4538c66b979d5783c2c3b5ba8c06494a54efeea3fc83c5488e89d5a10c0bb899",
        "experiments/d20.edi": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
        "analysis/analysis.edi": "0d463ba37e85baf7de2e4c08ac0d596a3756a50edea40b993b3120a9ae0209c6"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_scan-324f",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "cosio_d20_scan",
        "_metadata.created": "09 Sep 2026 07:33:40",
        "_metadata.last_modified": "23 Sep 2026 14:06:27",
        "_metadata.timestamp": "2026-09-09T07:34:35+00:00",
        "_rendering_plot.type": "auto",
        "_report.cif": "false",
        "_report.html": "true",
        "_report.tex": "false",
        "_report.pdf": "false",
        "_report.html_offline": "false",
        "_rendering_table.type": "auto",
        "_rendering_structure.type": "auto",
        "_structure_view.show_labels": "false",
        "_structure_view.show_moments": "true",
        "_structure_view.range_a_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_a_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_b_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_min": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_view.range_c_max": {
          "value": 1.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_view": "adp",
        "_structure_style.color_scheme": "jmol",
        "_structure_style.adp_probability": {
          "value": 0.99,
          "free": false,
          "uncertainty": 0.0
        },
        "_structure_style.atom_scale": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_verbosity.fit": "short",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Cooling and warming scan · 324 patterns between 50.4 and 497.4 K",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_sequential_fit.data_dir": "experiments/d20_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "false"
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.335842071204308,
          "spaceGroup": "P n m a",
          "cell": [
            10.335842071204308,
            6.029694577103228,
            4.797569862624058,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [
        {
          "file": "01_001_497p3790.dat",
          "sha256": "22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4024.358,
                31.828
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                442.251,
                10.252
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "01_002_497p3410.dat",
          "sha256": "ef3eaf0029ac15202d49952f66caf1d30a8d4ca3adf82e76f3a89ef4a843728d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_003_497p2280.dat",
          "sha256": "12df6cee20e6241e84a392053ef1ad6cb9cc153d96ddbd95b025ba79f4c22734",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_004_497p0360.dat",
          "sha256": "943ff86fb9bf5d264f4a2d41e64b1d5711f26ab76de4cb90c0545900e92c674e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_005_496p5900.dat",
          "sha256": "5f3023b3820eb243fe8186c8f9ff953e1325c0d767097174f77e94419f1d8094",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_006_495p3740.dat",
          "sha256": "f2025c68fdd8fc3de28b057382d9087ea6c0b92dbec0c1b9eca54dc0ef41f2d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_007_489p9560.dat",
          "sha256": "2898a2b6434c15f02eff1c1994fa8c896c6d92b93d15a15994854e75be060aef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_008_485p7350.dat",
          "sha256": "de3f00765f6765b80157d75947c7517e997dfea579adcc76251fe644a9a7ba70",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_009_481p2260.dat",
          "sha256": "021d76aad5f57879aefa516eefc96418536d0f42af793e6a0d47d6f407e05005",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_010_476p9800.dat",
          "sha256": "1dc012ecb202cb10c04d5a70be15c2a9734c2b37d547f564ecee9d2c9abedefa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_011_472p5840.dat",
          "sha256": "acd16e373fdfe9e3cc5c597be55ec304109578badf82df8743d69f07a58ca9c0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_012_468p2800.dat",
          "sha256": "f78b5d3d9da83a3f003535847f2610e52e7dfd8374ee5950a0c3c34109f56462",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_013_463p8850.dat",
          "sha256": "d5c22e9a92bfaf425cd6ab3633325319d7a62db6e65d3916e97447c6422fd30c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_014_459p2510.dat",
          "sha256": "dd07ea491ebb2a9fd37a9b0a6204e82367ea4a1954315778ceb2fe585d93bbd4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_015_454p8870.dat",
          "sha256": "48231f25702a2c8e550c09f6272b5305549297e7647b59b7a3d8d6b28810b1a4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_016_450p3320.dat",
          "sha256": "6e363f78be7d54a57830bca46b5bd0a18f768f6b15dd8a68ed6c1d292216fb03",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_017_446p0030.dat",
          "sha256": "89c898df19634d5672e76798c37bc9e8551bb5678767e988bc41d735173483e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_018_441p4020.dat",
          "sha256": "aca3572c999b8cf60592ea7b884f67ecc8a90664361f4e6aa15590b6ef8ea6e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_019_437p1320.dat",
          "sha256": "f6418e949ff522365390f777c197ab7fbd9d76cded8c04d7d4a509a51e8b877b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_020_433p0150.dat",
          "sha256": "a3d5a690e7a7b31263035b240181507e751f6b7f0ba35b77c29cd82d6bb535fd",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_021_428p4870.dat",
          "sha256": "b80cc00f57695d56589aa857d1c72fd921acc2ec2c45adecc4d2901e49e3bff4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_022_424p1020.dat",
          "sha256": "458d5d83a455d35efe65f3a9a518cf0b66d677b280be587868a6cb9e7af2db38",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_023_419p4530.dat",
          "sha256": "33611d2a5959694b1dbe9d228db99613afe5431bc35a43e61764267a73be83d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_024_415p1880.dat",
          "sha256": "7a9fdd55cf98f32e0ec00e042999c4555b5c818c9429d6daf41fc7a166bac478",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_025_410p7830.dat",
          "sha256": "d0e151a4805a8c29be88b33249f11e1f5414e9de25dffde20869b202cdeb72ec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_026_406p1830.dat",
          "sha256": "7fa18447b1981382d68d30c896b87af509f6bba264bc1013af1650cb5b34383e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_027_402p1390.dat",
          "sha256": "a68b8fae71666b66d6139375978379ab63ce7facb1f4c63a343262c47e81270b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_028_397p5640.dat",
          "sha256": "450d09ba353d52cf88805f153913f308ec51428aa279649911a5297dd4106f25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_029_393p2660.dat",
          "sha256": "6ebb10a745535d973fbaa3aa16bcf57f163ad99d67cedb123f6739cc0d19989a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_030_388p8760.dat",
          "sha256": "2fe4da899cfec93b4685f5ddf48cb98f639901dc2239bced310739522ed301ba",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_031_384p6000.dat",
          "sha256": "c051142ae04c23efe2323ca6ffbbdf39ee6571371d26dcc00c1cf592ff97ee55",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_032_380p2820.dat",
          "sha256": "e03e997f68637b4df7b60513c7845a260b01726f3f67fa804b355a71b94de8f5",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_033_375p8110.dat",
          "sha256": "a56ff8f5849e1e3fe67b6858352fcc88c24a53cfe579df98e97d48c2e2d9f055",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_034_371p4350.dat",
          "sha256": "76e2fd2646d8c37d1d357e4479b20e29a47c41ee357614f7d947a8c1fcbb7ce3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_035_362p8190.dat",
          "sha256": "424bea57f499991eb8aa7d224373a6bd73d0107c0977c06f0db15ed1eaab8ccc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_036_358p4140.dat",
          "sha256": "1006fc6e31bbd16528ac73eccd0e115148bcdfb75b397df5a11a5849d96131bc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_037_354p1160.dat",
          "sha256": "0e6a05e598dadc199dd04823bed2db908f96e104cbb5359fc824893a657adc1f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_038_349p8060.dat",
          "sha256": "206f085b19fa066d2b473479221c460287a40f19f5e7c1f0320c2979c8ffe32a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_039_345p2570.dat",
          "sha256": "5f1b51a111b63db9d3154dd6fa9e2dfc1c18cdaccfcd38a0f6cc97dae5e79615",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_040_340p7230.dat",
          "sha256": "7855c5f97795bcb99310acd974b65fc6aad8a5d157f41aec9bdf2802533414ac",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_041_336p6280.dat",
          "sha256": "10d3cb20af02ac533a17e0966dd41f3fb80f80bfdc5e2763d4e92b08485640f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_042_332p2660.dat",
          "sha256": "03fe53d66954d3935bbbca3c39dda6ec625c1f5627c6eb6d89e94d0364ade80e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_043_327p9190.dat",
          "sha256": "f8dbe59316ee34514cf8ddd5502b5b53609276ce3117e05d87ac7ac9afd97aec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_044_323p3350.dat",
          "sha256": "c038f2e38226ad3fd2281b55fbb39cf04a6ef2dc3d4f0276b5c8bf0ba393024f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_045_319p0710.dat",
          "sha256": "5c2058a222ef253a0f46235b9615cf957e6414b4e52f4138dfb64be5fd173af4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_046_314p8200.dat",
          "sha256": "08d4bf74090bd142686ba02fe36c6642f4117480d0f9026b3e3a307ca64b6ed8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_047_310p9350.dat",
          "sha256": "fec1490aaf6f59a7464c3b21cdedf6333cb3d764f8d9a13ac62478cb2d981afa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_048_306p6800.dat",
          "sha256": "29e6848c38f889e1bc839bac949c3b2404abe2f9a652a604fc4542fe55d52dc3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_049_303p0940.dat",
          "sha256": "70240b3346e701baaa43629897aeb121f54cd19aff707eabe45d2524844ca664",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_050_300p4240.dat",
          "sha256": "92e8342610fa5d0f5a749a9b4dc29479c3ac75b052db2c9a2393155bf354b28c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_051_299p3940.dat",
          "sha256": "dd2bf75b4d8e3ae22bf9643d3be77773d3b5317b6ab8a273b802bb3640059874",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_052_299p2050.dat",
          "sha256": "4565452f1baca8f389bcf7d8e47faef032fc945105c95923f74ddd4b6709c410",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_053_298p8330.dat",
          "sha256": "841b483ddd09b3c2e767db9bb9890c5ac2d1d3a937b51da72f3bc18871e3e79b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_054_298p0250.dat",
          "sha256": "eb716b2eecde0c12d3329a5651ab8d3945e07d0929a802c164b15868861dd689",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_055_296p4040.dat",
          "sha256": "acf75bbc5a6a1e60f2fec3d8e7d6101374ee8528af85817d84a816c2681eca6a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_056_290p7210.dat",
          "sha256": "940bcd89b8fe5ac1ac574ac558dcc921e82ea8b40238c76209b0bc786ad22eee",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_057_286p2140.dat",
          "sha256": "90525f159ad2e7b5dba17ba5e5a817b03e81b9bb850373e34de26fc30e00bd8d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_058_281p9010.dat",
          "sha256": "243f7d2144ece905f6de4f72acbff36fad21f42706937370f63b21afdd3ba325",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_059_277p4860.dat",
          "sha256": "7283650bc9654d294ddb40e2e97f293f9be346e04dc3b01ab80def0c379ddba1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_060_273p0910.dat",
          "sha256": "6e6045caf495e42b716d4a14b0544ae4465e7f61b9db4200b8740f2137c33043",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_061_268p6170.dat",
          "sha256": "56ae5f39aff745c323b4143c019c828b649dd24cb38b6dd995710f747cdea63b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_062_264p2270.dat",
          "sha256": "cac5e46d43612d7f3e44829e0b83606258443922c94ab58cf5f5da9767e1eef3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_063_259p8830.dat",
          "sha256": "7d831ef5c563487fead89e89d0b2f663265a34c8d8d1ca8615f7147fa88926d9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_064_255p4710.dat",
          "sha256": "9b7bee4d7bce1b21a6c949784dcc77cbe1c4f68dac20b6e1f5403d7e416892ff",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_065_250p8860.dat",
          "sha256": "5f1d25db589640730d6dfb7c267af35b6c0d108e30e927467c780335b65b711c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_066_246p4910.dat",
          "sha256": "1475795b475c580b6bebef7a47b544c125adb53e056c5e0234cc04943212fdda",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_067_242p0240.dat",
          "sha256": "a809c348dc88901c28d6a2bba6675fdcd92759739b52287aef810827d9350872",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_068_237p6280.dat",
          "sha256": "17bc9c32998fc52f5a707528e0bb34a5f5a3c758460c06a680106d7f8b15d509",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_069_233p1580.dat",
          "sha256": "353eb5a64530acc7d801ff266b4c26a28edf1f0d106cb53f31b1dabb0784cac1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_070_228p8500.dat",
          "sha256": "fa65084b98954849ab8c758c025c9d54844eccf44191b4a17f0af0048cc2aafb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_071_224p4280.dat",
          "sha256": "1d3a611527ac7c9e20d2630f570ba3d2501d06c203f30b135d59d71dc6c24607",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_072_220p0320.dat",
          "sha256": "b96c8d59b7f83d69264b2f0b9d788f510424ba4b05ab05877b3f378ea28971ea",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_073_215p5290.dat",
          "sha256": "2bb93ecf6d608b203a456fc6105f09a4da91fabdb918040bdca1f376e4eb20e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_074_211p2050.dat",
          "sha256": "de09bfbe03355eb1707e5a3f9782e5e8264b6306003ea3c43340853cd98378e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_075_206p8010.dat",
          "sha256": "b25f8a037ebda34163d413ad3f86663a10c2de1e16479dbcd0213318421cdb6b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_076_202p4320.dat",
          "sha256": "850dc3873eb6e1351365d111421a6dd56965d3f13096f8a99761fdaf45939b6f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_077_198p0270.dat",
          "sha256": "821331225f83ffebfd52964851dc3d87b99f2767afc0229014d755b2ad93961a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_078_193p7040.dat",
          "sha256": "0f3bd513597e7753ac9be045536f431e00616e13b7d4d7a69d94bf9bb5660ed6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_079_189p3940.dat",
          "sha256": "9fd207d48eb77ecf979aaaa1cfcb1efe09edfa7259a5b26150a9669a70b5ec86",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_080_184p9760.dat",
          "sha256": "be54656813c1d4be8e78e622770e4bbc63e2f78e8600097dbae0337a2ace7f15",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_081_180p6510.dat",
          "sha256": "a35ba186cfd2383fc5610becdcd625108a38e3606c48aab96cff1f1a6d49d0cb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_082_176p5080.dat",
          "sha256": "99e844a0e5fcf2cabb3afcb4e54e7b6685d3678191371241417600b878b78e9d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_083_172p2020.dat",
          "sha256": "adab65cb6294027bb3ae955a72eb27eec38f463125f8747d5ca95c22f6f7d7b2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_084_167p8070.dat",
          "sha256": "cccb96e06d3430b50321be31f750bce1d93c9577e8baf8fe6b5571e838e9d483",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_085_163p5550.dat",
          "sha256": "b49dda0e6f80077784a6e3075d6f3e5c277b2ea61c381fb54eeca92abcf088c3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_086_159p2290.dat",
          "sha256": "e0412cd8d7fc27c4a70276f921cf3bd2fc42216399bc37347529045cbabd3bf2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_087_154p8790.dat",
          "sha256": "786ec6d894d6c72e98bcd75a6f6d33f79e67380ecd6f1306518cd702ced85776",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_088_150p5940.dat",
          "sha256": "9bef7dde185a0e05295b7b2cfc571759148a38b5a9e7d20c2ebb7155ce77b9f6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_089_146p2570.dat",
          "sha256": "187774183b67a14b26fd9ca37fd2c83e1499c685aeacca49d269875e4f27fe21",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_090_142p0530.dat",
          "sha256": "2f52bfef144edebe852b12e23351f05f97e50a573181c1f2c14383444bd16987",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_091_137p9060.dat",
          "sha256": "9cbb27d5e6862e44010e27b37e2e6bc092eff833555d83a6bb40c2ff4ddc7b2c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_092_133p7450.dat",
          "sha256": "ed8e8a37b1b57b1ec606e2c5ee57d40d946d34249e879ab44fd5505c79f1da45",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_093_129p5840.dat",
          "sha256": "48b543ba633903102e0be89434ef4269cfec2faabddcc4209471a1228d63491e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_094_125p4340.dat",
          "sha256": "a5fc59c5920f766e8057cde53301488b64fb737f2fe69ea2db029d8a1d6c6124",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_095_121p3580.dat",
          "sha256": "31e9e79b02c15a215dfb9d25f79e69a9989b8f69413608a04954c3392733de27",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_096_117p1490.dat",
          "sha256": "1e9cd3e8c1ec347cb153e9cef1754912b90d64919206cba528ec107579b7f71b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_097_113p0630.dat",
          "sha256": "04e9db3d4b807c246171fa9efc761987edd89b8e4c0bbbc4db58149e2e21d61f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_098_109p2600.dat",
          "sha256": "fe318a1be180fe8bb36553072a06fcb914716f775e4178c57196c3f54bbe7440",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_099_105p6360.dat",
          "sha256": "a1db92e7f37ab2530b18f9c979e7626e81d320fdc62e0a99ad6b55257912ea08",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_100_103p0030.dat",
          "sha256": "2c963c020313193b28e64a42e7d217b52e3548dbd22e17a6bb1ce212b19ecc99",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_101_101p9130.dat",
          "sha256": "b60e169864b4fcc0a34c5cd18bdcda39eb73565319b70d1dcea644602e266bcf",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_102_101p8800.dat",
          "sha256": "fce7aae98c761517eab36c3435fad63f1b54b42cfeed5d9aa3dd6cc52507cade",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_103_101p8220.dat",
          "sha256": "380ec121a9e49a470b3cb567c66739ccba346c9959ea8ac3e7f5d5866d7aec8c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_104_101p6830.dat",
          "sha256": "660fd2627db86042128122ba1979627462e9787bed8746fb3683891a726bf9b4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_105_101p3630.dat",
          "sha256": "122de03f7e29f0ba58bfa1e62a16d21f1d70ac179f7150af95825078a1b377d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_106_100p5400.dat",
          "sha256": "2cdd6346481323006d05564bdd8c58cc7522e6440ef5333d785abf2def2f9efa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_107_099p5650.dat",
          "sha256": "28eaf543a7cc252ac4e9f82c0c449071c9892e3306483c929232a28efe10f4f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_108_098p5500.dat",
          "sha256": "6a23ea8bcc2c3014e7d5fb60d525105a6c1ba1d4908f6042535ee90192b77219",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_109_097p5340.dat",
          "sha256": "f1fb0335a3df055a0dd1d468f23c430aef3d41c33555c684d8e4ced5ed4ba78e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_110_096p4920.dat",
          "sha256": "bb9babfd6b49b4cb019f007ac4f9683a14c8dc9f89fc9eddd092677094bf41de",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_111_095p5170.dat",
          "sha256": "23e84372a799fba239ccc6e3c7beac018b9c17c73c3ebf43ccf1d332cddb677b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_112_094p4880.dat",
          "sha256": "fbb59687dfec327ef1368e073bdf04a3b61fc071a78f89803751235ea32ab9fb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_113_093p4840.dat",
          "sha256": "91e30e877319e41a9a13e9ea2171d71f9de992c31e9ec6bd063f92e7c9c3e228",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_114_092p4800.dat",
          "sha256": "341c1a1e0b27ed7b8182971ab13b4cf68657d5b9f40e78e9f68efea059fb3e67",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_115_091p4890.dat",
          "sha256": "d4b270af7d468e0cb960a7b8a1e821a7e5565e65c7f9cdd2596ac325e63ae415",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_116_090p4890.dat",
          "sha256": "fdff650c5d456acb17b8d145c38c0bc0929eccd291570e39d734711bfd2ccb35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_117_089p4800.dat",
          "sha256": "a9a99d3e263c724b28b8b945b30e7846101952a87cad1458138e43a8adca77fe",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_118_088p4620.dat",
          "sha256": "a5971a3ea8bd0c09c26df43e41f00ba736066fc4d8d052b74b7196f0658780ef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_119_087p4450.dat",
          "sha256": "6fe2f51b48a833d73b7be41dab21f6cda08a054dcb817a9601671c323f8d988e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_120_086p4230.dat",
          "sha256": "c69586ac805e3af61a33d90b87e635e7f895b724c78f32f02211b28203fe4a13",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_121_085p3880.dat",
          "sha256": "356f9e9f7f7d96f760a789bb577e15d5e42ede954fffaefb21fbc6cc8c8e1424",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_122_084p3500.dat",
          "sha256": "5546c302c3af0bd2bb86386677de6e13c30a8808fca1271631cb228a7f4d650f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_123_083p2780.dat",
          "sha256": "ab54111a4bad28e9b194ea9c79b824204b9fe57cd2e3592c9037d2217118e957",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_124_082p1890.dat",
          "sha256": "b5426601315463137a772b5a2f38cc75bfca98a567d576b24ca4cc53c2721933",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_125_081p1590.dat",
          "sha256": "0d8bfe903fe180e35e3ab9644d9ae95290807d660c0bd555186fc782091c9311",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_126_080p1810.dat",
          "sha256": "f436500faab79ac06a477f25279e666fc395aa1309f6206c4cfc370e5ab236dc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_127_079p2110.dat",
          "sha256": "565eb4a52e8001ab11d847cabe6c71db3de5288b55044202d1bead9792dc96aa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_128_078p2390.dat",
          "sha256": "32338a8411205faf0cdbb6c740df2867df4140f25564f687a87ed4f9e6b8457d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_129_077p2590.dat",
          "sha256": "9f6ed717261d3de98b96991b91ca1fb2b54eca19b47ec16838867caef8915dbb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_130_076p2370.dat",
          "sha256": "61a7e8264179201cf1419b47c7ae62cbea5ce243810c7415e974efee7f58948f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_131_075p2470.dat",
          "sha256": "641c94352867e68da1ac3169da18b4b95e5fcb04356bc23f6bcbcc2393546968",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_132_074p2460.dat",
          "sha256": "f8523d6cc3107326f4336d080b447d1ba2c6a065e51189ea14fa01401871f7da",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_133_073p2490.dat",
          "sha256": "0d2b0add7aa63374321bcadeb41c09b21b1619cba288b9595d6b0cd1abf3fdad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_134_072p2520.dat",
          "sha256": "d0591e7013ac0001709d1d1b21f9fa3d9be0ca6f0b0f2101ebecf861b4da3728",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_135_071p2550.dat",
          "sha256": "803b7a6ff8dd28c8f728105f00ca2cee7e73cc53137ba96de8974282143e975d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_136_070p2250.dat",
          "sha256": "798255d0b928feaead4de0698608821eb06915c5a4dd67b99a4815986b9557a1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_137_069p2340.dat",
          "sha256": "be0e5eabb2dcdf28b310958cda178b9777e974370c651e4f9d792adc049ef4b0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_138_068p2110.dat",
          "sha256": "0c9777ed8db46f31ebef1aa1c4b8ffb59f01208158e492151a65aa83770793d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_139_067p1860.dat",
          "sha256": "67e114cf9eb3ac20e1325b2271e20c9fa612ace8188d0056aecd232545054cf0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_140_066p2090.dat",
          "sha256": "29daac593288f93fb1c6f3c9633c3306571c1ab66bb37f3dcc64f606ab0a9e35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_141_065p2420.dat",
          "sha256": "fad943baa9b1621d072a1a2ffccc85e3091000062a45e2abf33637d5a002fc80",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_142_064p2810.dat",
          "sha256": "fd6f185b182b286b474bca2959a1a74c05125b7b6da907e1c1fc4f6b64119738",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_143_063p2750.dat",
          "sha256": "67f4d6e158ec69618c5be22eb762be95da14e754a0cfb5378dfa12518116d94e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_144_062p3420.dat",
          "sha256": "ed46ce55bfc090d19cff03c8583c977b76beea36d3ca9c73dc7fb443106c4dd0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_145_061p3970.dat",
          "sha256": "7a2da67d3d162992697ae55962ec0b05f4dc23df10a487fe3d3293e66d312779",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_146_060p4590.dat",
          "sha256": "6ae57bb627d9d02c5ff29b2c704252a8d3a6db30740e3c3ef15176f1b8df12d0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_147_059p5330.dat",
          "sha256": "795069a1c843c39047fa93a06d5470de4a455a1766ac46f3256dc969b10c6be4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_148_058p6120.dat",
          "sha256": "1b01909c754668e190702a9e431c1e6261ade0bde50c7c2ff2732b3c4c262e7b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_149_057p6970.dat",
          "sha256": "c669aa6aa7081b786c150c8f6b0ba3e85d25e637e907ba4f0b12ceee4b532d92",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_150_056p7860.dat",
          "sha256": "11d5df33f66162035b7475748d6f0eb50fef402628e35baef9527ccb86999dcc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_151_055p8750.dat",
          "sha256": "6d0fcc54e30995618e087169d843308e2edcf43198da06723237e67eb2bae203",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_152_054p9730.dat",
          "sha256": "fc0630582ea6a255ff3933ab0db9a5a6102dba721ccbf5edfb4727403790f15a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_153_054p0730.dat",
          "sha256": "f5cb618b08438919701e21e20051c3aa95cd3d48aadfdfedf5a2699b7f4da0e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_154_053p1720.dat",
          "sha256": "b1a9779c8a27da47bb1975645c7257101878758e16c1f5ea40b8a94f4f97f0a9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_155_052p3450.dat",
          "sha256": "c6ddfe0309c55ce450cdb1b9a0a009b1dd2a66b0616b3f39f911bc86fd64cc19",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_156_051p8630.dat",
          "sha256": "afd9c3153047f2348f032054326c34b7d00231e7a55be6ccafe0b9237c56602e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_157_051p8610.dat",
          "sha256": "811d12ff3ce0b8a2f0810233572120f3b7e4a9aa1f37dc1004b1caa498b0a2c8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_158_051p8530.dat",
          "sha256": "71fb1da8bf9ae6c13fb7e12305c7dbcdfab4eb55cb79c4bbd9fd679404bd9b25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_159_051p8480.dat",
          "sha256": "fa790d2e6485682af832719cf2c4072f4299677bffa67e71159b9ac4a1d754e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_160_051p7720.dat",
          "sha256": "f7de52240ea61be6602658e7ba18202c11c469cebb1c8cedca0b2184262d3b02",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_161_051p3070.dat",
          "sha256": "180edbe3e0f475f2238d43739ab946bacec6475c3e9286a81d66679128754cad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_162_050p4140.dat",
          "sha256": "145b3d0e82b0324eca2fc3da02ee15b890114e41a7883c7f70e0058a430f00f3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_001_050p4140.dat",
          "sha256": "145b3d0e82b0324eca2fc3da02ee15b890114e41a7883c7f70e0058a430f00f3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4137.396,
                28.207
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                418.492,
                8.717
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "02_002_051p3070.dat",
          "sha256": "180edbe3e0f475f2238d43739ab946bacec6475c3e9286a81d66679128754cad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_003_051p7720.dat",
          "sha256": "f7de52240ea61be6602658e7ba18202c11c469cebb1c8cedca0b2184262d3b02",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_004_051p8480.dat",
          "sha256": "fa790d2e6485682af832719cf2c4072f4299677bffa67e71159b9ac4a1d754e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_005_051p8530.dat",
          "sha256": "71fb1da8bf9ae6c13fb7e12305c7dbcdfab4eb55cb79c4bbd9fd679404bd9b25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_006_051p8610.dat",
          "sha256": "811d12ff3ce0b8a2f0810233572120f3b7e4a9aa1f37dc1004b1caa498b0a2c8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_007_051p8630.dat",
          "sha256": "afd9c3153047f2348f032054326c34b7d00231e7a55be6ccafe0b9237c56602e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_008_052p3450.dat",
          "sha256": "c6ddfe0309c55ce450cdb1b9a0a009b1dd2a66b0616b3f39f911bc86fd64cc19",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_009_053p1720.dat",
          "sha256": "b1a9779c8a27da47bb1975645c7257101878758e16c1f5ea40b8a94f4f97f0a9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_010_054p0730.dat",
          "sha256": "f5cb618b08438919701e21e20051c3aa95cd3d48aadfdfedf5a2699b7f4da0e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_011_054p9730.dat",
          "sha256": "fc0630582ea6a255ff3933ab0db9a5a6102dba721ccbf5edfb4727403790f15a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_012_055p8750.dat",
          "sha256": "6d0fcc54e30995618e087169d843308e2edcf43198da06723237e67eb2bae203",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_013_056p7860.dat",
          "sha256": "11d5df33f66162035b7475748d6f0eb50fef402628e35baef9527ccb86999dcc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_014_057p6970.dat",
          "sha256": "c669aa6aa7081b786c150c8f6b0ba3e85d25e637e907ba4f0b12ceee4b532d92",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_015_058p6120.dat",
          "sha256": "1b01909c754668e190702a9e431c1e6261ade0bde50c7c2ff2732b3c4c262e7b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_016_059p5330.dat",
          "sha256": "795069a1c843c39047fa93a06d5470de4a455a1766ac46f3256dc969b10c6be4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_017_060p4590.dat",
          "sha256": "6ae57bb627d9d02c5ff29b2c704252a8d3a6db30740e3c3ef15176f1b8df12d0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_018_061p3970.dat",
          "sha256": "7a2da67d3d162992697ae55962ec0b05f4dc23df10a487fe3d3293e66d312779",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_019_062p3420.dat",
          "sha256": "ed46ce55bfc090d19cff03c8583c977b76beea36d3ca9c73dc7fb443106c4dd0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_020_063p2750.dat",
          "sha256": "67f4d6e158ec69618c5be22eb762be95da14e754a0cfb5378dfa12518116d94e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_021_064p2810.dat",
          "sha256": "fd6f185b182b286b474bca2959a1a74c05125b7b6da907e1c1fc4f6b64119738",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_022_065p2420.dat",
          "sha256": "fad943baa9b1621d072a1a2ffccc85e3091000062a45e2abf33637d5a002fc80",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_023_066p2090.dat",
          "sha256": "29daac593288f93fb1c6f3c9633c3306571c1ab66bb37f3dcc64f606ab0a9e35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_024_067p1860.dat",
          "sha256": "67e114cf9eb3ac20e1325b2271e20c9fa612ace8188d0056aecd232545054cf0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_025_068p2110.dat",
          "sha256": "0c9777ed8db46f31ebef1aa1c4b8ffb59f01208158e492151a65aa83770793d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_026_069p2340.dat",
          "sha256": "be0e5eabb2dcdf28b310958cda178b9777e974370c651e4f9d792adc049ef4b0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_027_070p2250.dat",
          "sha256": "798255d0b928feaead4de0698608821eb06915c5a4dd67b99a4815986b9557a1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_028_071p2550.dat",
          "sha256": "803b7a6ff8dd28c8f728105f00ca2cee7e73cc53137ba96de8974282143e975d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_029_072p2520.dat",
          "sha256": "d0591e7013ac0001709d1d1b21f9fa3d9be0ca6f0b0f2101ebecf861b4da3728",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_030_073p2490.dat",
          "sha256": "0d2b0add7aa63374321bcadeb41c09b21b1619cba288b9595d6b0cd1abf3fdad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_031_074p2460.dat",
          "sha256": "f8523d6cc3107326f4336d080b447d1ba2c6a065e51189ea14fa01401871f7da",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_032_075p2470.dat",
          "sha256": "641c94352867e68da1ac3169da18b4b95e5fcb04356bc23f6bcbcc2393546968",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_033_076p2370.dat",
          "sha256": "61a7e8264179201cf1419b47c7ae62cbea5ce243810c7415e974efee7f58948f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_034_077p2590.dat",
          "sha256": "9f6ed717261d3de98b96991b91ca1fb2b54eca19b47ec16838867caef8915dbb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_035_078p2390.dat",
          "sha256": "32338a8411205faf0cdbb6c740df2867df4140f25564f687a87ed4f9e6b8457d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_036_079p2110.dat",
          "sha256": "565eb4a52e8001ab11d847cabe6c71db3de5288b55044202d1bead9792dc96aa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_037_080p1810.dat",
          "sha256": "f436500faab79ac06a477f25279e666fc395aa1309f6206c4cfc370e5ab236dc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_038_081p1590.dat",
          "sha256": "0d8bfe903fe180e35e3ab9644d9ae95290807d660c0bd555186fc782091c9311",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_039_082p1890.dat",
          "sha256": "b5426601315463137a772b5a2f38cc75bfca98a567d576b24ca4cc53c2721933",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_040_083p2780.dat",
          "sha256": "ab54111a4bad28e9b194ea9c79b824204b9fe57cd2e3592c9037d2217118e957",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_041_084p3500.dat",
          "sha256": "5546c302c3af0bd2bb86386677de6e13c30a8808fca1271631cb228a7f4d650f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_042_085p3880.dat",
          "sha256": "356f9e9f7f7d96f760a789bb577e15d5e42ede954fffaefb21fbc6cc8c8e1424",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_043_086p4230.dat",
          "sha256": "c69586ac805e3af61a33d90b87e635e7f895b724c78f32f02211b28203fe4a13",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_044_087p4450.dat",
          "sha256": "6fe2f51b48a833d73b7be41dab21f6cda08a054dcb817a9601671c323f8d988e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_045_088p4620.dat",
          "sha256": "a5971a3ea8bd0c09c26df43e41f00ba736066fc4d8d052b74b7196f0658780ef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_046_089p4800.dat",
          "sha256": "a9a99d3e263c724b28b8b945b30e7846101952a87cad1458138e43a8adca77fe",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_047_090p4890.dat",
          "sha256": "fdff650c5d456acb17b8d145c38c0bc0929eccd291570e39d734711bfd2ccb35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_048_091p4890.dat",
          "sha256": "d4b270af7d468e0cb960a7b8a1e821a7e5565e65c7f9cdd2596ac325e63ae415",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_049_092p4800.dat",
          "sha256": "341c1a1e0b27ed7b8182971ab13b4cf68657d5b9f40e78e9f68efea059fb3e67",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_050_093p4840.dat",
          "sha256": "91e30e877319e41a9a13e9ea2171d71f9de992c31e9ec6bd063f92e7c9c3e228",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_051_094p4880.dat",
          "sha256": "fbb59687dfec327ef1368e073bdf04a3b61fc071a78f89803751235ea32ab9fb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_052_095p5170.dat",
          "sha256": "23e84372a799fba239ccc6e3c7beac018b9c17c73c3ebf43ccf1d332cddb677b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_053_096p4920.dat",
          "sha256": "bb9babfd6b49b4cb019f007ac4f9683a14c8dc9f89fc9eddd092677094bf41de",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_054_097p5340.dat",
          "sha256": "f1fb0335a3df055a0dd1d468f23c430aef3d41c33555c684d8e4ced5ed4ba78e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_055_098p5500.dat",
          "sha256": "6a23ea8bcc2c3014e7d5fb60d525105a6c1ba1d4908f6042535ee90192b77219",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_056_099p5650.dat",
          "sha256": "28eaf543a7cc252ac4e9f82c0c449071c9892e3306483c929232a28efe10f4f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_057_100p5400.dat",
          "sha256": "2cdd6346481323006d05564bdd8c58cc7522e6440ef5333d785abf2def2f9efa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_058_101p3630.dat",
          "sha256": "122de03f7e29f0ba58bfa1e62a16d21f1d70ac179f7150af95825078a1b377d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_059_101p6830.dat",
          "sha256": "660fd2627db86042128122ba1979627462e9787bed8746fb3683891a726bf9b4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_060_101p8220.dat",
          "sha256": "380ec121a9e49a470b3cb567c66739ccba346c9959ea8ac3e7f5d5866d7aec8c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_061_101p8800.dat",
          "sha256": "fce7aae98c761517eab36c3435fad63f1b54b42cfeed5d9aa3dd6cc52507cade",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_062_101p9130.dat",
          "sha256": "b60e169864b4fcc0a34c5cd18bdcda39eb73565319b70d1dcea644602e266bcf",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_063_103p0030.dat",
          "sha256": "2c963c020313193b28e64a42e7d217b52e3548dbd22e17a6bb1ce212b19ecc99",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_064_105p6360.dat",
          "sha256": "a1db92e7f37ab2530b18f9c979e7626e81d320fdc62e0a99ad6b55257912ea08",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_065_109p2600.dat",
          "sha256": "fe318a1be180fe8bb36553072a06fcb914716f775e4178c57196c3f54bbe7440",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_066_113p0630.dat",
          "sha256": "04e9db3d4b807c246171fa9efc761987edd89b8e4c0bbbc4db58149e2e21d61f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_067_117p1490.dat",
          "sha256": "1e9cd3e8c1ec347cb153e9cef1754912b90d64919206cba528ec107579b7f71b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_068_121p3580.dat",
          "sha256": "31e9e79b02c15a215dfb9d25f79e69a9989b8f69413608a04954c3392733de27",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_069_125p4340.dat",
          "sha256": "a5fc59c5920f766e8057cde53301488b64fb737f2fe69ea2db029d8a1d6c6124",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_070_129p5840.dat",
          "sha256": "48b543ba633903102e0be89434ef4269cfec2faabddcc4209471a1228d63491e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_071_133p7450.dat",
          "sha256": "ed8e8a37b1b57b1ec606e2c5ee57d40d946d34249e879ab44fd5505c79f1da45",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_072_137p9060.dat",
          "sha256": "9cbb27d5e6862e44010e27b37e2e6bc092eff833555d83a6bb40c2ff4ddc7b2c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_073_142p0530.dat",
          "sha256": "2f52bfef144edebe852b12e23351f05f97e50a573181c1f2c14383444bd16987",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_074_146p2570.dat",
          "sha256": "187774183b67a14b26fd9ca37fd2c83e1499c685aeacca49d269875e4f27fe21",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_075_150p5940.dat",
          "sha256": "9bef7dde185a0e05295b7b2cfc571759148a38b5a9e7d20c2ebb7155ce77b9f6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_076_154p8790.dat",
          "sha256": "786ec6d894d6c72e98bcd75a6f6d33f79e67380ecd6f1306518cd702ced85776",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_077_159p2290.dat",
          "sha256": "e0412cd8d7fc27c4a70276f921cf3bd2fc42216399bc37347529045cbabd3bf2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_078_163p5550.dat",
          "sha256": "b49dda0e6f80077784a6e3075d6f3e5c277b2ea61c381fb54eeca92abcf088c3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_079_167p8070.dat",
          "sha256": "cccb96e06d3430b50321be31f750bce1d93c9577e8baf8fe6b5571e838e9d483",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_080_172p2020.dat",
          "sha256": "adab65cb6294027bb3ae955a72eb27eec38f463125f8747d5ca95c22f6f7d7b2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_081_176p5080.dat",
          "sha256": "99e844a0e5fcf2cabb3afcb4e54e7b6685d3678191371241417600b878b78e9d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_082_180p6510.dat",
          "sha256": "a35ba186cfd2383fc5610becdcd625108a38e3606c48aab96cff1f1a6d49d0cb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_083_184p9760.dat",
          "sha256": "be54656813c1d4be8e78e622770e4bbc63e2f78e8600097dbae0337a2ace7f15",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_084_189p3940.dat",
          "sha256": "9fd207d48eb77ecf979aaaa1cfcb1efe09edfa7259a5b26150a9669a70b5ec86",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_085_193p7040.dat",
          "sha256": "0f3bd513597e7753ac9be045536f431e00616e13b7d4d7a69d94bf9bb5660ed6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_086_198p0270.dat",
          "sha256": "821331225f83ffebfd52964851dc3d87b99f2767afc0229014d755b2ad93961a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_087_202p4320.dat",
          "sha256": "850dc3873eb6e1351365d111421a6dd56965d3f13096f8a99761fdaf45939b6f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_088_206p8010.dat",
          "sha256": "b25f8a037ebda34163d413ad3f86663a10c2de1e16479dbcd0213318421cdb6b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_089_211p2050.dat",
          "sha256": "de09bfbe03355eb1707e5a3f9782e5e8264b6306003ea3c43340853cd98378e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_090_215p5290.dat",
          "sha256": "2bb93ecf6d608b203a456fc6105f09a4da91fabdb918040bdca1f376e4eb20e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_091_220p0320.dat",
          "sha256": "b96c8d59b7f83d69264b2f0b9d788f510424ba4b05ab05877b3f378ea28971ea",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_092_224p4280.dat",
          "sha256": "1d3a611527ac7c9e20d2630f570ba3d2501d06c203f30b135d59d71dc6c24607",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_093_228p8500.dat",
          "sha256": "fa65084b98954849ab8c758c025c9d54844eccf44191b4a17f0af0048cc2aafb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_094_233p1580.dat",
          "sha256": "353eb5a64530acc7d801ff266b4c26a28edf1f0d106cb53f31b1dabb0784cac1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_095_237p6280.dat",
          "sha256": "17bc9c32998fc52f5a707528e0bb34a5f5a3c758460c06a680106d7f8b15d509",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_096_242p0240.dat",
          "sha256": "a809c348dc88901c28d6a2bba6675fdcd92759739b52287aef810827d9350872",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_097_246p4910.dat",
          "sha256": "1475795b475c580b6bebef7a47b544c125adb53e056c5e0234cc04943212fdda",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_098_250p8860.dat",
          "sha256": "5f1d25db589640730d6dfb7c267af35b6c0d108e30e927467c780335b65b711c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_099_255p4710.dat",
          "sha256": "9b7bee4d7bce1b21a6c949784dcc77cbe1c4f68dac20b6e1f5403d7e416892ff",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_100_259p8830.dat",
          "sha256": "7d831ef5c563487fead89e89d0b2f663265a34c8d8d1ca8615f7147fa88926d9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_101_264p2270.dat",
          "sha256": "cac5e46d43612d7f3e44829e0b83606258443922c94ab58cf5f5da9767e1eef3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_102_268p6170.dat",
          "sha256": "56ae5f39aff745c323b4143c019c828b649dd24cb38b6dd995710f747cdea63b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_103_273p0910.dat",
          "sha256": "6e6045caf495e42b716d4a14b0544ae4465e7f61b9db4200b8740f2137c33043",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_104_277p4860.dat",
          "sha256": "7283650bc9654d294ddb40e2e97f293f9be346e04dc3b01ab80def0c379ddba1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_105_281p9010.dat",
          "sha256": "243f7d2144ece905f6de4f72acbff36fad21f42706937370f63b21afdd3ba325",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_106_286p2140.dat",
          "sha256": "90525f159ad2e7b5dba17ba5e5a817b03e81b9bb850373e34de26fc30e00bd8d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_107_290p7210.dat",
          "sha256": "940bcd89b8fe5ac1ac574ac558dcc921e82ea8b40238c76209b0bc786ad22eee",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_108_296p4040.dat",
          "sha256": "acf75bbc5a6a1e60f2fec3d8e7d6101374ee8528af85817d84a816c2681eca6a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_109_298p0250.dat",
          "sha256": "eb716b2eecde0c12d3329a5651ab8d3945e07d0929a802c164b15868861dd689",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_110_298p8330.dat",
          "sha256": "841b483ddd09b3c2e767db9bb9890c5ac2d1d3a937b51da72f3bc18871e3e79b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_111_299p2050.dat",
          "sha256": "4565452f1baca8f389bcf7d8e47faef032fc945105c95923f74ddd4b6709c410",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_112_299p3940.dat",
          "sha256": "dd2bf75b4d8e3ae22bf9643d3be77773d3b5317b6ab8a273b802bb3640059874",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_113_300p4240.dat",
          "sha256": "92e8342610fa5d0f5a749a9b4dc29479c3ac75b052db2c9a2393155bf354b28c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_114_303p0940.dat",
          "sha256": "70240b3346e701baaa43629897aeb121f54cd19aff707eabe45d2524844ca664",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_115_306p6800.dat",
          "sha256": "29e6848c38f889e1bc839bac949c3b2404abe2f9a652a604fc4542fe55d52dc3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_116_310p9350.dat",
          "sha256": "fec1490aaf6f59a7464c3b21cdedf6333cb3d764f8d9a13ac62478cb2d981afa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_117_314p8200.dat",
          "sha256": "08d4bf74090bd142686ba02fe36c6642f4117480d0f9026b3e3a307ca64b6ed8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_118_319p0710.dat",
          "sha256": "5c2058a222ef253a0f46235b9615cf957e6414b4e52f4138dfb64be5fd173af4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_119_323p3350.dat",
          "sha256": "c038f2e38226ad3fd2281b55fbb39cf04a6ef2dc3d4f0276b5c8bf0ba393024f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_120_327p9190.dat",
          "sha256": "f8dbe59316ee34514cf8ddd5502b5b53609276ce3117e05d87ac7ac9afd97aec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_121_332p2660.dat",
          "sha256": "03fe53d66954d3935bbbca3c39dda6ec625c1f5627c6eb6d89e94d0364ade80e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_122_336p6280.dat",
          "sha256": "10d3cb20af02ac533a17e0966dd41f3fb80f80bfdc5e2763d4e92b08485640f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_123_340p7230.dat",
          "sha256": "7855c5f97795bcb99310acd974b65fc6aad8a5d157f41aec9bdf2802533414ac",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_124_345p2570.dat",
          "sha256": "5f1b51a111b63db9d3154dd6fa9e2dfc1c18cdaccfcd38a0f6cc97dae5e79615",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_125_349p8060.dat",
          "sha256": "206f085b19fa066d2b473479221c460287a40f19f5e7c1f0320c2979c8ffe32a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_126_354p1160.dat",
          "sha256": "0e6a05e598dadc199dd04823bed2db908f96e104cbb5359fc824893a657adc1f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_127_358p4140.dat",
          "sha256": "1006fc6e31bbd16528ac73eccd0e115148bcdfb75b397df5a11a5849d96131bc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_128_362p8190.dat",
          "sha256": "424bea57f499991eb8aa7d224373a6bd73d0107c0977c06f0db15ed1eaab8ccc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_129_371p4350.dat",
          "sha256": "76e2fd2646d8c37d1d357e4479b20e29a47c41ee357614f7d947a8c1fcbb7ce3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_130_375p8110.dat",
          "sha256": "a56ff8f5849e1e3fe67b6858352fcc88c24a53cfe579df98e97d48c2e2d9f055",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_131_380p2820.dat",
          "sha256": "e03e997f68637b4df7b60513c7845a260b01726f3f67fa804b355a71b94de8f5",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_132_384p6000.dat",
          "sha256": "c051142ae04c23efe2323ca6ffbbdf39ee6571371d26dcc00c1cf592ff97ee55",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_133_388p8760.dat",
          "sha256": "2fe4da899cfec93b4685f5ddf48cb98f639901dc2239bced310739522ed301ba",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_134_393p2660.dat",
          "sha256": "6ebb10a745535d973fbaa3aa16bcf57f163ad99d67cedb123f6739cc0d19989a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_135_397p5640.dat",
          "sha256": "450d09ba353d52cf88805f153913f308ec51428aa279649911a5297dd4106f25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_136_402p1390.dat",
          "sha256": "a68b8fae71666b66d6139375978379ab63ce7facb1f4c63a343262c47e81270b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_137_406p1830.dat",
          "sha256": "7fa18447b1981382d68d30c896b87af509f6bba264bc1013af1650cb5b34383e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_138_410p7830.dat",
          "sha256": "d0e151a4805a8c29be88b33249f11e1f5414e9de25dffde20869b202cdeb72ec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_139_415p1880.dat",
          "sha256": "7a9fdd55cf98f32e0ec00e042999c4555b5c818c9429d6daf41fc7a166bac478",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_140_419p4530.dat",
          "sha256": "33611d2a5959694b1dbe9d228db99613afe5431bc35a43e61764267a73be83d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_141_424p1020.dat",
          "sha256": "458d5d83a455d35efe65f3a9a518cf0b66d677b280be587868a6cb9e7af2db38",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_142_428p4870.dat",
          "sha256": "b80cc00f57695d56589aa857d1c72fd921acc2ec2c45adecc4d2901e49e3bff4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_143_433p0150.dat",
          "sha256": "a3d5a690e7a7b31263035b240181507e751f6b7f0ba35b77c29cd82d6bb535fd",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_144_437p1320.dat",
          "sha256": "f6418e949ff522365390f777c197ab7fbd9d76cded8c04d7d4a509a51e8b877b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_145_441p4020.dat",
          "sha256": "aca3572c999b8cf60592ea7b884f67ecc8a90664361f4e6aa15590b6ef8ea6e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_146_446p0030.dat",
          "sha256": "89c898df19634d5672e76798c37bc9e8551bb5678767e988bc41d735173483e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_147_450p3320.dat",
          "sha256": "6e363f78be7d54a57830bca46b5bd0a18f768f6b15dd8a68ed6c1d292216fb03",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_148_454p8870.dat",
          "sha256": "48231f25702a2c8e550c09f6272b5305549297e7647b59b7a3d8d6b28810b1a4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_149_459p2510.dat",
          "sha256": "dd07ea491ebb2a9fd37a9b0a6204e82367ea4a1954315778ceb2fe585d93bbd4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_150_463p8850.dat",
          "sha256": "d5c22e9a92bfaf425cd6ab3633325319d7a62db6e65d3916e97447c6422fd30c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_151_468p2800.dat",
          "sha256": "f78b5d3d9da83a3f003535847f2610e52e7dfd8374ee5950a0c3c34109f56462",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_152_472p5840.dat",
          "sha256": "acd16e373fdfe9e3cc5c597be55ec304109578badf82df8743d69f07a58ca9c0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_153_476p9800.dat",
          "sha256": "1dc012ecb202cb10c04d5a70be15c2a9734c2b37d547f564ecee9d2c9abedefa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_154_481p2260.dat",
          "sha256": "021d76aad5f57879aefa516eefc96418536d0f42af793e6a0d47d6f407e05005",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_155_485p7350.dat",
          "sha256": "de3f00765f6765b80157d75947c7517e997dfea579adcc76251fe644a9a7ba70",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_156_489p9560.dat",
          "sha256": "2898a2b6434c15f02eff1c1994fa8c896c6d92b93d15a15994854e75be060aef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_157_495p3740.dat",
          "sha256": "f2025c68fdd8fc3de28b057382d9087ea6c0b92dbec0c1b9eca54dc0ef41f2d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_158_496p5900.dat",
          "sha256": "5f3023b3820eb243fe8186c8f9ff953e1325c0d767097174f77e94419f1d8094",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_159_497p0360.dat",
          "sha256": "943ff86fb9bf5d264f4a2d41e64b1d5711f26ab76de4cb90c0545900e92c674e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_160_497p2280.dat",
          "sha256": "12df6cee20e6241e84a392053ef1ad6cb9cc153d96ddbd95b025ba79f4c22734",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_161_497p3410.dat",
          "sha256": "ef3eaf0029ac15202d49952f66caf1d30a8d4ca3adf82e76f3a89ef4a843728d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "02_162_497p3790.dat",
          "sha256": "22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4024.358,
                31.828
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                442.251,
                10.252
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        }
      ],
      "loaderWarning": "",
      "files": {
        "project.edi": "313e0481b2d7f3e0ebfd805cb6b1433c66c4ed26fb72595abefedb8646a911a2",
        "structures/cosio.edi": "4538c66b979d5783c2c3b5ba8c06494a54efeea3fc83c5488e89d5a10c0bb899",
        "experiments/d20.edi": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
        "analysis/analysis.edi": "0d463ba37e85baf7de2e4c08ac0d596a3756a50edea40b993b3120a9ae0209c6"
      }
    },
    {
      "id": "pd-neut-cwl_lbco-hrpt_start-2",
      "path": "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "lbco_hrpt_s2",
        "_metadata.title": "La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI",
        "_metadata.description": "Cubic perovskite · Preferred orientation · Starting model 2",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "HRPT",
        "_metadata.facility": "PSI",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lbco",
          "atoms": 4,
          "cellA": 3.88,
          "spaceGroup": "P m -3 m",
          "cell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "hrpt"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "7402a40811051477f1f62fbf1506ec553ca8240d23845db54fc64b52bf3b4f08",
        "structures/lbco.edi": "1c8421e95c44cad8dce012f78e57ed2bcabd783c76443eddf0d5d16873cba5c3",
        "experiments/hrpt.edi": "cfe9ea2b020d8ac9b8b61a7affb253787d6a8a27be10462c396091f6e96baf7e",
        "analysis/analysis.edi": "06acc049b2fdfd16e06af5c03634f364d62a2819d2bb2b0ea456cd4b79ba5061"
      }
    },
    {
      "id": "pd-neut-cwl_lbco-hrpt_start-4",
      "path": "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "lbco_hrpt_s4",
        "_metadata.title": "La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI",
        "_metadata.description": "Cubic perovskite structure and profile refinement · Starting model 4",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "HRPT",
        "_metadata.facility": "PSI",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lbco",
          "atoms": 4,
          "cellA": 3.88,
          "spaceGroup": "P m -3 m",
          "cell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "hrpt"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "b47088ce8a1198fba99f4cca2fdee1b317230e0c66fbdc2602273344bdbab721",
        "structures/lbco.edi": "1c8421e95c44cad8dce012f78e57ed2bcabd783c76443eddf0d5d16873cba5c3",
        "experiments/hrpt.edi": "c7a093e4cdee2aeca6553b84cca81293b748caeb6270d2083b5a043724128c26",
        "analysis/analysis.edi": "06acc049b2fdfd16e06af5c03634f364d62a2819d2bb2b0ea456cd4b79ba5061"
      }
    },
    {
      "id": "pd-neut-tof_ncaf-wish-2bank_start-3",
      "path": "docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "ncaf_wish_2bank_s3",
        "_metadata.title": "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS",
        "_metadata.description": "2 banks · Shared atomic displacement · Jorgensen profile · Starting model 3",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "WISH",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ncaf",
          "atoms": 6,
          "cellA": 10.250256,
          "spaceGroup": "I 21 3",
          "cell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "wish_4_7",
        "wish_5_6"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "06de1407f4dfeb5784c0dbcb5078f3f3bb54782d9cf2c0a7af35937726e8af85",
        "structures/ncaf.edi": "f61f4922cf075908b47b4fd3b14c32f7aefef8e339d6161a5fece184396f865b",
        "experiments/wish_4_7.edi": "053751e9274de8a61c12fe3b8b0d96dca3f88ff0748db36ecd0ab88466e4d841",
        "experiments/wish_5_6.edi": "d08b3b01b671bf5d362da48a3e73442ed91b5f52a69d9ca5955091779c58796e",
        "analysis/analysis.edi": "362967ebcac29cd81a538ba27f01b70d61eb04bfcbf8d2de0ba4e13bb271e428"
      }
    },
    {
      "id": "pd-neut-tof_ncaf-wish-3bank_start-5",
      "path": "docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "ncaf_wish_3bank_s5",
        "_metadata.title": "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS",
        "_metadata.description": "3 banks · Structure and profile refinement · Jorgensen–Von Dreele · Starting model 5",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "WISH",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint"
      },
      "structures": [
        {
          "name": "ncaf",
          "atoms": 6,
          "cellA": 10.250256,
          "spaceGroup": "I 21 3",
          "cell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "wish_2_9",
        "wish_4_7",
        "wish_5_6"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "c898a54766c3cc7caa5b0db874b896ca507b893b918e4b83fd4c1413167e2540",
        "structures/ncaf.edi": "1f231ef2dc1ec210d95b9f52452dacb6102b7c515b6af603f205199a3aaf0e1d",
        "experiments/wish_2_9.edi": "761e2bed99259c0c0e679bdbfa5455671422ea953774f5450ba3edff6bd2200b",
        "experiments/wish_4_7.edi": "e63425979da16bed1c0cb0061700d1855a5847fb48e5ce0477bf293284cf204e",
        "experiments/wish_5_6.edi": "bb48d4b9c197737a2d35ef406dd3257bbe20dde70a6907bec5d14c8fd2e591a1",
        "analysis/analysis.edi": "bc78689c1a4491d308a0611490dceed83edb4898244ae092ec555ee91a548484"
      }
    },
    {
      "id": "pd-neut-tof_ncaf-wish-5bank_start-5",
      "path": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "ncaf_wish_5bank_s5",
        "_metadata.title": "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS",
        "_metadata.description": "5 banks · FullProf free parameters and exclusions · Starting model 5",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "WISH",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ncaf",
          "atoms": 6,
          "cellA": 10.250256,
          "spaceGroup": "I 21 3",
          "cell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "wish_1_10",
        "wish_2_9",
        "wish_3_8",
        "wish_4_7",
        "wish_5_6"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "3f486373dd1d409fbf5f1da64303b34f1ce46a1d77ea87eecf7a1637facbcf09",
        "structures/ncaf.edi": "1f231ef2dc1ec210d95b9f52452dacb6102b7c515b6af603f205199a3aaf0e1d",
        "experiments/wish_1_10.edi": "6893edefb924126beb3817b349dc4f263ff11308172d7cfff70dd9b003b6b67c",
        "experiments/wish_2_9.edi": "cf1953881302612f1dd7f659ac76026c2f75dfd929f6a846b7c0c822328eef19",
        "experiments/wish_3_8.edi": "58437073a03edf8861f09c22d0ddc85637268b35e189f76dc430b62068af0bfa",
        "experiments/wish_4_7.edi": "5642c0c37de594406461d2b66ef20d09c46e4cd3af26d1f92e4615714179a6ae",
        "experiments/wish_5_6.edi": "555792faa1e574fad3b12a810b6aa7dc67abad14977453c97d65a9d0b8826b3b",
        "analysis/analysis.edi": "39fbca0c5cfba66ab4e126f6070c173209bdec5b984a7462a84e702363e3570f"
      }
    },
    {
      "id": "pd-neut-tof_ncaf-wish-5bank_start-fullprof",
      "path": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "ncaf_wish_5bank_fullprof",
        "_metadata.title": "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS",
        "_metadata.description": "5 banks · Structure and profile refinement from FullProf’s minimum",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "WISH",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ncaf",
          "atoms": 6,
          "cellA": 10.250256,
          "spaceGroup": "I 21 3",
          "cell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "wish_1_10",
        "wish_2_9",
        "wish_3_8",
        "wish_4_7",
        "wish_5_6"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "21f6cc048a9dc4bcc486402c1bb1342d1be1cd95e643b6b34ab6357c991d437c",
        "structures/ncaf.edi": "44fe96e2d76e9a75815b831c6d060773e6129c8589aa5da5cd7e5b9e6b853eee",
        "experiments/wish_1_10.edi": "1daf13e94e0fde89c44822d226109b527c2bde097c33b8f20465d6e83ba7b1d5",
        "experiments/wish_2_9.edi": "7258aadc1cef7d305d237f7c5e031ee27251f0756159b61ad726cb24bfed435b",
        "experiments/wish_3_8.edi": "947f6b21e94bdfcf541ef46896b7fed26b91512da0c54084b429b75e24dbc05c",
        "experiments/wish_4_7.edi": "a0afd8a05804802f03de14361fb212c63a3549e61c6e32895fd83ee534312843",
        "experiments/wish_5_6.edi": "bf45ed7b5f511d26c9d49adf0b13224a87d06245504d377dd5cfe4d4ffadaeb7",
        "analysis/analysis.edi": "39fbca0c5cfba66ab4e126f6070c173209bdec5b984a7462a84e702363e3570f"
      }
    },
    {
      "id": "pd-neut-tof_si-sepd_start-2",
      "path": "docs/user/cli/pd-neut-tof_si-sepd_start-2/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "si_sepd_s2",
        "_metadata.title": "Silicon [Fd-3m] · SEPD @ Argonne",
        "_metadata.description": "Silicon standard · Jorgensen–Von Dreele profile · Starting model 2",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SEPD",
        "_metadata.facility": "Argonne",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "si",
          "atoms": 1,
          "cellA": 5.431,
          "spaceGroup": "F d -3 m",
          "cell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "sepd"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "ac3f1d57a3bb4e2643cf402533d76d9c6927b5bcb490b39d0e58419b6210a51f",
        "structures/si.edi": "531d657005b89223d20b18265ace558c8fba96473890fb91a86e77dd80ca8f94",
        "experiments/sepd.edi": "0b1167d3ccd41b2da642e443d5beb606932eea98580cd08364e21e51a4350152",
        "analysis/analysis.edi": "9f58295877950335b95efa1716755b1247203d5be0475d9520960a0584d2b17f"
      }
    },
    {
      "id": "pd-neut-tof_si-sepd_start-5",
      "path": "docs/user/cli/pd-neut-tof_si-sepd_start-5/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "si_sepd_s5",
        "_metadata.title": "Silicon [Fd-3m] · SEPD @ Argonne",
        "_metadata.description": "Silicon standard · Jorgensen–Von Dreele profile · Starting model 5",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SEPD",
        "_metadata.facility": "Argonne",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "si",
          "atoms": 1,
          "cellA": 5.431,
          "spaceGroup": "F d -3 m",
          "cell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "sepd"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "d977fa9bc32f98700add27b6ca71de2149fb320530e9ae8fc7c22815c2b6e96f",
        "structures/si.edi": "531d657005b89223d20b18265ace558c8fba96473890fb91a86e77dd80ca8f94",
        "experiments/sepd.edi": "4e49721b5e31d508798e5ad56db99fa37ba83bfd324df051776713402deeffc0",
        "analysis/analysis.edi": "9f58295877950335b95efa1716755b1247203d5be0475d9520960a0584d2b17f"
      }
    },
    {
      "id": "pd-neut-tof_diamond-dream_basic",
      "path": "docs/user/cli/pd-neut-tof_diamond-dream_basic/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_tof_diamond_dream",
        "_metadata.created": "24 Sep 2026 18:42:48",
        "_metadata.last_modified": "24 Sep 2026 18:42:49",
        "_metadata.timestamp": "?",
        "_metadata.title": "Diamond [Fd-3m] · DREAM @ ESS",
        "_metadata.description": "McStas-simulated 90° bank · Jorgensen profile · Scale-only refinement",
        "_metadata.purpose": "verification",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "DREAM",
        "_metadata.facility": "ESS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "diamond",
          "atoms": 1,
          "cellA": 3.567,
          "spaceGroup": "F d -3 m",
          "cell": [
            3.567,
            3.567,
            3.567,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "dream"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "f98e3df911acb3c08111ad6d035bc36eb7a569ba9e3d6f702da04d45a12e0bef",
        "structures/diamond.edi": "57650796c81a5963ee142a26847f89d9dac23cb6bc018406c77c6141a68f2613",
        "experiments/dream.edi": "82cab19d185fb4bf3a4706995e43af5b6b60a365d1db808fda958bdaaafba249",
        "analysis/analysis.edi": "c859cfebc586252e3b1572cd54f854592d55a143b97302621120483df4733340"
      }
    },
    {
      "id": "pd-neut-cwl_lab6-echidna_fcj-asymmetry",
      "path": "docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_lab6_echidna_fcj",
        "_metadata.created": "26 Sep 2026 10:29:37",
        "_metadata.last_modified": "26 Sep 2026 10:29:38",
        "_metadata.timestamp": "?",
        "_metadata.title": "LaB₆ [Pm-3m] · ECHIDNA @ ANSTO",
        "_metadata.description": "TCH pseudo-Voigt with FCJ axial divergence · Scale-only refinement",
        "_metadata.purpose": "verification",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "ECHIDNA",
        "_metadata.facility": "ANSTO",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "lab6",
          "atoms": 2,
          "cellA": 4.156885,
          "spaceGroup": "P m -3 m",
          "cell": [
            4.156885,
            4.156885,
            4.156885,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "echidna"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "a9e92b9e43d8021cec4b797480c3077e418c57b1ddf2acc05c26bb88e5b09d02",
        "structures/lab6.edi": "ae52d392119f81a94e77ba4128ee2afc447fbcd3bdd9cdc6e2fea56eba54074d",
        "experiments/echidna.edi": "80f077806e554470a5b4943991e795c465db78266fc072a6c07f9390e8117d6b",
        "analysis/analysis.edi": "622953d9f61a1927cfdde76b6296bf57805006e83817b80cd36f851b35d8ef79"
      }
    },
    {
      "id": "pd-neut-cwl_pbso4_beba-asymmetry",
      "path": "docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_pbso4_beba",
        "_metadata.created": "26 Sep 2026 10:28:28",
        "_metadata.last_modified": "26 Sep 2026 10:28:29",
        "_metadata.timestamp": "?",
        "_metadata.title": "PbSO₄ [Pnma] · D1A @ ILL",
        "_metadata.description": "Rietveld round-robin data · Bérar-Baldinozzi asymmetry refinement",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D1A",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "pbso4",
          "atoms": 5,
          "cellA": 8.479506,
          "spaceGroup": "P n m a",
          "cell": [
            8.479506,
            5.397256,
            6.958973,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d1a"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "91943d913a9800c06acbcb7bd3c2a8782996fddff8acbded15f2ab01d6b55a09",
        "structures/pbso4.edi": "d14b19ea6dc7f6f3a129fa5fb3538f7413fc3cb727950c2f70fb9e2e6e3f2520",
        "experiments/d1a.edi": "f494c2665e6d1a9986165650e677af2214e5fa63a797ce3ad15e8599064ce2e2",
        "analysis/analysis.edi": "494db6eaa33dd5b4e18e6fc2d28282486b2d9bfc50a8e52098e6ad34422062fd"
      }
    },
    {
      "id": "pd-neut-cwl_yap-spodi_3k",
      "path": "docs/user/cli/pd-neut-cwl_yap-spodi_3k/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_yap_spodi_3k",
        "_metadata.title": "YAlO₃ [Pbnm] / Al₂O₃ [R-3c] · SPODI @ FRM II",
        "_metadata.description": "2 phases at 3 K · Shared Bérar-Baldinozzi profile · Cylinder absorption",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SPODI",
        "_metadata.facility": "FRM II",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.max_iterations": {
          "value": 150.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 1e-08,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "Al2O3",
          "atoms": 2,
          "cellA": 4.756614,
          "spaceGroup": "R -3 c",
          "cell": [
            4.756614,
            4.756614,
            12.973036,
            90.0,
            90.0,
            120.0
          ]
        },
        {
          "name": "YAlO3",
          "atoms": 4,
          "cellA": 5.172418,
          "spaceGroup": "P b n m",
          "cell": [
            5.172418,
            5.32659,
            7.360847,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "spodi"
      ],
      "datasets": [],
      "loaderWarning": "Warning: structures[Al2O3].atom_sites[Al1].adp_iso = -0.13591 is outside its admissible range [0, 10]; loaded as saved (a fit may leave a value there)",
      "files": {
        "project.edi": "654e819625fe2f4f8681a3b6e9e96350a9ad2ef1d3d30bd94f43eab38a32b40e",
        "structures/Al2O3.edi": "f5d727bf0362dae6abfb4c2503669e83085bc897cbb09db913b359eb37999472",
        "structures/YAlO3.edi": "7a4c6c27b6314bca5d179350c2ee75e1e27565a6c59629c17ed11662e29a2ccb",
        "experiments/spodi.edi": "524a651bf9680b706da031ee998f1f8be52d6c1e2bf9038124ee89a5d3890279",
        "analysis/analysis.edi": "8cae35fd43bf1ae284f382fb2156e824f67d8a4ee2bd5ad0e47a5ae21785506f"
      }
    },
    {
      "id": "pd-xray-cwl_latp_scan-4f",
      "path": "docs/user/cli/pd-xray-cwl_latp_scan-4f/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-xray-cwl_latp_scan-4f",
        "_metadata.title": "LATP [R-3c] / AlPO₄ [C222₁] / AlPO₄ [P6₃mc] · BM01 @ SNBL",
        "_metadata.description": "3 phases · 4 of the 73 synchrotron patterns · Linked displacement parameters",
        "_metadata.authors": ".",
        "_metadata.created": "22 Oct 2026 09:50:09",
        "_metadata.last_modified": "22 Oct 2026 14:01:42",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "BM01",
        "_metadata.facility": "SNBL",
        "_su_format.rule": "iucr_19"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_sequential_fit.data_dir": "experiments/bm01_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "true",
        "_sequential_fit.template_file": "latp_312.dat"
      },
      "structures": [
        {
          "name": "alpo4_c2221",
          "atoms": 4,
          "cellA": 6.97,
          "displayCell": [
            6.97,
            7.11,
            7.004,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "C 2 2 21",
          "cell": [
            6.97,
            7.11,
            7.004,
            90.0,
            90.0,
            90.0
          ]
        },
        {
          "name": "alpo4_p63mc",
          "atoms": 4,
          "cellA": 4.983,
          "displayCell": [
            4.983,
            4.983,
            9.504,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "P 63 m c",
          "cell": [
            4.983,
            4.9832407377064385,
            9.504,
            90.0,
            90.0,
            120.0
          ]
        },
        {
          "name": "latp",
          "atoms": 7,
          "cellA": 8.4953,
          "displayCell": [
            8.4953,
            8.4953,
            20.8268,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "R -3 c",
          "cell": [
            8.4953,
            8.495251128959499,
            20.8268,
            90.0,
            90.0,
            120.0
          ]
        }
      ],
      "experiments": [
        "bm01"
      ],
      "datasets": [
        {
          "file": "latp_312.dat",
          "sha256": "cd3dc944fa035058af4caba8773f4247c955d5e5c29bfaef1504d70aacc05794",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                34562780.0,
                24701.53
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                28934400.0,
                145.9334
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                23445790.0,
                1155.716
              ]
            }
          ]
        },
        {
          "file": "latp_304.dat",
          "sha256": "bb777343b334e2317c0d74f085ba70552da2eb813a11a19b06383b360ded02f2",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_296.dat",
          "sha256": "66a5f34554e79943f4b056cfa67f4af48c0c962f3509f2f2693c3a46b9acba9e",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                29201310.0,
                22704.96
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                28881430.0,
                145.7981
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                33817660.0,
                1387.837
              ]
            }
          ]
        },
        {
          "file": "latp_288.dat",
          "sha256": "1fe408408d40d238d013afd8138646143fdb8bd76be7ad9891cfd8e3c7b83ecd",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                34696870.0,
                24749.4
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                28593710.0,
                145.0687
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                22176300.0,
                1123.975
              ]
            }
          ]
        }
      ],
      "loaderWarning": "",
      "files": {
        "project.edi": "4402d50f2799ef9c8371d0551cae4731ab16d8ae566e05fbecc33c7c820a429c",
        "structures/alpo4_c2221.edi": "b42662d5570b1a08f3b1df6451af8ff1f5c6e69ea3b40bd78f39dd2b181c5306",
        "structures/alpo4_p63mc.edi": "350e4eb631946104099c05296a072d96fd63ed5a28e13ada6e081bfd77610d5e",
        "structures/latp.edi": "2fa22f4a9a8554731d4abc98d471cb0a81a9b9a39eec390b7219a72d4d1ad3a9",
        "experiments/bm01.edi": "b25970da46d7829c717432de06c7d1a7e9f8f914a0b1bfce54d99cfa39809bf3",
        "analysis/analysis.edi": "54e3863bd8ff2eda1080f5784b54d828a2bb6050903a9c9d86b2421f1f8deba3"
      }
    },
    {
      "id": "pd-neut-tof_fe_pseudo-voigt",
      "path": "docs/user/cli/pd-neut-tof_fe_pseudo-voigt/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_tof_fe_pseudo_voigt",
        "_metadata.created": "26 Sep 2026 10:28:28",
        "_metadata.last_modified": "26 Sep 2026 10:28:29",
        "_metadata.timestamp": "?",
        "_rendering_plot.type": "plotly",
        "_metadata.title": "Iron [Im-3m] · BEER @ ESS",
        "_metadata.description": "90° bank · Non-convoluted pseudo-Voigt · Scale-only refinement",
        "_metadata.purpose": "verification",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "BEER",
        "_metadata.facility": "ESS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "bumps (lm)"
      },
      "structures": [
        {
          "name": "fe",
          "atoms": 1,
          "cellA": 2.886,
          "spaceGroup": "I m -3 m",
          "cell": [
            2.886,
            2.886,
            2.886,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "beer"
      ],
      "datasets": [],
      "loaderWarning": "Warning: unsupported _calculator.type \"cryspy\" - using crysta\nWarning: unsupported _minimizer.type \"bumps (lm)\" - using crysta\nWarning: unsupported _rendering_plot.type \"plotly\" - using auto",
      "files": {
        "project.edi": "95296a0d13ebb570f256c228a5e1663c886b5eb53fafe60534ab39c891a78735",
        "structures/fe.edi": "9ee23e6fff7c5eb544677380a5c3176ee7425e3e790cbe7b50dca77472a16c29",
        "experiments/beer.edi": "830696bd336668d52a2d0358fae8748d7447a2e01fb21df34953a4475ab0607f",
        "analysis/analysis.edi": "7936851a579a0171a425595f5090909d327362a0da203615725f2f2ceacbf642"
      }
    },
    {
      "id": "pd-neut-tof_cecoal-polaris_chebyshev",
      "path": "docs/user/cli/pd-neut-tof_cecoal-polaris_chebyshev/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_tof_cecoal_polaris_chebyshev",
        "_metadata.title": "CeCoAl₃ [Pmma] · POLARIS @ ISIS",
        "_metadata.description": "Structure and TOF profile refinement · 24-term Chebyshev background",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "POLARIS",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "cecoal",
          "atoms": 5,
          "cellA": 7.65038,
          "spaceGroup": "P m m a",
          "cell": [
            7.65038,
            4.051332,
            6.90536,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "polaris"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "b96f7a0f77fc7266fb1bbd4782508a55e43aee425378168ab9e269109973a8bd",
        "structures/cecoal.edi": "f6939b1d7fe11a4b7e8451ec9a4acb468c21522ef4a29af3995b86758e910616",
        "experiments/polaris.edi": "940231cb84abc21ad60fe760c793b603e8acbb6cb20478d94dfe858d250c33c0",
        "analysis/analysis.edi": "603772c6d4c286e53eb8554e6d2be4843c8f560cb942fec808bb8ca138eb993f"
      }
    },
    {
      "id": "pd-neut-tof_ceo2-pearl_polynomial",
      "path": "docs/user/cli/pd-neut-tof_ceo2-pearl_polynomial/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_tof_ceo2_pearl_polynomial",
        "_metadata.title": "CeO₂ [Fm-3m] · PEARL @ ISIS",
        "_metadata.description": "NBS SRM 674a standard · TOF profile refinement · 6-term polynomial background",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "PEARL",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ceo2",
          "atoms": 2,
          "cellA": 5.410495,
          "spaceGroup": "F m -3 m",
          "cell": [
            5.410495,
            5.410495,
            5.410495,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "pearl"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "44d95712746310b2fe328c448521383ad2f270062175750f985a61d63bc4f3e8",
        "structures/ceo2.edi": "aedac6b487103b77e50f106e073b5701214efed16a787a9832391ce2c3b4b79c",
        "experiments/pearl.edi": "dd405b91a0eea1bcc0c82d7763a7ae7ad2987b94169b9bb4e50454a140c57efd",
        "analysis/analysis.edi": "603772c6d4c286e53eb8554e6d2be4843c8f560cb942fec808bb8ca138eb993f"
      }
    },
    {
      "id": "pd-neut-cwl_lab6-11b-echidna_tch-fcj",
      "path": "docs/user/cli/pd-neut-cwl_lab6-11b-echidna_tch-fcj/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_lab6_11b_echidna_tch_fcj",
        "_metadata.title": "LaB₆ [Pm-3m] · ECHIDNA @ ANSTO",
        "_metadata.description": "¹¹B-enriched standard · TCH × FCJ · Absorption and polynomial background",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "ECHIDNA",
        "_metadata.facility": "ANSTO",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lab6",
          "atoms": 2,
          "cellA": 4.156885,
          "spaceGroup": "P m -3 m",
          "cell": [
            4.156885,
            4.156885,
            4.156885,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "echidna"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "80af9044b177f3f28acd9d19322a1694b73375080dfab72f2c870925a6e782aa",
        "structures/lab6.edi": "06d8ee9eadd4dd9c5f72aed4f264446172a15f81a0571e4a02adfba6156a53fd",
        "experiments/echidna.edi": "a51359be4b97bed9f488f4022c9efaba6267d954a8ca110c2ed39deb5b9c5eb6",
        "analysis/analysis.edi": "603772c6d4c286e53eb8554e6d2be4843c8f560cb942fec808bb8ca138eb993f"
      }
    },
    {
      "id": "pd-xray-cwl_lif_single",
      "path": "docs/user/cli/pd-xray-cwl_lif_single/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_xray_cwl_lif_single",
        "_metadata.title": "LiF [Fm-3m] · Calculated reference",
        "_metadata.description": "Cu Kα doublet FullProf reference · Doublet ratio and absorption refinement",
        "_metadata.created": "02 Oct 2026 14:28:55",
        "_metadata.last_modified": "02 Oct 2026 14:28:56",
        "_metadata.timestamp": "?",
        "_metadata.purpose": "verification",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "?",
        "_metadata.facility": "?"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "lif",
          "atoms": 2,
          "cellA": 4.0267,
          "spaceGroup": "F m -3 m",
          "cell": [
            4.0267,
            4.0267,
            4.0267,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "cu_ka"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "889a03d5f93dd1b479515d59b53eec51e417433901ce122fb805c8d056db7bab",
        "structures/lif.edi": "b68e864053c85ea3bb0e7a14b37131c7319cd2cd047b89d4dc4d8b30ff4033fe",
        "experiments/cu_ka.edi": "5b084a1364f4fbe8afc90fa44dc785eb0b674ad2954d8e66dce50e7a0194f9ad",
        "analysis/analysis.edi": "76917b3672c7268e7fee9fb901c0ed8ffdd5ffcf29c6fc1083d470ad5b501e72"
      }
    },
    {
      "id": "pd-neut-tof_ferrite-austenite-beer_joint",
      "path": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "beer_mcstas",
        "_metadata.title": "Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS",
        "_metadata.description": "2 iron phases · 2 McStas-simulated banks · Separate phase scales",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "BEER",
        "_metadata.facility": "ESS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.type": "lmfit (leastsq)",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 1e-08,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "austenite",
          "atoms": 1,
          "cellA": 3.6468,
          "spaceGroup": "F m -3 m",
          "cell": [
            3.6468,
            3.6468,
            3.6468,
            90.0,
            90.0,
            90.0
          ]
        },
        {
          "name": "ferrite",
          "atoms": 1,
          "cellA": 2.886,
          "spaceGroup": "I m -3 m",
          "cell": [
            2.886,
            2.886,
            2.886,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "expt_n2",
        "expt_s2"
      ],
      "datasets": [],
      "loaderWarning": "Warning: unsupported _calculator.type \"cryspy\" - using crysta\nWarning: unsupported _minimizer.type \"lmfit (leastsq)\" - using crysta",
      "files": {
        "project.edi": "649381af16dcc18e541345aa267e75b0115da8f806fce83345bc13548213470e",
        "structures/austenite.edi": "6b3eb1dab5b142687ed34263f04986ab3474bedfcaf9ce0d0ee7831f69929c93",
        "structures/ferrite.edi": "500fcf2007cefefb4b4477e10006596520d8e1cb8e61945d0791ff14ef27521c",
        "experiments/expt_n2.edi": "6e8f4ac836219d4ba503ff5583823b1d12eb523f788e16c03d86b2b5d2bacdda",
        "experiments/expt_s2.edi": "948b6f720ed6d72a5d5f0c5b8b06cae3dca6159f4f9e6edd56739110a2f2290a",
        "analysis/analysis.edi": "e228e179bbb95062d1646300ac68b92cbc0692d9b34a436ed944ef97cdd3df07"
      }
    },
    {
      "id": "pd-neut-cwl_y2o3_beta-adp",
      "path": "docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_y2o3_beta_adp",
        "_metadata.created": "06 Oct 2026 16:43:16",
        "_metadata.last_modified": "06 Oct 2026 16:43:17",
        "_metadata.timestamp": "?",
        "_metadata.title": "Y₂O₃ [Ia-3] · Unknown instrument",
        "_metadata.description": "Symmetry-constrained anisotropic β tensors · Scale-only refinement",
        "_metadata.purpose": "verification",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "?",
        "_metadata.facility": "?",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "y2o3",
          "atoms": 3,
          "cellA": 10.605744,
          "spaceGroup": "I a -3",
          "cell": [
            10.605744,
            10.605744,
            10.605744,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "y2o3"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "eb50aaa2bdec7eacb505b37b1a63bcd6066031d38008e2b14b1d1addcf688628",
        "structures/y2o3.edi": "dcacdbe2ddd6490b390aa7b4b36eeaf7e09d43b62f6b31b25a52121ffa295382",
        "experiments/y2o3.edi": "caa9b49442b995beef7b830e8709e1b62dfd015bc140fdf7a96c4719b62ed72d",
        "analysis/analysis.edi": "64a5254af5f390f3c3a49e84affc9bd4a6a074d2fe50ea5f97e5864c444c7f71"
      }
    },
    {
      "id": "pd-xray-cwl_pbso4-lab_round-robin",
      "path": "docs/user/cli/pd-xray-cwl_pbso4-lab_round-robin/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_xray_cwl_pbso4_lab_round_robin",
        "_metadata.title": "PbSO₄ [Pnma] · Laboratory X-ray",
        "_metadata.description": "Rietveld round-robin data · Kα doublet and Bérar-Baldinozzi asymmetry refinement",
        "_metadata.created": "13 Oct 2026 09:12:02",
        "_metadata.last_modified": "13 Oct 2026 09:12:03",
        "_metadata.timestamp": "?",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "?",
        "_metadata.facility": "?"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single"
      },
      "structures": [
        {
          "name": "pbso4",
          "atoms": 5,
          "cellA": 8.4859,
          "spaceGroup": "P n m a",
          "cell": [
            8.4859,
            5.402259,
            6.964587,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "pbsox"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "fa9e6fa39a75c1ab54504fea9930132d76ea1df515175ce9225a486eabe24c6b",
        "structures/pbso4.edi": "177c342c60fd3a0b087cb542e5aa7c31209fda745816cd21fd512fab0a780401",
        "experiments/pbsox.edi": "d627c625dad4ae24a482d344cf706c77a94c8cdcbaa531f45ee3acbc988603a9",
        "analysis/analysis.edi": "db6b3a6fb7b62313ff036e56efa6badd2f2d2953a0547ff5711048487cf799ab"
      }
    },
    {
      "id": "pd-neut-cwl_lab6-11b-echidna_basic",
      "path": "docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_cwl_lab6_11b_echidna_basic",
        "_metadata.title": "LaB₆ [Pm-3m] · ECHIDNA @ ANSTO",
        "_metadata.description": "¹¹B-enriched standard · TCH × FCJ · Wavelength and sample position from a standard",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "ECHIDNA",
        "_metadata.facility": "ANSTO",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lab6",
          "atoms": 2,
          "cellA": 4.156885,
          "spaceGroup": "P m -3 m",
          "cell": [
            4.156885,
            4.156885,
            4.156885,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "echidna"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "918045d0046e6067fb03ef03c7166467fe0fd4b9377ee06fb4a2980cd1845f54",
        "structures/lab6.edi": "e4882f46d2cbb6f4bf18d28865d16b09ec23f81db06775bd3f05aa1ef5671718",
        "experiments/echidna.edi": "f8fcbd4544ac9fca609567f985863f5fbe380c73c6968f417f54721b4089bde4",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-tof_diamond-dream_mcstas",
      "path": "docs/user/cli/pd-neut-tof_diamond-dream_mcstas/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd_neut_tof_diamond_dream_mcstas",
        "_metadata.title": "Diamond [Fd-3m] · DREAM @ ESS",
        "_metadata.description": "McStas-simulated 90° bank · Jorgensen profile · Structure and profile fit",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "DREAM",
        "_metadata.facility": "ESS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "diamond",
          "atoms": 1,
          "cellA": 3.57,
          "spaceGroup": "F d -3 m",
          "cell": [
            3.57,
            3.57,
            3.57,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "dream"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "fcf596965f487360c0f598acf5d9cfd5d58d6a572b6084207d01e1648b0390e0",
        "structures/diamond.edi": "82e667fcdfa28dc58d2222fe03df3b9bac6f15bf598ab6ffeb236cc0f7d21c86",
        "experiments/dream.edi": "ee3efe4adef810b92dbb8e2045d5af05258007e781b919ba1fd5f5822a3f00ea",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-cwl_lbco_simulation",
      "path": "docs/user/cli/pd-neut-cwl_lbco_simulation/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_lbco_simulation",
        "_metadata.title": "La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI",
        "_metadata.description": "Cubic perovskite · Simulated pattern without measured data",
        "_metadata.authors": ".",
        "_metadata.purpose": "simulation",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "HRPT",
        "_metadata.facility": "PSI",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta"
      },
      "structures": [
        {
          "name": "lbco",
          "atoms": 4,
          "cellA": 3.88,
          "displayCell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P m -3 m",
          "cell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "hrpt"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "c4a32320129dd599fa16240792760b0099a38556a917d73fc049b9e5bf9f4509",
        "structures/lbco.edi": "c4cd9712556b9d39513b186e86d5c87a04455111c0e34ca064875e36ba5eabff",
        "experiments/hrpt.edi": "21fadf02f63b79f1f18d78e8f0ca2af9cc017a8e429178853f7a8813a484072a",
        "analysis/analysis.edi": "1e59c0da22d1a5246a031013c7dc61ac906ee4aa6c1cc4c72b321be27c9480d3"
      }
    },
    {
      "id": "pd-neut-tof_si_simulation",
      "path": "docs/user/cli/pd-neut-tof_si_simulation/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_si_simulation",
        "_metadata.title": "Silicon [Fd-3m] · SEPD @ Argonne",
        "_metadata.description": "Silicon standard · Simulated time-of-flight pattern without measured data",
        "_metadata.authors": ".",
        "_metadata.purpose": "simulation",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SEPD",
        "_metadata.facility": "Argonne",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta"
      },
      "structures": [
        {
          "name": "si",
          "atoms": 1,
          "cellA": 5.431,
          "displayCell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F d -3 m",
          "cell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "sepd"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "e4e6788b1c5006848fd82e0f6e34a8afdad50dd53936b03fcf1b22dec3f7e150",
        "structures/si.edi": "1923e98e340ce5c3a6eb8f1febb921014d10df79310fab98574e8c0b6bd68bbd",
        "experiments/sepd.edi": "93449e1da42b2bdd244727e0d11234a906f950691f431e2e7b9e54323ba8a4f3",
        "analysis/analysis.edi": "1e59c0da22d1a5246a031013c7dc61ac906ee4aa6c1cc4c72b321be27c9480d3"
      }
    },
    {
      "id": "pd-xray-cwl_nacl_simulation",
      "path": "docs/user/cli/pd-xray-cwl_nacl_simulation/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-xray-cwl_nacl_simulation",
        "_metadata.title": "NaCl [Fm-3m] · Laboratory X-ray",
        "_metadata.description": "Rock salt · Simulated Cu Kα₁ pattern without measured data · Monochromator polarization",
        "_metadata.authors": ".",
        "_metadata.purpose": "simulation",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "?",
        "_metadata.facility": "?"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta"
      },
      "structures": [
        {
          "name": "nacl",
          "atoms": 2,
          "cellA": 5.62,
          "displayCell": [
            5.62,
            5.62,
            5.62,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F m -3 m",
          "cell": [
            5.62,
            5.62,
            5.62,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "lab"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "91fbf69d977176ba39c839a3f77859ff32d3eff2e1771c59b1d5be68235703de",
        "structures/nacl.edi": "b83321f0b2a722cd6f359baeb5b816bf7c6c42272f91352b0a8910baa13107ef",
        "experiments/lab.edi": "219e05053736474497f7a37b2a16f273feef817129aa860ee9289bba4fb9fe8e",
        "analysis/analysis.edi": "1e59c0da22d1a5246a031013c7dc61ac906ee4aa6c1cc4c72b321be27c9480d3"
      }
    },
    {
      "id": "pd-neut-cwl_lbco-hrpt",
      "path": "docs/user/cli/pd-neut-cwl_lbco-hrpt/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_lbco-hrpt",
        "_metadata.title": "La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI",
        "_metadata.description": "Cubic perovskite · La and Ba sharing one site · Profile, background, displacements",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "HRPT",
        "_metadata.facility": "PSI",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lbco",
          "atoms": 4,
          "cellA": 3.88,
          "displayCell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P m -3 m",
          "cell": [
            3.88,
            3.88,
            3.88,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "hrpt"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "55a1f672b1825145203ea9e39399e8cb3f9df106ac390a8b58258a03ba222aa2",
        "structures/lbco.edi": "d1c245e00052e5ba22a07a5f26d645d97bc4576e369599467bfc85af224bfb04",
        "experiments/hrpt.edi": "502941566652e6acfff532d1c9a4b5b73e7827a66d22d3fb8903078d2d310286",
        "analysis/analysis.edi": "a4d2395b2606f9ba4730de91f87aa0cb92167c5b5d0680c0a8d8bb32f5dd8959"
      }
    },
    {
      "id": "pd-neut-cwl_hs-hrpt",
      "path": "docs/user/cli/pd-neut-cwl_hs-hrpt/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_hs-hrpt",
        "_metadata.title": "ZnCu₃(OD)₆Cl₂ [R-3m] · HRPT @ PSI",
        "_metadata.description": "Herbertsmithite · Deuterated kagome antiferromagnet · Bérar-Baldinozzi asymmetry",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "HRPT",
        "_metadata.facility": "PSI",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "hs",
          "atoms": 5,
          "cellA": 6.85,
          "displayCell": [
            6.85,
            6.85,
            14.1,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "R -3 m",
          "cell": [
            6.85,
            6.85,
            14.1,
            90.0,
            90.0,
            120.0
          ]
        }
      ],
      "experiments": [
        "hrpt"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "bb5499875dd9375029109f20ce61e37e3e40bddaedd670229e1f99d4b1217380",
        "structures/hs.edi": "3d18bdb07a5053f136abe3e69b51940389e439aea3ba47c2251fe5ce998a0e8b",
        "experiments/hrpt.edi": "c2c754ec57afc404092bd505e22dce51bcc17d91f391b378c7559e969e6cd800",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_cosio-d20",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Olivine · Coordinates, displacements and oxygen occupancies",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.descent": "fast_descent"
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.3,
          "displayCell": [
            10.3,
            6.0,
            4.8,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P n m a",
          "cell": [
            10.3,
            6.0,
            4.8,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "f5122560b7ac87cd06b76f4d19a3573ef1f54a2d281b01c5d7388aa01d7b05be",
        "structures/cosio.edi": "ed3e7f5594f4cab7b193440098431f483428082499f191b4d8640dd12a2d6c84",
        "experiments/d20.edi": "c8d4fdecf1deb36ac5b190425365067c4e71714c071340c7c4cc5e22a2d8f786",
        "analysis/analysis.edi": "eb25ddb4323f27b49ee37478d30a7910428f4d00a7d0003a744a36f680679ace"
      }
    },
    {
      "id": "pd-neut-cwl_lmo-echidna",
      "path": "docs/user/cli/pd-neut-cwl_lmo-echidna/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_lmo-echidna",
        "_metadata.title": "LiNiO₂ [R-3m] · ECHIDNA @ ANSTO",
        "_metadata.description": "Layered oxide · Li/Ni site mixing · Occupancy constraints · TCH × FCJ asymmetry",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "ECHIDNA",
        "_metadata.facility": "ANSTO",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lmo",
          "atoms": 5,
          "cellA": 2.88,
          "displayCell": [
            2.88,
            2.88,
            14.18,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "R -3 m",
          "cell": [
            2.88,
            2.88,
            14.18,
            90.0,
            90.0,
            120.0
          ]
        }
      ],
      "experiments": [
        "echidna"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "4aa689feef827ee8de58921b970ea639720550330301b7f92f582aec419720c0",
        "structures/lmo.edi": "e9d889ae30298b4df82d49720b6ef23c181646c8afd8b8a44a68e455cf93f61d",
        "experiments/echidna.edi": "56c050bdeb4188c636ef5afbacc5d1d36353690dfb3c2689ae48b85642612d6d",
        "analysis/analysis.edi": "15de9a58c3c93c2e535daeeefe2973c5ea43b7e6a2e389c356d82b4fa9a058a3"
      }
    },
    {
      "id": "pd-neut-cwl_y2o3-spodi",
      "path": "docs/user/cli/pd-neut-cwl_y2o3-spodi/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_y2o3-spodi",
        "_metadata.title": "Y₂O₃ [Ia-3] · SPODI @ FRM II",
        "_metadata.description": "Anisotropic β tensors tied by site symmetry · Coordinates, profile and background",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SPODI",
        "_metadata.facility": "FRM II",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "y2o3",
          "atoms": 3,
          "cellA": 10.61,
          "displayCell": [
            10.61,
            10.61,
            10.61,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "I a -3",
          "cell": [
            10.61,
            10.61,
            10.61,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "spodi"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "525caaf8272cd074bf63438c5600d57b65411c64250af602f569d4c9622f8fd5",
        "structures/y2o3.edi": "0035a2409b1fa26521d4b59c9520c37d8c4bb8c2ec9e53c50ff227ad87d53ccf",
        "experiments/spodi.edi": "54b3966a0f3286aae339911ff388f3280f6552946e312b2ed5258542a565e346",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-cwl_yalo3-al2o3-spodi",
      "path": "docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_yalo3-al2o3-spodi",
        "_metadata.title": "YAlO₃ [Pbnm] / Al₂O₃ [R-3c] · SPODI @ FRM II",
        "_metadata.description": "2 phases at 3 K · Shared Bérar-Baldinozzi profile · Cylinder absorption",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SPODI",
        "_metadata.facility": "FRM II",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "Al2O3",
          "atoms": 2,
          "cellA": 4.76,
          "displayCell": [
            4.76,
            4.76,
            12.97,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "R -3 c",
          "cell": [
            4.76,
            4.76,
            12.97,
            90.0,
            90.0,
            120.0
          ]
        },
        {
          "name": "YAlO3",
          "atoms": 4,
          "cellA": 5.17,
          "displayCell": [
            5.17,
            5.33,
            7.36,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P b n m",
          "cell": [
            5.17,
            5.33,
            7.36,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "spodi"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "4fe45a231bbed80e49a7fecae6f6e051965bb6edb8678f8afc7d6af5fdabe8cc",
        "structures/Al2O3.edi": "37791064fcee7bd1e29a0b64b03c7f7b326c4b37ab97d4b01098e7e49aedb6b0",
        "structures/YAlO3.edi": "582a5e23201b519fced17407e697e46d11718a9b4d6b260c12df2ccaab5b1580",
        "experiments/spodi.edi": "a0a6cdf5fe6d807a7241f7e68456804c212120119e3bac264293f0c90723fc7c",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-tof_si-sepd",
      "path": "docs/user/cli/pd-neut-tof_si-sepd/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_si-sepd",
        "_metadata.title": "Silicon [Fd-3m] · SEPD @ Argonne",
        "_metadata.description": "Silicon standard · Jorgensen–Von Dreele profile · Time-of-flight neutron powder data",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "SEPD",
        "_metadata.facility": "Argonne",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "si",
          "atoms": 1,
          "cellA": 5.431,
          "displayCell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F d -3 m",
          "cell": [
            5.431,
            5.431,
            5.431,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "sepd"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "50da0bb240d60f01d8e954de95ea03d66813ea3dc91c3453207075d142ad2930",
        "structures/si.edi": "a873319a522398a2c26fbd3b155bb8974a9af54f4fe381277f66f72777f448bc",
        "experiments/sepd.edi": "5720646987f9ce601cfa32532c369d2fb7e5997a7635004b856c1103dde7a6b8",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-tof_cecoal-polaris",
      "path": "docs/user/cli/pd-neut-tof_cecoal-polaris/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_cecoal-polaris",
        "_metadata.title": "CeCoAl₃ [Pmma] · POLARIS @ ISIS",
        "_metadata.description": "Structure and time-of-flight profile fit · 24-term Chebyshev background",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "POLARIS",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "cecoal",
          "atoms": 5,
          "cellA": 7.65,
          "displayCell": [
            7.65,
            4.05,
            6.91,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P m m a",
          "cell": [
            7.65,
            4.05,
            6.91,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "polaris"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "2d3fd04ef008e237bf6c9b7595ea87ba870b86b91f0aa2523bdc9295e5d3c7fb",
        "structures/cecoal.edi": "def09ded57c181a601e481deef7bf49b135374646e4b05a7e6939e44a5a6acf4",
        "experiments/polaris.edi": "f76663b87db3b3356426a1fd3be25a2e26a8b10fd808978897a4bf15b77df789",
        "analysis/analysis.edi": "603772c6d4c286e53eb8554e6d2be4843c8f560cb942fec808bb8ca138eb993f"
      }
    },
    {
      "id": "pd-neut-tof_ceo2-pearl",
      "path": "docs/user/cli/pd-neut-tof_ceo2-pearl/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_ceo2-pearl",
        "_metadata.title": "CeO₂ [Fm-3m] · PEARL @ ISIS",
        "_metadata.description": "NBS SRM 674a standard · Calibration and profile fit · 6-term polynomial background",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "PEARL",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ceo2",
          "atoms": 2,
          "cellA": 5.410495,
          "displayCell": [
            5.410495,
            5.410495,
            5.410495,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F m -3 m",
          "cell": [
            5.410495,
            5.410495,
            5.410495,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "pearl"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "aeca211016c2558bee106fdf77ac1d54cc436173c3d98394e39f3406ba42880b",
        "structures/ceo2.edi": "c0736a60e1ee6a225e5d068304ba28caf8f86b0ab1fd104c6b4fa67117f7e60e",
        "experiments/pearl.edi": "457cf6771c73209cd11a20b4e9e3aed81f0e14fb3f4f082e20bed9248c8ab0ec",
        "analysis/analysis.edi": "603772c6d4c286e53eb8554e6d2be4843c8f560cb942fec808bb8ca138eb993f"
      }
    },
    {
      "id": "pd-neut-tof_lbco-si-mcstas",
      "path": "docs/user/cli/pd-neut-tof_lbco-si-mcstas/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_lbco-si-mcstas",
        "_metadata.title": "La₀.₅Ba₀.₅CoO₃ [Pm-3m] / Silicon [Fd-3m] · McStas simulation",
        "_metadata.description": "2 phases · Simulated TOF pattern · Jorgensen profile",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "McStas",
        "_metadata.facility": "?",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "lbco",
          "atoms": 4,
          "cellA": 3.8909,
          "displayCell": [
            3.8909,
            3.8909,
            3.8909,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P m -3 m",
          "cell": [
            3.8909,
            3.8909,
            3.8909,
            90.0,
            90.0,
            90.0
          ]
        },
        {
          "name": "si",
          "atoms": 1,
          "cellA": 5.43,
          "displayCell": [
            5.43,
            5.43,
            5.43,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F d -3 m",
          "cell": [
            5.43,
            5.43,
            5.43,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "mcstas"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "99b430ebb5188462e1c65635297b9659d5cedc023f38f38eb668ef4c0d7666af",
        "structures/lbco.edi": "924577a5d681aa43253ffbc435048da628318f7d0290fedd3ca6bc9602dcdf4b",
        "structures/si.edi": "d266b86077ac8cf3a8e35f802fcae5728244b9189f30dd17b8479f132e406304",
        "experiments/mcstas.edi": "6479750462101d7af25eb5f73226347791e788535c1253abb286086e9c97dc0e",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-neut-tof_ncaf-wish",
      "path": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_ncaf-wish",
        "_metadata.title": "Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS",
        "_metadata.description": "All five detector bank pairs fitted jointly · Jorgensen–Von Dreele profile · Per-bank calibration",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "WISH",
        "_metadata.facility": "ISIS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.chi_square_tolerance": {
          "value": 0.0001,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "ncaf",
          "atoms": 6,
          "cellA": 10.250256,
          "displayCell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "I 21 3",
          "cell": [
            10.250256,
            10.250256,
            10.250256,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "wish_1_10",
        "wish_2_9",
        "wish_3_8",
        "wish_4_7",
        "wish_5_6"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "075fc2c6b70a7588dd716e34b83a9deb965592bf3fa04dfcd77ba602887c465f",
        "structures/ncaf.edi": "7eefbd591ab966a95b10bf062be50d0302820a06b62f5207371857c408a0be99",
        "experiments/wish_1_10.edi": "24dd6b5278ac7369ad528da944b324e3a5d0472cd2f448c289faeb57ec78bd27",
        "experiments/wish_2_9.edi": "cc447addb349b2956750e4e8d4da74e42325acd3be70163c533f2a2b76beca65",
        "experiments/wish_3_8.edi": "14265d219fe6a6efa50b4b074d33ac8713ad6cb7d3cd7b013f13085cb976857f",
        "experiments/wish_4_7.edi": "a3833fabd3d3c4b59403d5c0d995e7ece5db4e40efcdc208024d1f0fd19c8c5f",
        "experiments/wish_5_6.edi": "2db147368b28fac20b85d9dd62479e73cf6c1c620e3d97c7a65224f34a29836d",
        "analysis/analysis.edi": "7c81ec972ad81fe5eae0e540805e3a5d28cf10f9c88cd1d6dc8eaff82a0a40b5"
      }
    },
    {
      "id": "pd-neut-tof_ferrite-austenite-beer",
      "path": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-tof_ferrite-austenite-beer",
        "_metadata.title": "Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS",
        "_metadata.description": "Instrument calibration · 2 McStas-simulated banks fitted jointly · Per-bank zero and resolution",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "BEER",
        "_metadata.facility": "ESS",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "austenite",
          "atoms": 1,
          "cellA": 3.6468,
          "displayCell": [
            3.6468,
            3.6468,
            3.6468,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "F m -3 m",
          "cell": [
            3.6468,
            3.6468,
            3.6468,
            90.0,
            90.0,
            90.0
          ]
        },
        {
          "name": "ferrite",
          "atoms": 1,
          "cellA": 2.886,
          "displayCell": [
            2.886,
            2.886,
            2.886,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "I m -3 m",
          "cell": [
            2.886,
            2.886,
            2.886,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "expt_n2",
        "expt_s2"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "431d213ca71f62f608cc3ebd9b78c10e015f1e3ac1dd547f7c44eb65ce14f052",
        "structures/austenite.edi": "8a0d6a8a8b3c20dea4553d4eec01e109d3e7f142038baaabe2d9f19442cb74eb",
        "structures/ferrite.edi": "ec49d823d61e5c7224a554dd51a842edd9465868af93a6b94209ae775e20d5d0",
        "experiments/expt_n2.edi": "3c963915d618f98cf845e8d45b2b5171debc9628fec033e144df231355c913aa",
        "experiments/expt_s2.edi": "ec5dcf452a79597dfb7d97c2ff4b3d44100dbba834c5da8b914329d5f21fe792",
        "analysis/analysis.edi": "1c24e1088d024dfe9edfd8784920133ad4476690edf8d925284411ef3c65700b"
      }
    },
    {
      "id": "pd-xray-cwl_pbso4-lab",
      "path": "docs/user/cli/pd-xray-cwl_pbso4-lab/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-xray-cwl_pbso4-lab",
        "_metadata.title": "PbSO₄ [Pnma] · Laboratory X-ray",
        "_metadata.description": "Rietveld round-robin data · Cu Kα doublet · Bérar-Baldinozzi asymmetry",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "?",
        "_metadata.facility": "?"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "pbso4",
          "atoms": 5,
          "cellA": 8.47,
          "displayCell": [
            8.47,
            5.39,
            6.95,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P n m a",
          "cell": [
            8.47,
            5.39,
            6.95,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "lab"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "075f9672a6b401a1863e3dd37b7dc96b62cc0d84e000c6078b23d7cd5659fcf8",
        "structures/pbso4.edi": "24770242effa8a4d410836f2cef855fc6454d84e5f3cd2d2bd7ab760f21b3ba5",
        "experiments/lab.edi": "ca3f995c61a0af07ffb660b5cef344a87f87ed79c7918704a595538c41662230",
        "analysis/analysis.edi": "7d828f50cfa11d9e21c6493d25e287388293d6b0de36760c45f1eca6c8a3d84e"
      }
    },
    {
      "id": "pd-xray-cwl_lam7o3-p021",
      "path": "docs/user/cli/pd-xray-cwl_lam7o3-p021/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-xray-cwl_lam7o3-p021",
        "_metadata.title": "La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃ [Pnma] · P02.1 @ PETRA III",
        "_metadata.description": "High-entropy perovskite · Seven cations on one site · Synchrotron X-ray",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "P02.1",
        "_metadata.facility": "PETRA III"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "single",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_minimizer.descent": "fast_descent"
      },
      "structures": [
        {
          "name": "lam7o3",
          "atoms": 10,
          "cellA": 5.5,
          "displayCell": [
            5.5,
            7.7,
            5.5,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P n m a",
          "cell": [
            5.5,
            7.7,
            5.5,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "p021"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "2dd84c953128d99c58a15736feabbf4bcb753b2c10cd741290949d74ef428580",
        "structures/lam7o3.edi": "f3ac01debabaf3539ce5bb66a3cbb5f4974bd89ddec736b82bd94f2c10be4e47",
        "experiments/p021.edi": "d166c4fa0b68e1ce01791d070d96bdde27b5ed69f750a5c8bd14a1919647a01b",
        "analysis/analysis.edi": "487e082c579f3bbc602f285738f6169844c7413774acc1d9b1df60030054bd36"
      }
    },
    {
      "id": "pd-neut-xray-cwl_pbso4-d1a-lab",
      "path": "docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-xray-cwl_pbso4-d1a-lab",
        "_metadata.title": "PbSO₄ [Pnma] · D1A @ ILL and laboratory X-ray",
        "_metadata.description": "Rietveld round-robin data · Neutron and X-ray patterns fitted jointly",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D1A",
        "_metadata.facility": "ILL"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "joint",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "structures": [
        {
          "name": "pbso4",
          "atoms": 5,
          "cellA": 8.47,
          "displayCell": [
            8.47,
            5.39,
            6.95,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P n m a",
          "cell": [
            8.47,
            5.39,
            6.95,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d1a",
        "lab"
      ],
      "datasets": [],
      "loaderWarning": "",
      "files": {
        "project.edi": "7e8257868dac01bd2aee23562171eeb2c18d9d1563a58ee9da7d6dbef64c2c42",
        "structures/pbso4.edi": "24770242effa8a4d410836f2cef855fc6454d84e5f3cd2d2bd7ab760f21b3ba5",
        "experiments/d1a.edi": "26e46ae4ecfc954b05f2f1feba64db526d47c0cfd9f691ace720980331eec35e",
        "experiments/lab.edi": "2abea9b19c44ec9b47d096c4091aeb7e6c62682ffcdfe6abffae2180698b50ff",
        "analysis/analysis.edi": "17f359c213950f1f635d83d1a22a465491101031b51a0e79e72297d5d7e58d4e"
      }
    },
    {
      "id": "pd-neut-cwl_cosio-d20_scan",
      "path": "docs/user/cli/pd-neut-cwl_cosio-d20_scan/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-neut-cwl_cosio-d20_scan",
        "_metadata.title": "Co₂SiO₄ [Pnma] · D20 @ ILL",
        "_metadata.description": "Cooling scan · 155 patterns from 497.4 to 52.3 K · Magnetic frames left out",
        "_metadata.authors": ".",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "D20",
        "_metadata.facility": "ILL",
        "_metadata.polarisation": "none"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_minimizer.type": "crysta",
        "_minimizer.max_iterations": {
          "value": 1000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_sequential_fit.data_dir": "experiments/d20_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "false",
        "_sequential_fit.template_file": "01_001_497p3790.dat"
      },
      "structures": [
        {
          "name": "cosio",
          "atoms": 6,
          "cellA": 10.31,
          "displayCell": [
            10.31,
            6.0,
            4.79,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "P n m a",
          "cell": [
            10.31,
            6.0,
            4.79,
            90.0,
            90.0,
            90.0
          ]
        }
      ],
      "experiments": [
        "d20"
      ],
      "datasets": [
        {
          "file": "01_001_497p3790.dat",
          "sha256": "22db61d0c3782c2614c6fccb92e1b9861010bfdb391ff87fa7ab0f53abcfc37f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4024.358,
                31.828
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                442.251,
                10.252
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "01_002_497p3410.dat",
          "sha256": "ef3eaf0029ac15202d49952f66caf1d30a8d4ca3adf82e76f3a89ef4a843728d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_003_497p2280.dat",
          "sha256": "12df6cee20e6241e84a392053ef1ad6cb9cc153d96ddbd95b025ba79f4c22734",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_004_497p0360.dat",
          "sha256": "943ff86fb9bf5d264f4a2d41e64b1d5711f26ab76de4cb90c0545900e92c674e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_005_496p5900.dat",
          "sha256": "5f3023b3820eb243fe8186c8f9ff953e1325c0d767097174f77e94419f1d8094",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_006_495p3740.dat",
          "sha256": "f2025c68fdd8fc3de28b057382d9087ea6c0b92dbec0c1b9eca54dc0ef41f2d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_007_489p9560.dat",
          "sha256": "2898a2b6434c15f02eff1c1994fa8c896c6d92b93d15a15994854e75be060aef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_008_485p7350.dat",
          "sha256": "de3f00765f6765b80157d75947c7517e997dfea579adcc76251fe644a9a7ba70",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_009_481p2260.dat",
          "sha256": "021d76aad5f57879aefa516eefc96418536d0f42af793e6a0d47d6f407e05005",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_010_476p9800.dat",
          "sha256": "1dc012ecb202cb10c04d5a70be15c2a9734c2b37d547f564ecee9d2c9abedefa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_011_472p5840.dat",
          "sha256": "acd16e373fdfe9e3cc5c597be55ec304109578badf82df8743d69f07a58ca9c0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_012_468p2800.dat",
          "sha256": "f78b5d3d9da83a3f003535847f2610e52e7dfd8374ee5950a0c3c34109f56462",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_013_463p8850.dat",
          "sha256": "d5c22e9a92bfaf425cd6ab3633325319d7a62db6e65d3916e97447c6422fd30c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_014_459p2510.dat",
          "sha256": "dd07ea491ebb2a9fd37a9b0a6204e82367ea4a1954315778ceb2fe585d93bbd4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_015_454p8870.dat",
          "sha256": "48231f25702a2c8e550c09f6272b5305549297e7647b59b7a3d8d6b28810b1a4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_016_450p3320.dat",
          "sha256": "6e363f78be7d54a57830bca46b5bd0a18f768f6b15dd8a68ed6c1d292216fb03",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_017_446p0030.dat",
          "sha256": "89c898df19634d5672e76798c37bc9e8551bb5678767e988bc41d735173483e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_018_441p4020.dat",
          "sha256": "aca3572c999b8cf60592ea7b884f67ecc8a90664361f4e6aa15590b6ef8ea6e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_019_437p1320.dat",
          "sha256": "f6418e949ff522365390f777c197ab7fbd9d76cded8c04d7d4a509a51e8b877b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_020_433p0150.dat",
          "sha256": "a3d5a690e7a7b31263035b240181507e751f6b7f0ba35b77c29cd82d6bb535fd",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_021_428p4870.dat",
          "sha256": "b80cc00f57695d56589aa857d1c72fd921acc2ec2c45adecc4d2901e49e3bff4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_022_424p1020.dat",
          "sha256": "458d5d83a455d35efe65f3a9a518cf0b66d677b280be587868a6cb9e7af2db38",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_023_419p4530.dat",
          "sha256": "33611d2a5959694b1dbe9d228db99613afe5431bc35a43e61764267a73be83d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_024_415p1880.dat",
          "sha256": "7a9fdd55cf98f32e0ec00e042999c4555b5c818c9429d6daf41fc7a166bac478",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_025_410p7830.dat",
          "sha256": "d0e151a4805a8c29be88b33249f11e1f5414e9de25dffde20869b202cdeb72ec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_026_406p1830.dat",
          "sha256": "7fa18447b1981382d68d30c896b87af509f6bba264bc1013af1650cb5b34383e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_027_402p1390.dat",
          "sha256": "a68b8fae71666b66d6139375978379ab63ce7facb1f4c63a343262c47e81270b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_028_397p5640.dat",
          "sha256": "450d09ba353d52cf88805f153913f308ec51428aa279649911a5297dd4106f25",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_029_393p2660.dat",
          "sha256": "6ebb10a745535d973fbaa3aa16bcf57f163ad99d67cedb123f6739cc0d19989a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_030_388p8760.dat",
          "sha256": "2fe4da899cfec93b4685f5ddf48cb98f639901dc2239bced310739522ed301ba",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_031_384p6000.dat",
          "sha256": "c051142ae04c23efe2323ca6ffbbdf39ee6571371d26dcc00c1cf592ff97ee55",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_032_380p2820.dat",
          "sha256": "e03e997f68637b4df7b60513c7845a260b01726f3f67fa804b355a71b94de8f5",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_033_375p8110.dat",
          "sha256": "a56ff8f5849e1e3fe67b6858352fcc88c24a53cfe579df98e97d48c2e2d9f055",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_034_371p4350.dat",
          "sha256": "76e2fd2646d8c37d1d357e4479b20e29a47c41ee357614f7d947a8c1fcbb7ce3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_035_362p8190.dat",
          "sha256": "424bea57f499991eb8aa7d224373a6bd73d0107c0977c06f0db15ed1eaab8ccc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_036_358p4140.dat",
          "sha256": "1006fc6e31bbd16528ac73eccd0e115148bcdfb75b397df5a11a5849d96131bc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_037_354p1160.dat",
          "sha256": "0e6a05e598dadc199dd04823bed2db908f96e104cbb5359fc824893a657adc1f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_038_349p8060.dat",
          "sha256": "206f085b19fa066d2b473479221c460287a40f19f5e7c1f0320c2979c8ffe32a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_039_345p2570.dat",
          "sha256": "5f1b51a111b63db9d3154dd6fa9e2dfc1c18cdaccfcd38a0f6cc97dae5e79615",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_040_340p7230.dat",
          "sha256": "7855c5f97795bcb99310acd974b65fc6aad8a5d157f41aec9bdf2802533414ac",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_041_336p6280.dat",
          "sha256": "10d3cb20af02ac533a17e0966dd41f3fb80f80bfdc5e2763d4e92b08485640f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_042_332p2660.dat",
          "sha256": "03fe53d66954d3935bbbca3c39dda6ec625c1f5627c6eb6d89e94d0364ade80e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_043_327p9190.dat",
          "sha256": "f8dbe59316ee34514cf8ddd5502b5b53609276ce3117e05d87ac7ac9afd97aec",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_044_323p3350.dat",
          "sha256": "c038f2e38226ad3fd2281b55fbb39cf04a6ef2dc3d4f0276b5c8bf0ba393024f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_045_319p0710.dat",
          "sha256": "5c2058a222ef253a0f46235b9615cf957e6414b4e52f4138dfb64be5fd173af4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_046_314p8200.dat",
          "sha256": "08d4bf74090bd142686ba02fe36c6642f4117480d0f9026b3e3a307ca64b6ed8",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_047_310p9350.dat",
          "sha256": "fec1490aaf6f59a7464c3b21cdedf6333cb3d764f8d9a13ac62478cb2d981afa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_048_306p6800.dat",
          "sha256": "29e6848c38f889e1bc839bac949c3b2404abe2f9a652a604fc4542fe55d52dc3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_049_303p0940.dat",
          "sha256": "70240b3346e701baaa43629897aeb121f54cd19aff707eabe45d2524844ca664",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_050_300p4240.dat",
          "sha256": "92e8342610fa5d0f5a749a9b4dc29479c3ac75b052db2c9a2393155bf354b28c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_051_299p3940.dat",
          "sha256": "dd2bf75b4d8e3ae22bf9643d3be77773d3b5317b6ab8a273b802bb3640059874",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_052_299p2050.dat",
          "sha256": "4565452f1baca8f389bcf7d8e47faef032fc945105c95923f74ddd4b6709c410",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_053_298p8330.dat",
          "sha256": "841b483ddd09b3c2e767db9bb9890c5ac2d1d3a937b51da72f3bc18871e3e79b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_054_298p0250.dat",
          "sha256": "eb716b2eecde0c12d3329a5651ab8d3945e07d0929a802c164b15868861dd689",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_055_296p4040.dat",
          "sha256": "acf75bbc5a6a1e60f2fec3d8e7d6101374ee8528af85817d84a816c2681eca6a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_056_290p7210.dat",
          "sha256": "940bcd89b8fe5ac1ac574ac558dcc921e82ea8b40238c76209b0bc786ad22eee",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_057_286p2140.dat",
          "sha256": "90525f159ad2e7b5dba17ba5e5a817b03e81b9bb850373e34de26fc30e00bd8d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_058_281p9010.dat",
          "sha256": "243f7d2144ece905f6de4f72acbff36fad21f42706937370f63b21afdd3ba325",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_059_277p4860.dat",
          "sha256": "7283650bc9654d294ddb40e2e97f293f9be346e04dc3b01ab80def0c379ddba1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_060_273p0910.dat",
          "sha256": "6e6045caf495e42b716d4a14b0544ae4465e7f61b9db4200b8740f2137c33043",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_061_268p6170.dat",
          "sha256": "56ae5f39aff745c323b4143c019c828b649dd24cb38b6dd995710f747cdea63b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_062_264p2270.dat",
          "sha256": "cac5e46d43612d7f3e44829e0b83606258443922c94ab58cf5f5da9767e1eef3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_063_259p8830.dat",
          "sha256": "7d831ef5c563487fead89e89d0b2f663265a34c8d8d1ca8615f7147fa88926d9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_064_255p4710.dat",
          "sha256": "9b7bee4d7bce1b21a6c949784dcc77cbe1c4f68dac20b6e1f5403d7e416892ff",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_065_250p8860.dat",
          "sha256": "5f1d25db589640730d6dfb7c267af35b6c0d108e30e927467c780335b65b711c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_066_246p4910.dat",
          "sha256": "1475795b475c580b6bebef7a47b544c125adb53e056c5e0234cc04943212fdda",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_067_242p0240.dat",
          "sha256": "a809c348dc88901c28d6a2bba6675fdcd92759739b52287aef810827d9350872",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_068_237p6280.dat",
          "sha256": "17bc9c32998fc52f5a707528e0bb34a5f5a3c758460c06a680106d7f8b15d509",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_069_233p1580.dat",
          "sha256": "353eb5a64530acc7d801ff266b4c26a28edf1f0d106cb53f31b1dabb0784cac1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_070_228p8500.dat",
          "sha256": "fa65084b98954849ab8c758c025c9d54844eccf44191b4a17f0af0048cc2aafb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_071_224p4280.dat",
          "sha256": "1d3a611527ac7c9e20d2630f570ba3d2501d06c203f30b135d59d71dc6c24607",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_072_220p0320.dat",
          "sha256": "b96c8d59b7f83d69264b2f0b9d788f510424ba4b05ab05877b3f378ea28971ea",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_073_215p5290.dat",
          "sha256": "2bb93ecf6d608b203a456fc6105f09a4da91fabdb918040bdca1f376e4eb20e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_074_211p2050.dat",
          "sha256": "de09bfbe03355eb1707e5a3f9782e5e8264b6306003ea3c43340853cd98378e1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_075_206p8010.dat",
          "sha256": "b25f8a037ebda34163d413ad3f86663a10c2de1e16479dbcd0213318421cdb6b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_076_202p4320.dat",
          "sha256": "850dc3873eb6e1351365d111421a6dd56965d3f13096f8a99761fdaf45939b6f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_077_198p0270.dat",
          "sha256": "821331225f83ffebfd52964851dc3d87b99f2767afc0229014d755b2ad93961a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_078_193p7040.dat",
          "sha256": "0f3bd513597e7753ac9be045536f431e00616e13b7d4d7a69d94bf9bb5660ed6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4030.078,
                27.713
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                412.011,
                8.61
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        },
        {
          "file": "01_079_189p3940.dat",
          "sha256": "9fd207d48eb77ecf979aaaa1cfcb1efe09edfa7259a5b26150a9669a70b5ec86",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_080_184p9760.dat",
          "sha256": "be54656813c1d4be8e78e622770e4bbc63e2f78e8600097dbae0337a2ace7f15",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_081_180p6510.dat",
          "sha256": "a35ba186cfd2383fc5610becdcd625108a38e3606c48aab96cff1f1a6d49d0cb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_082_176p5080.dat",
          "sha256": "99e844a0e5fcf2cabb3afcb4e54e7b6685d3678191371241417600b878b78e9d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_083_172p2020.dat",
          "sha256": "adab65cb6294027bb3ae955a72eb27eec38f463125f8747d5ca95c22f6f7d7b2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_084_167p8070.dat",
          "sha256": "cccb96e06d3430b50321be31f750bce1d93c9577e8baf8fe6b5571e838e9d483",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_085_163p5550.dat",
          "sha256": "b49dda0e6f80077784a6e3075d6f3e5c277b2ea61c381fb54eeca92abcf088c3",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_086_159p2290.dat",
          "sha256": "e0412cd8d7fc27c4a70276f921cf3bd2fc42216399bc37347529045cbabd3bf2",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_087_154p8790.dat",
          "sha256": "786ec6d894d6c72e98bcd75a6f6d33f79e67380ecd6f1306518cd702ced85776",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_088_150p5940.dat",
          "sha256": "9bef7dde185a0e05295b7b2cfc571759148a38b5a9e7d20c2ebb7155ce77b9f6",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_089_146p2570.dat",
          "sha256": "187774183b67a14b26fd9ca37fd2c83e1499c685aeacca49d269875e4f27fe21",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_090_142p0530.dat",
          "sha256": "2f52bfef144edebe852b12e23351f05f97e50a573181c1f2c14383444bd16987",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_091_137p9060.dat",
          "sha256": "9cbb27d5e6862e44010e27b37e2e6bc092eff833555d83a6bb40c2ff4ddc7b2c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_092_133p7450.dat",
          "sha256": "ed8e8a37b1b57b1ec606e2c5ee57d40d946d34249e879ab44fd5505c79f1da45",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_093_129p5840.dat",
          "sha256": "48b543ba633903102e0be89434ef4269cfec2faabddcc4209471a1228d63491e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_094_125p4340.dat",
          "sha256": "a5fc59c5920f766e8057cde53301488b64fb737f2fe69ea2db029d8a1d6c6124",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_095_121p3580.dat",
          "sha256": "31e9e79b02c15a215dfb9d25f79e69a9989b8f69413608a04954c3392733de27",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_096_117p1490.dat",
          "sha256": "1e9cd3e8c1ec347cb153e9cef1754912b90d64919206cba528ec107579b7f71b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_097_113p0630.dat",
          "sha256": "04e9db3d4b807c246171fa9efc761987edd89b8e4c0bbbc4db58149e2e21d61f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_098_109p2600.dat",
          "sha256": "fe318a1be180fe8bb36553072a06fcb914716f775e4178c57196c3f54bbe7440",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_099_105p6360.dat",
          "sha256": "a1db92e7f37ab2530b18f9c979e7626e81d320fdc62e0a99ad6b55257912ea08",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_100_103p0030.dat",
          "sha256": "2c963c020313193b28e64a42e7d217b52e3548dbd22e17a6bb1ce212b19ecc99",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_101_101p9130.dat",
          "sha256": "b60e169864b4fcc0a34c5cd18bdcda39eb73565319b70d1dcea644602e266bcf",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_102_101p8800.dat",
          "sha256": "fce7aae98c761517eab36c3435fad63f1b54b42cfeed5d9aa3dd6cc52507cade",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_103_101p8220.dat",
          "sha256": "380ec121a9e49a470b3cb567c66739ccba346c9959ea8ac3e7f5d5866d7aec8c",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_104_101p6830.dat",
          "sha256": "660fd2627db86042128122ba1979627462e9787bed8746fb3683891a726bf9b4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_105_101p3630.dat",
          "sha256": "122de03f7e29f0ba58bfa1e62a16d21f1d70ac179f7150af95825078a1b377d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_106_100p5400.dat",
          "sha256": "2cdd6346481323006d05564bdd8c58cc7522e6440ef5333d785abf2def2f9efa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_107_099p5650.dat",
          "sha256": "28eaf543a7cc252ac4e9f82c0c449071c9892e3306483c929232a28efe10f4f0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_108_098p5500.dat",
          "sha256": "6a23ea8bcc2c3014e7d5fb60d525105a6c1ba1d4908f6042535ee90192b77219",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_109_097p5340.dat",
          "sha256": "f1fb0335a3df055a0dd1d468f23c430aef3d41c33555c684d8e4ced5ed4ba78e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_110_096p4920.dat",
          "sha256": "bb9babfd6b49b4cb019f007ac4f9683a14c8dc9f89fc9eddd092677094bf41de",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_111_095p5170.dat",
          "sha256": "23e84372a799fba239ccc6e3c7beac018b9c17c73c3ebf43ccf1d332cddb677b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_112_094p4880.dat",
          "sha256": "fbb59687dfec327ef1368e073bdf04a3b61fc071a78f89803751235ea32ab9fb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_113_093p4840.dat",
          "sha256": "91e30e877319e41a9a13e9ea2171d71f9de992c31e9ec6bd063f92e7c9c3e228",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_114_092p4800.dat",
          "sha256": "341c1a1e0b27ed7b8182971ab13b4cf68657d5b9f40e78e9f68efea059fb3e67",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_115_091p4890.dat",
          "sha256": "d4b270af7d468e0cb960a7b8a1e821a7e5565e65c7f9cdd2596ac325e63ae415",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_116_090p4890.dat",
          "sha256": "fdff650c5d456acb17b8d145c38c0bc0929eccd291570e39d734711bfd2ccb35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_117_089p4800.dat",
          "sha256": "a9a99d3e263c724b28b8b945b30e7846101952a87cad1458138e43a8adca77fe",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_118_088p4620.dat",
          "sha256": "a5971a3ea8bd0c09c26df43e41f00ba736066fc4d8d052b74b7196f0658780ef",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_119_087p4450.dat",
          "sha256": "6fe2f51b48a833d73b7be41dab21f6cda08a054dcb817a9601671c323f8d988e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_120_086p4230.dat",
          "sha256": "c69586ac805e3af61a33d90b87e635e7f895b724c78f32f02211b28203fe4a13",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_121_085p3880.dat",
          "sha256": "356f9e9f7f7d96f760a789bb577e15d5e42ede954fffaefb21fbc6cc8c8e1424",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_122_084p3500.dat",
          "sha256": "5546c302c3af0bd2bb86386677de6e13c30a8808fca1271631cb228a7f4d650f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_123_083p2780.dat",
          "sha256": "ab54111a4bad28e9b194ea9c79b824204b9fe57cd2e3592c9037d2217118e957",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_124_082p1890.dat",
          "sha256": "b5426601315463137a772b5a2f38cc75bfca98a567d576b24ca4cc53c2721933",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_125_081p1590.dat",
          "sha256": "0d8bfe903fe180e35e3ab9644d9ae95290807d660c0bd555186fc782091c9311",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_126_080p1810.dat",
          "sha256": "f436500faab79ac06a477f25279e666fc395aa1309f6206c4cfc370e5ab236dc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_127_079p2110.dat",
          "sha256": "565eb4a52e8001ab11d847cabe6c71db3de5288b55044202d1bead9792dc96aa",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_128_078p2390.dat",
          "sha256": "32338a8411205faf0cdbb6c740df2867df4140f25564f687a87ed4f9e6b8457d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_129_077p2590.dat",
          "sha256": "9f6ed717261d3de98b96991b91ca1fb2b54eca19b47ec16838867caef8915dbb",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_130_076p2370.dat",
          "sha256": "61a7e8264179201cf1419b47c7ae62cbea5ce243810c7415e974efee7f58948f",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_131_075p2470.dat",
          "sha256": "641c94352867e68da1ac3169da18b4b95e5fcb04356bc23f6bcbcc2393546968",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_132_074p2460.dat",
          "sha256": "f8523d6cc3107326f4336d080b447d1ba2c6a065e51189ea14fa01401871f7da",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_133_073p2490.dat",
          "sha256": "0d2b0add7aa63374321bcadeb41c09b21b1619cba288b9595d6b0cd1abf3fdad",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_134_072p2520.dat",
          "sha256": "d0591e7013ac0001709d1d1b21f9fa3d9be0ca6f0b0f2101ebecf861b4da3728",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_135_071p2550.dat",
          "sha256": "803b7a6ff8dd28c8f728105f00ca2cee7e73cc53137ba96de8974282143e975d",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_136_070p2250.dat",
          "sha256": "798255d0b928feaead4de0698608821eb06915c5a4dd67b99a4815986b9557a1",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_137_069p2340.dat",
          "sha256": "be0e5eabb2dcdf28b310958cda178b9777e974370c651e4f9d792adc049ef4b0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_138_068p2110.dat",
          "sha256": "0c9777ed8db46f31ebef1aa1c4b8ffb59f01208158e492151a65aa83770793d4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_139_067p1860.dat",
          "sha256": "67e114cf9eb3ac20e1325b2271e20c9fa612ace8188d0056aecd232545054cf0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_140_066p2090.dat",
          "sha256": "29daac593288f93fb1c6f3c9633c3306571c1ab66bb37f3dcc64f606ab0a9e35",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_141_065p2420.dat",
          "sha256": "fad943baa9b1621d072a1a2ffccc85e3091000062a45e2abf33637d5a002fc80",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_142_064p2810.dat",
          "sha256": "fd6f185b182b286b474bca2959a1a74c05125b7b6da907e1c1fc4f6b64119738",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_143_063p2750.dat",
          "sha256": "67f4d6e158ec69618c5be22eb762be95da14e754a0cfb5378dfa12518116d94e",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_144_062p3420.dat",
          "sha256": "ed46ce55bfc090d19cff03c8583c977b76beea36d3ca9c73dc7fb443106c4dd0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_145_061p3970.dat",
          "sha256": "7a2da67d3d162992697ae55962ec0b05f4dc23df10a487fe3d3293e66d312779",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_146_060p4590.dat",
          "sha256": "6ae57bb627d9d02c5ff29b2c704252a8d3a6db30740e3c3ef15176f1b8df12d0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_147_059p5330.dat",
          "sha256": "795069a1c843c39047fa93a06d5470de4a455a1766ac46f3256dc969b10c6be4",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_148_058p6120.dat",
          "sha256": "1b01909c754668e190702a9e431c1e6261ade0bde50c7c2ff2732b3c4c262e7b",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_149_057p6970.dat",
          "sha256": "c669aa6aa7081b786c150c8f6b0ba3e85d25e637e907ba4f0b12ceee4b532d92",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_150_056p7860.dat",
          "sha256": "11d5df33f66162035b7475748d6f0eb50fef402628e35baef9527ccb86999dcc",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_151_055p8750.dat",
          "sha256": "6d0fcc54e30995618e087169d843308e2edcf43198da06723237e67eb2bae203",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_152_054p9730.dat",
          "sha256": "fc0630582ea6a255ff3933ab0db9a5a6102dba721ccbf5edfb4727403790f15a",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_153_054p0730.dat",
          "sha256": "f5cb618b08438919701e21e20051c3aa95cd3d48aadfdfedf5a2699b7f4da0e0",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_154_053p1720.dat",
          "sha256": "b1a9779c8a27da47bb1975645c7257101878758e16c1f5ea40b8a94f4f97f0a9",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ]
        },
        {
          "file": "01_155_052p3450.dat",
          "sha256": "c6ddfe0309c55ce450cdb1b9a0a009b1dd2a66b0616b3f39f911bc86fd64cc19",
          "range": [
            0.0953,
            150.8953,
            0.10006635700066356,
            1508
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                0.0953,
                4066.526,
                27.949
              ]
            },
            {
              "index": 754,
              "values": [
                75.4953,
                405.145,
                8.572
              ]
            },
            {
              "index": 1507,
              "values": [
                150.8953,
                0.0,
                1.0
              ]
            }
          ]
        }
      ],
      "loaderWarning": "",
      "files": {
        "project.edi": "e457fc6ef52ce696fbf6a766486d5ba2fe4af4ab9c7c15925a557c490db29786",
        "structures/cosio.edi": "db297a9cb8148c8be36f3d5d52d5151e9b0f67e31ffcf92e52854a678c4f24d6",
        "experiments/d20.edi": "841aa1a1ca4c6f39c3eb82664ebc9832c47ca4fe53650da29c62a43626b54393",
        "analysis/analysis.edi": "f3be9aaf7a450a964908736076414946c1dbe77087030fe2cb632d679f5e362b"
      }
    },
    {
      "id": "pd-xray-cwl_latp-bm01_scan",
      "path": "docs/user/cli/pd-xray-cwl_latp-bm01_scan/project",
      "metadata": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_metadata.name": "pd-xray-cwl_latp-bm01_scan",
        "_metadata.title": "LATP [R-3c] / AlPO₄ [C222₁] / AlPO₄ [P6₃mc] · BM01 @ SNBL",
        "_metadata.description": "3 phases · 73 synchrotron patterns · Linked displacement parameters",
        "_metadata.authors": ".",
        "_metadata.created": "22 Oct 2026 09:50:09",
        "_metadata.last_modified": "22 Oct 2026 14:01:42",
        "_metadata.purpose": "refinement",
        "_metadata.dimensionality": "1D",
        "_metadata.instrument": "BM01",
        "_metadata.facility": "SNBL",
        "_su_format.rule": "iucr_19"
      },
      "analysis": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_fitting_mode.type": "sequential",
        "_sequential_fit.data_dir": "experiments/bm01_scan",
        "_sequential_fit.file_pattern": "*.dat",
        "_sequential_fit.reverse": "true",
        "_sequential_fit.template_file": "latp_312.dat"
      },
      "structures": [
        {
          "name": "alpo4_c2221",
          "atoms": 4,
          "cellA": 6.97,
          "displayCell": [
            6.97,
            7.11,
            7.004,
            90.0,
            90.0,
            90.0
          ],
          "spaceGroup": "C 2 2 21",
          "cell": [
            6.97,
            7.11,
            7.004,
            90.0,
            90.0,
            90.0
          ]
        },
        {
          "name": "alpo4_p63mc",
          "atoms": 4,
          "cellA": 4.983,
          "displayCell": [
            4.983,
            4.983,
            9.504,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "P 63 m c",
          "cell": [
            4.983,
            4.9832407377064385,
            9.504,
            90.0,
            90.0,
            120.0
          ]
        },
        {
          "name": "latp",
          "atoms": 7,
          "cellA": 8.4953,
          "displayCell": [
            8.4953,
            8.4953,
            20.8268,
            90.0,
            90.0,
            120.0
          ],
          "spaceGroup": "R -3 c",
          "cell": [
            8.4953,
            8.495251128959499,
            20.8268,
            90.0,
            90.0,
            120.0
          ]
        }
      ],
      "experiments": [
        "bm01"
      ],
      "datasets": [
        {
          "file": "latp_312.dat",
          "sha256": "cd3dc944fa035058af4caba8773f4247c955d5e5c29bfaef1504d70aacc05794",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                34562780.0,
                24701.53
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                28934400.0,
                145.9334
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                23445790.0,
                1155.716
              ]
            }
          ]
        },
        {
          "file": "latp_311.dat",
          "sha256": "5a332ab8d4901c54e4126ae0e153c4452ae1b5babe4bdaeae7cd6b8e43750e0e",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_310.dat",
          "sha256": "1e96b9c9336dbef7bc5df88104d618163de2b4d2931d0c2d81657adf997fc454",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_309.dat",
          "sha256": "ef861319c4b48a66f6c7f0037d6e9ba1018b20f6499383cecb478dd1d4b01c63",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_308.dat",
          "sha256": "84471889a6d91b78532f99995219198945f58d4b8805acd7f36f89d8209747e4",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_307.dat",
          "sha256": "e8d12faab8d68abaa9ec2c10f162070c0887b46c7aba47cd24ace3d32445f8e5",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_306.dat",
          "sha256": "1c15258a3b4fe43a02e422b37d39ad6034ed36bc95d9878f85c64a2c7d5215c1",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_305.dat",
          "sha256": "e221c7d1484f718bda49ff0059eec0af08a724592d27c50a1a985d25e916b82d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_304.dat",
          "sha256": "bb777343b334e2317c0d74f085ba70552da2eb813a11a19b06383b360ded02f2",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_303.dat",
          "sha256": "e7dce12320374b1852afa8d865195cd36dbc9c7bf6b7696b650a69cc419d63e0",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_302.dat",
          "sha256": "7b7c69a722e93829317f692d5636fa404e95d5b44d6ecf814e9faec371ef40c3",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_301.dat",
          "sha256": "0c868e3ba7b3f4877c5d48d19e015801952bb74ccb2a4b2f8b5d890770200796",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_300.dat",
          "sha256": "cd60091d7234955ecc0e11d895176a2e0fd2b91670d98feb64b88df37146eb26",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_299.dat",
          "sha256": "de32f4da3d9b70a5e80df1008731bfafdd670b055e559b6eb2b61c886c47b927",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_298.dat",
          "sha256": "8493bb29aac751d2080eabc681515fa292af1745a3937631d1ff45c8a8eb86ad",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_297.dat",
          "sha256": "001eebfbfdd16ce3e8a23f21dd307714a2d5be492b79d89f5cc378ed85c7e51c",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_296.dat",
          "sha256": "66a5f34554e79943f4b056cfa67f4af48c0c962f3509f2f2693c3a46b9acba9e",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_295.dat",
          "sha256": "b5a6e719296bc3b34775149419f22e2936d1eacf9e4810edb33134023a303a13",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_294.dat",
          "sha256": "604e81e0447837df88ce53d309f6bcb0c3c6122e530cf0445bb45ceb89a3a19b",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_293.dat",
          "sha256": "56eea771a448e2051179620deff4494d9692bdcab981601fc1513ac6538b2cf5",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_292.dat",
          "sha256": "af32a1a4b6a4ccc94e5bdcb5b14109e3e2a4b6c4baf6a3564b2941e2942f23ad",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_291.dat",
          "sha256": "dd0905f4b7610c9f102cb7039c30ac2fe1dc8d69ff2fccd8a106cbf2a0214f71",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_290.dat",
          "sha256": "586fa1d78a5f866eef08c1eb146c308db02ae3027e0f666ab86dfabecb2d626b",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_289.dat",
          "sha256": "e22c5b18834adcc67e409c5230297d279bf5c725809d4ea5c16586ca35fd07b3",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_288.dat",
          "sha256": "1fe408408d40d238d013afd8138646143fdb8bd76be7ad9891cfd8e3c7b83ecd",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_287.dat",
          "sha256": "680ff2690c20fdac323c3f4e744e5eb379e0364718015edc208ab679d8064108",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_286.dat",
          "sha256": "d5dc54d2c4e182b6c7bb43867561d8e23f3a7bed81832bc8cf7971f946e7c16c",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_285.dat",
          "sha256": "32f16bc1047e43b1a1130fc282ccee952077f3e5eeb88c9dc36d0cfa77a196df",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_284.dat",
          "sha256": "77b3bfa9fe5dbb66d21de403a7d97e55c7a4679ad471dc6d92f6a8db01e33a7d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_283.dat",
          "sha256": "9a75c89b8dbea5a5ed6569d3ab957e35d9d4aead528b0e48fe314a91bb4f61f3",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_282.dat",
          "sha256": "0fb8d0a138bea39124e5e380748e9daf79d9fcdea689f6b542783d25416930e2",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_281.dat",
          "sha256": "d0ea90c5b8b87bb88eb1f0eb9e4c0e3e1816a36ad29e980005015de0be43427b",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_280.dat",
          "sha256": "1e30f9276fe15c106adb2a7c81ff1cf77dc9555c1aad4e134398e8726d92ac56",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_279.dat",
          "sha256": "b6e7ad7012dc948ba849718254f37a1696c9f809ca2cb7a1077979fc59f16fd6",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_278.dat",
          "sha256": "1da075fb35617097af73bdcd534d05bd6462e45212713a9f2b0ff47ef2bc5043",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_277.dat",
          "sha256": "a9d9a947f58ea9e48c256ef002e6e28998fca92ddd35426c7a965ab85cedcd8c",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_276.dat",
          "sha256": "f11d15a339772a97bbd66bf002bae69fe9684af1387a975d43b7128adfab1eb2",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                33068030.0,
                24161.49
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                29000450.0,
                146.0957
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                30677260.0,
                1321.854
              ]
            }
          ]
        },
        {
          "file": "latp_275.dat",
          "sha256": "fc10c8360bd02a24a1c3f914978df480dc2962185023eee5de659a4df22dd58d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_274.dat",
          "sha256": "7fc54b849420978c1b531166a90d5e5bcfa8c1e67dada09c6236709020049a36",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_273.dat",
          "sha256": "c2a26b75e4b8f06bcf4f9b4a16046333b0ff673784859a68af657bd8de2522f9",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_272.dat",
          "sha256": "696a7f4148c15704666c29f2d01cd739db680c5a21ae25aff0a1620f12662291",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_271.dat",
          "sha256": "dbdde893605cab68a6ad14a8e5f8f35f28a9373ac98c78e8d999d9a3b6f5d364",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_270.dat",
          "sha256": "fa7ec964987eec63d6236bd0cf0aef98cc02d859a936efabe15c94f9fc402e8d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_269.dat",
          "sha256": "e3933645aa72a91a523b9aa2f716869c4b085f9f143b8688226052d5279288af",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_268.dat",
          "sha256": "81d95619043a6b3b9a89b81918acb586044b2f2cb4c8eec20b4490292160798d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_267.dat",
          "sha256": "b04822521fb9152b7770b7b31d06d69f353afceddfa1da59faa54849c42d0375",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_266.dat",
          "sha256": "904833ab1a2bc7b17f90892b537cbc9f1ed01684297cbe5aaaa68b24476c1f29",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_265.dat",
          "sha256": "82eab61ac54177f86a6ab7db2b9331d710054a870586cf95c92d3bf7d69ebff5",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_264.dat",
          "sha256": "64afde298e0bd34f8e098886572b44f2450b148b63360f4692e2c0456e0b783d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_263.dat",
          "sha256": "cac138f145a6f12768dd00d710e90cbfb53a0d5fe26ecd829d0c904cfbff7278",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_262.dat",
          "sha256": "3d3fce2b7cfe6c3d3a8859a92f970570f8c7df17d05889de4535819dd4c1c496",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_261.dat",
          "sha256": "7b85c597f10c4463b00745957fcd118e8e8882c91489104668d8fab8277503a6",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_260.dat",
          "sha256": "70d3863ee1ca9b7418fd81322dbbfee2ca2523b3fabdcfed28d68653ea58149e",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_259.dat",
          "sha256": "c77ee7d4fa994e59b30f7de2bf2d64799bd0ceb5c84b3e2e8eaeaeec1b592f16",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_258.dat",
          "sha256": "dba168b82a57ce0feea2f631f0791985a7f6f2400235ad0fd6c05783a239b1b1",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_257.dat",
          "sha256": "83152d67060f754dddbb3ea384371346203d743de58198a33a4345888d622431",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_256.dat",
          "sha256": "f7018bba3c2fe1c09f54674fd7a984d0469054c8cecb38218a65b19cb26ec69d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_255.dat",
          "sha256": "e9e2a5e259cd26b5e6a29d779f20df858c907b89a133b1bc59e9eb2a5b6e7aad",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_254.dat",
          "sha256": "fd65a3d05bc066fbebdde4bf87e8e5ad6ef6e35dbd2b503a755fa47d705c22e6",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_253.dat",
          "sha256": "5c7a04c8d24ceaa9938d5430ff87f09e4fb104b7708184252c6bbeea52f272d5",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_252.dat",
          "sha256": "c1617690307d098fb4fc0008f9f2fea2232c41619d50830a7773eae0bc8fa8fe",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_251.dat",
          "sha256": "a5d740471dffe7252f37a17e1fa31a77bb283ad98fab76136c135798b6585676",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_250.dat",
          "sha256": "1ab67e88cceb3f20f4cfe516ddcd9b17eca3a02b6a4c4848c71071855c39dc46",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_249.dat",
          "sha256": "0fcc676638e227d203c7e76d547bcc7edf88be23d878617bf728bbda6a3cfb47",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_248.dat",
          "sha256": "c96bb957fe558976d57a1ea8084e2c91d0ea9f5e34ec2e40ec7f1e2f48d36e2c",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_247.dat",
          "sha256": "cf3d7e12a7b7d69fcfa1164b87c9ca785e3eb20d5662dbda9cd51623039475ed",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_246.dat",
          "sha256": "b0b80be9e1988f6fb52f5caf7339d3a57709996e1060b42afa947a5757082aa7",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_245.dat",
          "sha256": "4b01694748ef95a354dd7f5aa2b5cfb6598ab9eef0596e0624764ab92cf3d85b",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_244.dat",
          "sha256": "157e14c1deee032ec2724a719f606c9de3e0485418e86be0cf2b65b05e6a6483",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_243.dat",
          "sha256": "865aaf40320ff185c267842492faad4273f9d82f350c114035f362170f88978d",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_242.dat",
          "sha256": "1670502096c41689fc935fc41ba910008206422aad385b6f56a3bee32b712cc6",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_241.dat",
          "sha256": "25b576445e35b49c9ae8e9247518c05f3705cd97ec14dcc7823d86ceebc6163b",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ]
        },
        {
          "file": "latp_240.dat",
          "sha256": "3b9d988630366da767e4b12f28e2124050d7a997ae7071e170ee97a5577f4728",
          "range": [
            3.67257,
            63.0724,
            0.018785524984187223,
            3163
          ],
          "samples": [
            {
              "index": 0,
              "values": [
                3.67257,
                28870320.0,
                22575.91
              ]
            },
            {
              "index": 1581,
              "values": [
                33.37249,
                41120690.0,
                173.974
              ]
            },
            {
              "index": 3162,
              "values": [
                63.0724,
                36706480.0,
                1445.965
              ]
            }
          ]
        }
      ],
      "loaderWarning": "",
      "files": {
        "project.edi": "bba48295f833c50bfaeb3c27ee82c6c653f987976678c97b41bf9c7e6a44d71e",
        "structures/alpo4_c2221.edi": "b42662d5570b1a08f3b1df6451af8ff1f5c6e69ea3b40bd78f39dd2b181c5306",
        "structures/alpo4_p63mc.edi": "350e4eb631946104099c05296a072d96fd63ed5a28e13ada6e081bfd77610d5e",
        "structures/latp.edi": "2fa22f4a9a8554731d4abc98d471cb0a81a9b9a39eec390b7219a72d4d1ad3a9",
        "experiments/bm01.edi": "b25970da46d7829c717432de06c7d1a7e9f8f914a0b1bfce54d99cfa39809bf3",
        "analysis/analysis.edi": "54e3863bd8ff2eda1080f5784b54d828a2bb6050903a9c9d86b2421f1f8deba3"
      }
    }
  ],
  "corpus": [
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project",
      "experiment": "d20",
      "sha256": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.0953,
        150.8953,
        0.10013280212483398,
        1507
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.broad_gauss_u": {
          "value": 0.23091065335098124,
          "free": true,
          "uncertainty": 0.00783695876908295
        },
        "_peak.broad_gauss_v": {
          "value": -0.5140245672916492,
          "free": true,
          "uncertainty": 0.01687653105597828
        },
        "_peak.broad_gauss_w": {
          "value": 0.37261626098763034,
          "free": true,
          "uncertainty": 0.010527576747697052
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.012941642271138643,
          "free": true,
          "uncertainty": 0.005158706509940048
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.2900788119975914,
          "free": true,
          "uncertainty": 0.0022671137191298996
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project",
      "experiment": "d20",
      "sha256": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.0953,
        150.8953,
        0.10013280212483398,
        1507
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.broad_gauss_u": {
          "value": 0.23091065335098124,
          "free": true,
          "uncertainty": 0.00783695876908295
        },
        "_peak.broad_gauss_v": {
          "value": -0.5140245672916492,
          "free": true,
          "uncertainty": 0.01687653105597828
        },
        "_peak.broad_gauss_w": {
          "value": 0.37261626098763034,
          "free": true,
          "uncertainty": 0.010527576747697052
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.012941642271138643,
          "free": true,
          "uncertainty": 0.005158706509940048
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.2900788119975914,
          "free": true,
          "uncertainty": 0.0022671137191298996
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project",
      "experiment": "d20",
      "sha256": "89c14df4a88f6eeedc8d42647ad4bda32c52856d2fe58e6a64f041062e5d86c7",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.0953,
        150.8953,
        0.10013280212483398,
        1507
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.24,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.53,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.38,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.29,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project",
      "experiment": "d20",
      "sha256": "c0ef1ce128acbcc94eda9294f6afd63fd80c059eb7f7e5f1c5981f3efb07fbca",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        8.0953,
        150.0953,
        0.10021171489061398,
        1418
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {
        "linked_structure": [
          {
            "structure_id": "cosio",
            "scale": {
              "value": 10.0,
              "free": true,
              "uncertainty": null
            }
          }
        ],
        "background": [
          {
            "id": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 8.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 2.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 9.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 3.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 10.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 11.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 5.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 12.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 6.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 15.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 7.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 25.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 8.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 30.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 9.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 50.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 10.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 70.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 11.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 90.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 12.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 110.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 13.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 130.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 14.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 150.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": null
            }
          }
        ]
      }
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project",
      "experiment": "d20",
      "sha256": "6b86e5db73f55ae128b14d5ab237595530483f4543886f7e8d4012d30e05e1be",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        8.0953,
        150.0953,
        0.10021171489061398,
        1418
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.001,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.25,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lab6-11b-echidna_tch-fcj/project",
      "experiment": "echidna",
      "sha256": "a51359be4b97bed9f488f4022c9efaba6267d954a8ca110c2ed39deb5b9c5eb6",
      "peakType": "cwl-tch-pseudo-voigt-fcj",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y",
        "asym_fcj_1",
        "asym_fcj_2"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "calib_sample_displacement",
        "calib_sample_transparency"
      ],
      "range": [
        3.86396,
        163.75638,
        0.04998200062519538,
        3200
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.089876,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.377516,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.476188,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.052654,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_fcj_1": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_fcj_2": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt-fcj",
        "_instrument.setup_wavelength": {
          "value": 1.622536,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.21356,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_displacement": {
          "value": 0.05395,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_transparency": {
          "value": 0.09127,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.7,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "polynomial",
        "_background.origin": {
          "value": 80.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project",
      "experiment": "echidna",
      "sha256": "80f077806e554470a5b4943991e795c465db78266fc072a6c07f9390e8117d6b",
      "peakType": "cwl-tch-pseudo-voigt-fcj",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y",
        "asym_fcj_1",
        "asym_fcj_2"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        3.86396,
        163.75638,
        0.04998200062519538,
        3200
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.broad_gauss_u": {
          "value": 0.143431,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.52314,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.590412,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.054515,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_fcj_1": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_fcj_2": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt-fcj",
        "_instrument.setup_wavelength": {
          "value": 1.623899,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.45778,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project",
      "experiment": "hrpt",
      "sha256": "cfe9ea2b020d8ac9b8b61a7affb253787d6a8a27be10462c396091f6e96baf7e",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        164.85,
        0.049999999999999996,
        3098
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.broad_gauss_u": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.001,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.494,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.6,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {
        "preferred_orientation": [
          {
            "structure_id": "lbco",
            "march_r": {
              "value": 0.8,
              "free": true,
              "uncertainty": null
            },
            "index_h": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "index_k": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "index_l": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "march_random_fract": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            }
          }
        ],
        "excluded_region": [
          {
            "id": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "start": {
              "value": 0.0,
              "free": false,
              "uncertainty": 0.0
            },
            "end": {
              "value": 5.0,
              "free": false,
              "uncertainty": 0.0
            }
          },
          {
            "id": {
              "value": 2.0,
              "free": false,
              "uncertainty": 0.0
            },
            "start": {
              "value": 165.0,
              "free": false,
              "uncertainty": 0.0
            },
            "end": {
              "value": 180.0,
              "free": false,
              "uncertainty": 0.0
            }
          }
        ],
        "linked_structure": [
          {
            "structure_id": "lbco",
            "scale": {
              "value": 10.0,
              "free": true,
              "uncertainty": null
            }
          }
        ],
        "background": [
          {
            "id": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 10.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 169.0,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 2.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 30.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 164.1,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 3.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 50.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 166.91,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 110.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 175.27,
              "free": true,
              "uncertainty": null
            }
          },
          {
            "id": {
              "value": 5.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 165.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 174.56,
              "free": true,
              "uncertainty": null
            }
          }
        ]
      }
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project",
      "experiment": "hrpt",
      "sha256": "c7a093e4cdee2aeca6553b84cca81293b748caeb6270d2083b5a043724128c26",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        164.85,
        0.049999999999999996,
        3098
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.broad_gauss_u": {
          "value": 0.081547,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.115345,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.121125,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.001,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.494,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.3,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project",
      "experiment": "d1a",
      "sha256": "f494c2665e6d1a9986165650e677af2214e5fa63a797ce3ad15e8599064ce2e2",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        155.95,
        0.049999999999999996,
        2920
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.153402,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.453103,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.419409,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.25,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a0": {
          "value": -0.36248,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": -0.02261,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": -0.03862,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": -0.04941,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 180.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_instrument.setup_wavelength": {
          "value": 1.912,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.08424,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project",
      "experiment": "y2o3",
      "sha256": "caa9b49442b995beef7b830e8709e1b62dfd015bc140fdf7a96c4719b62ed72d",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.95,
        153.9,
        0.05,
        3060
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.036631,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.068345,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.131426,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.54822,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.01625,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_yap-spodi_3k/project",
      "experiment": "spodi",
      "sha256": "524a651bf9680b706da031ee998f1f8be52d6c1e2bf9038124ee89a5d3890279",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        4.05,
        151.95,
        0.04999999999999999,
        2959
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_instrument.setup_wavelength": {
          "value": 1.54816,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.00146,
          "free": true,
          "uncertainty": null
        },
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_u": {
          "value": 0.038892,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.0462,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.10586,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.12522,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": -0.22457,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": -0.00305,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.11122,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": -0.05563,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.0221,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_cecoal-polaris_chebyshev/project",
      "experiment": "polaris",
      "sha256": "940231cb84abc21ad60fe760c793b603e8acbb6cb20478d94dfe858d250c33c0",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        3001.589,
        19004.658,
        4.334525731310943,
        3693
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_calculator.type": "crysta",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.2971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.043085,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.002867,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 39.4615,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 4.7781,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 4.2,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 145.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 3.93042,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 6176.03076,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.92194,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.01561,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "chebyshev",
        "_background.x_min": {
          "value": 3001.5891,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.x_max": {
          "value": 19004.6582,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ceo2-pearl_polynomial/project",
      "experiment": "pearl",
      "sha256": "dd405b91a0eea1bcc0c82d7763a7ae7ad2987b94169b9bb4e50454a140c57efd",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        1500.25,
        19400.1875,
        7.094703725723345,
        2524
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_calculator.type": "crysta",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.251559,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_0": {
          "value": 0.025455,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.029005,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 83.8088,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 3.5751,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 4.8407,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 3.05177,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 4677.93018,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.7621,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.00029,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "polynomial",
        "_background.origin": {
          "value": 7000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_diamond-dream_basic/project",
      "experiment": "dream",
      "sha256": "82cab19d185fb4bf3a4706995e43af5b6b60a365d1db808fda958bdaaafba249",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        8530.1009,
        66503.6911,
        29.001295747873936,
        2000
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.022544,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.01433,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 46937.7188,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 4887.918,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 28385.86133,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_fe_pseudo-voigt/project",
      "experiment": "beer",
      "sha256": "830696bd336668d52a2d0358fae8748d7447a2e01fb21df34953a4475ab0607f",
      "peakType": "tof-pseudo-voigt",
      "mode": "tof",
      "peakFields": [
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        40158.2311891045,
        135592.47482202607,
        31.853886392830965,
        2997
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_calculator.type": "cryspy",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 893.6397,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 1283.6387,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 311.7041,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 5.033,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-pseudo-voigt",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -10.29183,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 54902.1875,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project",
      "experiment": "expt_n2",
      "sha256": "6e8f4ac836219d4ba503ff5583823b1d12eb523f788e16c03d86b2b5d2bacdda",
      "peakType": "tof-pseudo-voigt",
      "mode": "tof",
      "peakFields": [
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        40094.52341631884,
        135592.47482202607,
        31.85388639283096,
        2999
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "cryspy",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.broad_lorentz_gamma_0": {
          "value": 5.0279,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 914.6177,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 1249.5679,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 325.2586,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-pseudo-voigt",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -2.09073,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 54902.1875,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project",
      "experiment": "expt_s2",
      "sha256": "948b6f720ed6d72a5d5f0c5b8b06cae3dca6159f4f9e6edd56739110a2f2290a",
      "peakType": "tof-pseudo-voigt",
      "mode": "tof",
      "peakFields": [
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        40094.52341631884,
        135592.47482202607,
        31.85388639283096,
        2999
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "cryspy",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.broad_lorentz_gamma_0": {
          "value": 5.033,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 893.6397,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 1283.6387,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 311.7041,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-pseudo-voigt",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -10.29183,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 54902.1875,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project",
      "experiment": "wish_4_7",
      "sha256": "053751e9274de8a61c12fe3b8b0d96dca3f88ff0748db36ecd0ab88466e4d841",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7468.4165,
        109083.4844,
        25.139799084611578,
        4043
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.0115,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.1,
          "free": true,
          "uncertainty": 0.1
        },
        "_peak.decay_beta_0": {
          "value": 0.006,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.decay_beta_1": {
          "value": 0.015,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 29.8,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 6.0,
          "free": true,
          "uncertainty": 1
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen",
        "_instrument.setup_twotheta_bank": {
          "value": 121.66,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 18660.0,
          "free": true,
          "uncertainty": 1
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -0.47488,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project",
      "experiment": "wish_5_6",
      "sha256": "d08b3b01b671bf5d362da48a3e73442ed91b5f52a69d9ca5955091779c58796e",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7272.2524,
        103417.6719,
        23.33626686893204,
        4121
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.0094,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.1,
          "free": true,
          "uncertainty": 0.1
        },
        "_peak.decay_beta_0": {
          "value": 0.007,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.decay_beta_1": {
          "value": 0.01,
          "free": true,
          "uncertainty": 0.01
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 5.0,
          "free": true,
          "uncertainty": 1
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen",
        "_instrument.setup_twotheta_bank": {
          "value": 152.827,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 20773.0,
          "free": true,
          "uncertainty": 1
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.08308,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project",
      "experiment": "wish_2_9",
      "sha256": "761e2bed99259c0c0e679bdbfa5455671422ea953774f5450ba3edff6bd2200b",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        6075.1914,
        135112.4062,
        30.981324081632653,
        4166
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.040554,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.023869,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.005322,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.083299,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 69.8201,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 23.0513,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 1.6846,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 10.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 58.33,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 10389.9,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85233,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project",
      "experiment": "wish_4_7",
      "sha256": "e63425979da16bed1c0cb0061700d1855a5847fb48e5ce0477bf293284cf204e",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7468.4165,
        109083.4844,
        25.139799084611578,
        4043
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.011598,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.122764,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006428,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.01468,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 29.3563,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 18.1966,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 10.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 121.66,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 18660.1,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -0.47488,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project",
      "experiment": "wish_5_6",
      "sha256": "bb48d4b9c197737a2d35ef406dd3257bbe20dde70a6907bec5d14c8fd2e591a1",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7305.1274,
        103417.6719,
        23.367990396304403,
        4114
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.009502,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.110229,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006672,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.010073,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.701,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0019,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 10.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 152.827,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 20772.9,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.08308,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "experiment": "wish_1_10",
      "sha256": "6893edefb924126beb3817b349dc4f263ff11308172d7cfff70dd9b003b6b67c",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        4862.5732,
        256691.6094,
        60.231771394403246,
        4182
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.014439,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.05507,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.004707,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.137368,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.4063,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 8.2904,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 27.081,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 10
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 4985.32,
          "free": true,
          "uncertainty": 0.1
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85733,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "experiment": "wish_2_9",
      "sha256": "cf1953881302612f1dd7f659ac76026c2f75dfd929f6a846b7c0c822328eef19",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        6075.1914,
        135112.4062,
        30.981324081632653,
        4166
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.040554,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.023869,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.005322,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.083299,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 69.8201,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 23.0513,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 1.6846,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 58.33,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 10
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 10389.9,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85233,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "experiment": "wish_3_8",
      "sha256": "58437073a03edf8861f09c22d0ddc85637268b35e189f76dc430b62068af0bfa",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7549.5366,
        116924.6406,
        27.557345427059712,
        3970
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.012131,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.122897,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.005991,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.027663,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 62.243,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 16.86,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0002,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 10
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 15105.5,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.00785,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "experiment": "wish_4_7",
      "sha256": "5642c0c37de594406461d2b66ef20d09c46e4cd3af26d1f92e4615714179a6ae",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7468.4165,
        109083.4844,
        25.139799084611578,
        4043
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.011598,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.122764,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006428,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.01468,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 29.3563,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 18.1966,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 121.66,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 10
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 18660.1,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -0.47488,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project",
      "experiment": "wish_5_6",
      "sha256": "555792faa1e574fad3b12a810b6aa7dc67abad14977453c97d65a9d0b8826b3b",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7305.1274,
        103417.6719,
        23.367990396304403,
        4114
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.009502,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.110229,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006672,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.010073,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.701,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0019,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 152.827,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 10
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 20772.9,
          "free": true,
          "uncertainty": 1.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.08308,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": 1.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "experiment": "wish_1_10",
      "sha256": "1daf13e94e0fde89c44822d226109b527c2bde097c33b8f20465d6e83ba7b1d5",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        4862.5732,
        256691.6094,
        60.231771394403246,
        4182
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.014439,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.05507,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.004707,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.137368,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.4063,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 8.2904,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 27.081,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 13.51431,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 4986.07373,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85733,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "experiment": "wish_2_9",
      "sha256": "7258aadc1cef7d305d237f7c5e031ee27251f0756159b61ad726cb24bfed435b",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        6075.1914,
        135112.4062,
        30.981324081632653,
        4166
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.040554,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.023869,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.005322,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.083299,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 69.8201,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 23.0513,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 1.6846,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 58.33,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 13.99412,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 10389.88477,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85233,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": -0.004,
          "free": true,
          "uncertainty": 0.0001
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "experiment": "wish_3_8",
      "sha256": "947f6b21e94bdfcf541ef46896b7fed26b91512da0c54084b429b75e24dbc05c",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7549.5366,
        116924.6406,
        27.557345427059712,
        3970
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.012131,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.122897,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.005991,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.027663,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 62.243,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 16.86,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0002,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -12.72588,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 15105.37695,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.00785,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.00109,
          "free": true,
          "uncertainty": 0.0001
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "experiment": "wish_4_7",
      "sha256": "a0afd8a05804802f03de14361fb212c63a3549e61c6e32895fd83ee534312843",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7468.4165,
        109083.4844,
        25.139799084611578,
        4043
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.011598,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.122764,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006428,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.01468,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 29.3563,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 18.1966,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 121.66,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -15.05243,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 18660.06836,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -0.47488,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0043,
          "free": true,
          "uncertainty": 0.0001
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof/project",
      "experiment": "wish_5_6",
      "sha256": "bf45ed7b5f511d26c9d49adf0b13224a87d06245504d377dd5cfe4d4ffadaeb7",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7305.1274,
        103417.6719,
        23.367990396304403,
        4114
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": -0.009502,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.rise_alpha_1": {
          "value": 0.110229,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_0": {
          "value": 0.006672,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.decay_beta_1": {
          "value": 0.010073,
          "free": true,
          "uncertainty": 9.999999999999999e-06
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.701,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0019,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 152.827,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -13.71096,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 20773.01367,
          "free": true,
          "uncertainty": 0.0001
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.08308,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.00956,
          "free": true,
          "uncertainty": 0.0001
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_si-sepd_start-2/project",
      "experiment": "sepd",
      "sha256": "0b1167d3ccd41b2da642e443d5beb606932eea98580cd08364e21e51a4350152",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        2000.0,
        29995.0,
        5.0,
        5600
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.5971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.02,
          "free": true,
          "uncertainty": 0.01
        },
        "_peak.decay_beta_1": {
          "value": 0.005,
          "free": true,
          "uncertainty": 0.001
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.3,
          "free": true,
          "uncertainty": 0.1
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.5,
          "free": true,
          "uncertainty": 0.1
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 5.0,
          "free": true,
          "uncertainty": 0.1
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.2,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 144.845,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": 0.1
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 7476.91,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.54,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {
        "linked_structure": [
          {
            "structure_id": "si",
            "scale": {
              "value": 30.0,
              "free": true,
              "uncertainty": 0.1
            }
          }
        ],
        "background": [
          {
            "id": {
              "value": 1.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 2000.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 2.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 9035.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 3.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 9335.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 4.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 11915.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 5.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 12315.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 6.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 12695.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 7.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 13745.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 8.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 14410.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 9.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 14875.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 10.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 15660.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 11.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 23075.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 12.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 23515.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 13.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 28100.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          },
          {
            "id": {
              "value": 14.0,
              "free": false,
              "uncertainty": 0.0
            },
            "position": {
              "value": 29995.0,
              "free": false,
              "uncertainty": 0.0
            },
            "intensity": {
              "value": 0.0,
              "free": true,
              "uncertainty": 0.1
            }
          }
        ]
      }
    },
    {
      "project": "docs/user/cli/pd-neut-tof_si-sepd_start-5/project",
      "experiment": "sepd",
      "sha256": "4e49721b5e31d508798e5ad56db99fa37ba83bfd324df051776713402deeffc0",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        2000.0,
        29995.0,
        5.0,
        5600
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_diffrn.ambient_temperature": "?",
        "_diffrn.ambient_pressure": "?",
        "_diffrn.ambient_magnetic_field": "?",
        "_diffrn.ambient_electric_field": "?",
        "_calculator.type": "crysta",
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.5971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0408,
          "free": true,
          "uncertainty": 0.0001
        },
        "_peak.decay_beta_1": {
          "value": 0.0123,
          "free": true,
          "uncertainty": 0.0001
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 2.5489,
          "free": true,
          "uncertainty": 0.0001
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 3.0148,
          "free": true,
          "uncertainty": 0.0001
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 33.3451,
          "free": true,
          "uncertainty": 0.0001
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.2,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen-von-dreele",
        "_instrument.setup_twotheta_bank": {
          "value": 144.845,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": -10.0,
          "free": true,
          "uncertainty": 0.1
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 7476.91,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.54,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_lif_single/project",
      "experiment": "cu_ka",
      "sha256": "5b084a1364f4fbe8afc90fa44dc785eb0b674ad2954d8e66dce50e7a0194f9ad",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        10.0,
        160.0,
        0.025,
        6001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.048457,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.083053,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.04,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.049268,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_polarization_coefficient": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 26.5650511771,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 1.5444,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.7,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "tests/fixtures/e04_t1/eta-project",
      "experiment": "experiment",
      "sha256": "ea9233a144911683df0059636a1511c5dc9a38365e066fb177793e2aa0b90664",
      "peakType": "cwl-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        20.25,
        80.25,
        30.0,
        3
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_experiment_type.beam_mode": "constant wavelength",
        "_peak.type": "cwl-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.048457,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.083053,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.04,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_background.type": "line-segment",
        "_instrument.setup_polarization_coefficient": {
          "value": 0.4,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.mixing_eta_0": {
          "value": 0.37,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.mixing_eta_1": {
          "value": 0.0023,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "tests/fixtures/e04_t1/gaussian-project",
      "experiment": "experiment",
      "sha256": "882fae1d1e7511d1ea39e6eec8c68659ad8687fbcfc8ec0497b6559c11740fcb",
      "peakType": "cwl-gaussian",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        20.25,
        80.25,
        30.0,
        3
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_experiment_type.beam_mode": "constant wavelength",
        "_peak.type": "cwl-gaussian",
        "_peak.broad_gauss_u": {
          "value": 0.048457,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.083053,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.04,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_background.type": "line-segment",
        "_instrument.setup_polarization_coefficient": {
          "value": 0.4,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "tests/fixtures/e04_t1/lorentzian-project",
      "experiment": "experiment",
      "sha256": "67d398886934ceda26fc55fa765859ddc0f80d1e673aba8aa38e41c7531e9f27",
      "peakType": "cwl-lorentzian",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        20.25,
        80.25,
        30.0,
        3
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_experiment_type.beam_mode": "constant wavelength",
        "_peak.type": "cwl-lorentzian",
        "_peak.broad_gauss_u": {
          "value": 0.048457,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.083053,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.04,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_background.type": "line-segment",
        "_instrument.setup_polarization_coefficient": {
          "value": 0.4,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_pbso4-lab_round-robin/project",
      "experiment": "pbsox",
      "sha256": "d627c625dad4ae24a482d344cf706c77a94c8cdcbaa531f45ee3acbc988603a9",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        10.0,
        160.0,
        0.025,
        6001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.065374,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.102354,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.047897,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.625,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a0": {
          "value": 0.41356,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": -0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": -1.26777,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": -0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.00363,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_polarization_coefficient": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 26.5650511771,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 1.5444,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "polynomial",
        "_background.origin": {
          "value": 50.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lab6-11b-echidna_basic/project",
      "experiment": "echidna",
      "sha256": "f8fcbd4544ac9fca609567f985863f5fbe380c73c6968f417f54721b4089bde4",
      "peakType": "cwl-tch-pseudo-voigt-fcj",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y",
        "asym_fcj_1",
        "asym_fcj_2"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "calib_sample_displacement",
        "calib_sample_transparency"
      ],
      "range": [
        3.86396,
        163.75638,
        0.04998200062519538,
        3200
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.type": "cwl-tch-pseudo-voigt-fcj",
        "_peak.broad_gauss_u": {
          "value": 0.09,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.05,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_fcj_1": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_fcj_2": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.622,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_displacement": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_transparency": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.7,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "polynomial",
        "_background.origin": {
          "value": 80.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_diamond-dream_mcstas/project",
      "experiment": "dream",
      "sha256": "ee3efe4adef810b92dbb8e2045d5af05258007e781b919ba1fd5f5822a3f00ea",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        8530.1009,
        66503.6911,
        29.001295747873936,
        2000
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen",
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_0": {
          "value": 0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 50000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 5000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 28385.86133,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20/project",
      "experiment": "d20",
      "sha256": "c8d4fdecf1deb36ac5b190425365067c4e71714c071340c7c4cc5e22a2d8f786",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        8.0953,
        150.0953,
        0.10021171489061398,
        1418
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_scan/project",
      "experiment": "d20",
      "sha256": "841aa1a1ca4c6f39c3eb82664ebc9832c47ca4fe53650da29c62a43626b54393",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.0953,
        150.6953,
        0.10006644518272424,
        1506
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_data_source.file_name": "01_001_497p3790.dat",
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.87,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_hs-hrpt/project",
      "experiment": "hrpt",
      "sha256": "c2c754ec57afc404092bd505e22dce51bcc17d91f391b378c7559e969e6cd800",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        3.95,
        164.9,
        0.05,
        3220
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.broad_gauss_u": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 180.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.89,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lbco-hrpt/project",
      "experiment": "hrpt",
      "sha256": "502941566652e6acfff532d1c9a4b5b73e7827a66d22d3fb8903078d2d310286",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        164.85,
        0.049999999999999996,
        3098
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.08,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.08,
          "free": true,
          "uncertainty": null
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.494,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.3,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lbco_simulation/project",
      "experiment": "hrpt",
      "sha256": "21fadf02f63b79f1f18d78e8f0ca2af9cc017a8e429178853f7a8813a484072a",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        160.0,
        0.05,
        3001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_instrument.setup_wavelength": {
          "value": 1.494,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_min": {
          "value": 10.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_max": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_step": {
          "value": 0.05,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lmo-echidna/project",
      "experiment": "echidna",
      "sha256": "56c050bdeb4188c636ef5afbacc5d1d36353690dfb3c2689ae48b85642612d6d",
      "peakType": "cwl-tch-pseudo-voigt-fcj",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y",
        "asym_fcj_1",
        "asym_fcj_2"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "calib_sample_displacement",
        "calib_sample_transparency"
      ],
      "range": [
        4.01383,
        163.9066,
        0.04998211003438574,
        3200
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "cwl-tch-pseudo-voigt-fcj",
        "_peak.broad_gauss_u": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.3,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_fcj_1": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_fcj_2": {
          "value": 0.08,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.6215,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_displacement": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_sample_transparency": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_y2o3-spodi/project",
      "experiment": "spodi",
      "sha256": "54b3966a0f3286aae339911ff388f3280f6552946e312b2ed5258542a565e346",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        0.95,
        153.9,
        0.05,
        3060
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.04,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.07,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54822,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_yalo3-al2o3-spodi/project",
      "experiment": "spodi",
      "sha256": "a0a6cdf5fe6d807a7241f7e68456804c212120119e3bac264293f0c90723fc7c",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        4.05,
        151.95,
        0.04999999999999999,
        2959
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.broad_gauss_u": {
          "value": 0.04,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.05,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 20.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54816,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.0221,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_cecoal-polaris/project",
      "experiment": "polaris",
      "sha256": "f76663b87db3b3356426a1fd3be25a2e26a8b10fd808978897a4bf15b77df789",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        3001.589,
        19004.658,
        4.334525731310943,
        3693
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 4.2,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.2971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.043085,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.002867,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 40.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 5.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 145.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 6176.03076,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.92194,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "chebyshev",
        "_background.x_min": {
          "value": 3001.5891,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.x_max": {
          "value": 19004.6582,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ceo2-pearl/project",
      "experiment": "pearl",
      "sha256": "457cf6771c73209cd11a20b4e9e3aed81f0e14fb3f4f082e20bed9248c8ab0ec",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        1500.25,
        19400.1875,
        7.094703725723345,
        2524
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.3,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_0": {
          "value": 0.03,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.03,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 80.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 4.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 5.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 4680.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.7621,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "polynomial",
        "_background.origin": {
          "value": 7000.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer/project",
      "experiment": "expt_n2",
      "sha256": "3c963915d618f98cf845e8d45b2b5171debc9628fec033e144df231355c913aa",
      "peakType": "tof-pseudo-voigt",
      "mode": "tof",
      "peakFields": [
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        40094.52341631884,
        135592.47482202607,
        31.85388639283096,
        2999
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-pseudo-voigt",
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 900.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 1000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 300.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 5.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 54902.1875,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ferrite-austenite-beer/project",
      "experiment": "expt_s2",
      "sha256": "ec5dcf452a79597dfb7d97c2ff4b3d44100dbba834c5da8b914329d5f21fe792",
      "peakType": "tof-pseudo-voigt",
      "mode": "tof",
      "peakFields": [
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        40094.52341631884,
        135592.47482202607,
        31.85388639283096,
        2999
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-pseudo-voigt",
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 900.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 1000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 300.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 5.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 54902.1875,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment",
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_lbco-si-mcstas/project",
      "experiment": "mcstas",
      "sha256": "6479750462101d7af25eb5f73226347791e788535c1253abb286086e9c97dc0e",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        41168.12859292999,
        146787.37361476864,
        105.72496999183048,
        1000
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen",
        "_peak.broad_gauss_sigma_0": {
          "value": 50000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": -50000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 20000.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_0": {
          "value": 0.006,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.004,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 94.90931761529106,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 58724.76869981215,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "experiment": "wish_1_10",
      "sha256": "24dd6b5278ac7369ad528da944b324e3a5d0472cd2f448c289faeb57ec78bd27",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        4862.5732,
        256691.6094,
        60.231771394403246,
        4182
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 15.4063,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 8.2904,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.004707,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.137368,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.014439,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.05507,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 27.081,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 4985.32,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85733,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "experiment": "wish_2_9",
      "sha256": "cc447addb349b2956750e4e8d4da74e42325acd3be70163c533f2a2b76beca65",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        6075.1914,
        135112.4062,
        30.981324081632653,
        4166
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 34.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 11.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 1.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0061,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.096,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_0": {
          "value": 0.053,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_1": {
          "value": 0.031,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 58.33,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 10389.9,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.85233,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "experiment": "wish_3_8",
      "sha256": "14265d219fe6a6efa50b4b074d33ac8713ad6cb7d3cd7b013f13085cb976857f",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7549.5366,
        116924.6406,
        27.557345427059712,
        3970
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 30.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 8.3,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0002,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0069,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.032,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_0": {
          "value": -0.016,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_1": {
          "value": 0.16,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 90.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 15105.5,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": 1.00785,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "experiment": "wish_4_7",
      "sha256": "a3833fabd3d3c4b59403d5c0d995e7ece5db4e40efcdc208024d1f0fd19c8c5f",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7468.4165,
        109083.4844,
        25.139799084611578,
        4043
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 14.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 8.9,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0074,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.017,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_0": {
          "value": -0.015,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_1": {
          "value": 0.16,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 121.66,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 18660.1,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -0.47488,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish/project",
      "experiment": "wish_5_6",
      "sha256": "2db147368b28fac20b85d9dd62479e73cf6c1c620e3d97c7a65224f34a29836d",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        7305.1274,
        103417.6719,
        23.367990396304403,
        4114
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 7.7,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 0.0019,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.0077,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.012,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_0": {
          "value": -0.012,
          "free": true,
          "uncertainty": null
        },
        "_peak.rise_alpha_1": {
          "value": 0.14,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 152.827,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 20772.9,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.08308,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "cylinder",
        "_absorption.abscor1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.abscor2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_si-sepd/project",
      "experiment": "sepd",
      "sha256": "5720646987f9ce601cfa32532c369d2fb7e5997a7635004b856c1103dde7a6b8",
      "peakType": "tof-jorgensen-von-dreele",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain",
        "broad_lorentz_gamma_0",
        "broad_lorentz_gamma_1",
        "broad_lorentz_gamma_2",
        "broad_lorentz_size",
        "broad_lorentz_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        2000.0,
        29995.0,
        5.0,
        5600
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "tof-jorgensen-von-dreele",
        "_peak.cutoff_fwhm": {
          "value": 8.2,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.5971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.04,
          "free": true,
          "uncertainty": null
        },
        "_peak.decay_beta_1": {
          "value": 0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_0": {
          "value": 3.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 30.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_gamma_1": {
          "value": 3.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_gamma_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_twotheta_bank": {
          "value": 144.845,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 7476.91,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.54,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_reciprocal": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_si_simulation/project",
      "experiment": "sepd",
      "sha256": "93449e1da42b2bdd244727e0d11234a906f950691f431e2e7b9e54323ba8a4f3",
      "peakType": "tof-jorgensen",
      "mode": "tof",
      "peakFields": [
        "rise_alpha_0",
        "rise_alpha_1",
        "decay_beta_0",
        "decay_beta_1",
        "broad_gauss_sigma_0",
        "broad_gauss_sigma_1",
        "broad_gauss_sigma_2",
        "broad_gauss_size",
        "broad_gauss_strain"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_twotheta_bank",
        "calib_d_to_tof_offset",
        "calib_d_to_tof_linear",
        "calib_d_to_tof_quadratic",
        "calib_d_to_tof_reciprocal"
      ],
      "range": [
        5000.0,
        15000.0,
        2.0,
        5001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "time-of-flight",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_instrument.setup_twotheta_bank": {
          "value": 144.845,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_linear": {
          "value": 7476.91,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_d_to_tof_quadratic": {
          "value": -1.54,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "tof-jorgensen",
        "_peak.broad_gauss_sigma_0": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_1": {
          "value": 40.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_sigma_2": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_size": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_strain": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_0": {
          "value": 0.04221,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.decay_beta_1": {
          "value": 0.00946,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_0": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.rise_alpha_1": {
          "value": 0.5971,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 12.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.time_of_flight_min": {
          "value": 5000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.time_of_flight_max": {
          "value": 15000.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.time_of_flight_step": {
          "value": 2.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project",
      "experiment": "d1a",
      "sha256": "26e46ae4ecfc954b05f2f1feba64db526d47c0cfd9f691ace720980331eec35e",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset"
      ],
      "range": [
        10.0,
        155.45,
        0.049999999999999996,
        2910
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "neutron",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.neutron_scattering_length": "sears1992",
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.broad_gauss_u": {
          "value": 0.2,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_limit": {
          "value": 180.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.91,
          "free": true,
          "uncertainty": null
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-xray-cwl_pbso4-d1a-lab/project",
      "experiment": "lab",
      "sha256": "2abea9b19c44ec9b47d096c4091aeb7e6c62682ffcdfe6abffae2180698b50ff",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        10.0,
        160.0,
        0.025,
        6001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.broad_gauss_u": {
          "value": 0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.008,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_limit": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 1.5444,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_polarization_coefficient": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 26.5650511771,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "chebyshev",
        "_background.x_min": {
          "value": 15.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.x_max": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_lam7o3-p021/project",
      "experiment": "p021",
      "sha256": "d166c4fa0b68e1ce01791d070d96bdde27b5ed69f750a5c8bd14a1919647a01b",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        0.0052581048,
        15.337892,
        0.010516209804663924,
        1459
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.04,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.01,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.001,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_x": {
          "value": 0.1,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_lorentz_y": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 30.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 0.207109,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "line-segment",
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_latp-bm01_scan/project",
      "experiment": "bm01",
      "sha256": "b25970da46d7829c717432de06c7d1a7e9f8f914a0b1bfce54d99cfa39809bf3",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        3.67257,
        63.0724,
        0.018785524984187223,
        3163
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "wk1995",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_data_source.file_name": "latp_312.dat",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.019,
          "free": true,
          "uncertainty": 0.009000000000000001
        },
        "_peak.broad_gauss_v": {
          "value": 0.019,
          "free": true,
          "uncertainty": 0.006
        },
        "_peak.broad_gauss_w": {
          "value": 0.0156,
          "free": true,
          "uncertainty": 0.0009000000000000001
        },
        "_peak.mixing_eta_0": {
          "value": 0.374,
          "free": true,
          "uncertainty": 0.016
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.088,
          "free": true,
          "uncertainty": 0.005
        },
        "_peak.asym_beba_b0": {
          "value": 0.0043,
          "free": true,
          "uncertainty": 0.0011
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_limit": {
          "value": 180.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_instrument.setup_wavelength": {
          "value": 0.69687,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.0388,
          "free": true,
          "uncertainty": 0.0014
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment",
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_latp_scan-4f/project",
      "experiment": "bm01",
      "sha256": "b25970da46d7829c717432de06c7d1a7e9f8f914a0b1bfce54d99cfa39809bf3",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        3.67257,
        63.0724,
        0.018785524984187223,
        3163
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "wk1995",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_data_source.file_name": "latp_312.dat",
        "_calculator.type": "crysta",
        "_peak.broad_gauss_u": {
          "value": 0.019,
          "free": true,
          "uncertainty": 0.009000000000000001
        },
        "_peak.broad_gauss_v": {
          "value": 0.019,
          "free": true,
          "uncertainty": 0.006
        },
        "_peak.broad_gauss_w": {
          "value": 0.0156,
          "free": true,
          "uncertainty": 0.0009000000000000001
        },
        "_peak.mixing_eta_0": {
          "value": 0.374,
          "free": true,
          "uncertainty": 0.016
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.088,
          "free": true,
          "uncertainty": 0.005
        },
        "_peak.asym_beba_b0": {
          "value": 0.0043,
          "free": true,
          "uncertainty": 0.0011
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_limit": {
          "value": 180.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 8.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_instrument.setup_wavelength": {
          "value": 0.69687,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": -0.0388,
          "free": true,
          "uncertainty": 0.0014
        },
        "_absorption.type": "cylinder-hewat",
        "_absorption.mu_r": {
          "value": 0.3,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.type": "line-segment",
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_nacl_simulation/project",
      "experiment": "lab",
      "sha256": "219e05053736474497f7a37b2a16f273feef817129aa860ee9289bba4fb9fe8e",
      "peakType": "cwl-tch-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        10.0,
        150.0,
        0.02,
        7001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_instrument.setup_wavelength": {
          "value": 1.5406,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_polarization_coefficient": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 26.5650511771,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.type": "cwl-tch-pseudo-voigt",
        "_peak.broad_gauss_u": {
          "value": 0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_v": {
          "value": -0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_gauss_w": {
          "value": 0.1,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_x": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.broad_lorentz_y": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_min": {
          "value": 10.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_max": {
          "value": 150.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_data_range.two_theta_step": {
          "value": 0.02,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.0,
          "free": false,
          "uncertainty": null
        }
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-xray-cwl_pbso4-lab/project",
      "experiment": "lab",
      "sha256": "ca3f995c61a0af07ffb660b5cef344a87f87ed79c7918704a595538c41662230",
      "peakType": "cwl-pseudo-voigt-berar-baldinozzi",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1",
        "asym_beba_a0",
        "asym_beba_b0",
        "asym_beba_a1",
        "asym_beba_b1",
        "asym_beba_limit"
      ],
      "unusedFreeFields": [],
      "peakDefaults": {},
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta",
        "setup_wavelength_2",
        "setup_wavelength_2_to_1_ratio"
      ],
      "range": [
        10.0,
        160.0,
        0.025,
        6001
      ],
      "scalars": {
        "_edi.schema_version": {
          "value": 3.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_experiment_type.sample_form": "powder",
        "_experiment_type.beam_mode": "constant wavelength",
        "_experiment_type.radiation_probe": "xray",
        "_experiment_type.scattering_type": "bragg",
        "_scattering_source.xray_form_factor": "it1992",
        "_scattering_source.xray_dispersion": "sasaki1989",
        "_peak.type": "cwl-pseudo-voigt-berar-baldinozzi",
        "_peak.broad_gauss_u": {
          "value": 0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_v": {
          "value": -0.02,
          "free": true,
          "uncertainty": null
        },
        "_peak.broad_gauss_w": {
          "value": 0.008,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_0": {
          "value": 0.5,
          "free": true,
          "uncertainty": null
        },
        "_peak.mixing_eta_1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_a0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_b0": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_peak.asym_beba_a1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_b1": {
          "value": 0.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.asym_beba_limit": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_peak.cutoff_fwhm": {
          "value": 48.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength": {
          "value": 1.54056,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2": {
          "value": 1.5444,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_wavelength_2_to_1_ratio": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_polarization_coefficient": {
          "value": 0.5,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 26.5650511771,
          "free": false,
          "uncertainty": 0.0
        },
        "_instrument.calib_twotheta_offset": {
          "value": 0.0,
          "free": true,
          "uncertainty": null
        },
        "_background.type": "chebyshev",
        "_background.x_min": {
          "value": 15.0,
          "free": false,
          "uncertainty": 0.0
        },
        "_background.x_max": {
          "value": 160.0,
          "free": false,
          "uncertainty": 0.0
        }
      },
      "loops": {}
    }
  ],
  "catalogue_ids": [
    "pd-neut-cwl_lbco_simulation",
    "pd-neut-tof_si_simulation",
    "pd-xray-cwl_nacl_simulation",
    "pd-neut-cwl_lbco-hrpt",
    "pd-neut-cwl_hs-hrpt",
    "pd-neut-cwl_cosio-d20",
    "pd-neut-cwl_lmo-echidna",
    "pd-neut-cwl_y2o3-spodi",
    "pd-neut-cwl_yalo3-al2o3-spodi",
    "pd-neut-tof_si-sepd",
    "pd-neut-tof_cecoal-polaris",
    "pd-neut-tof_ceo2-pearl",
    "pd-neut-tof_lbco-si-mcstas",
    "pd-neut-tof_ncaf-wish",
    "pd-neut-tof_ferrite-austenite-beer",
    "pd-xray-cwl_pbso4-lab",
    "pd-xray-cwl_lam7o3-p021",
    "pd-neut-xray-cwl_pbso4-d1a-lab",
    "pd-neut-cwl_cosio-d20_scan",
    "pd-xray-cwl_latp-bm01_scan"
  ]
};
