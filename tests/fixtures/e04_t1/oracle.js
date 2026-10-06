// Independent category oracle. Regenerate only with generate.py.
var frozen = {
  "source": "diffraction-lib 0ffba46f declarations +  §2b D-a..D-j + CLI files",
  "profiles": {
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
      "calib_twotheta_offset"
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
        "_metadata.title": " graded start s1 of refine-cosio-d20",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "87d25fc29d7193ca138b24714a0afeafd7551daee12ba60919b4d097e72b2269",
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
        "_metadata.title": " graded start s4 of refine-cosio-d20",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "af9f1f2177a007e7979e8ef30ae768972acfe1849b1e4b8c452f3f5c3e44c216",
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
        "_metadata.title": "Co2SiO4 D20 three-temperature sequential scan",
        "_metadata.description": " corpus project",
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
        "_verbosity.fit": "short"
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
      "loaderWarning": "Warning: unsupported _minimizer.type \"crysta (lm)\" - using crysta",
      "files": {
        "project.edi": "d230f1049d75c2b5b01c2b848e4d9287086c69ddf191d3881fccf0e1a38064df",
        "structures/cosio.edi": "1b3afde2d3a8184d6cb9789fa3fc8fa5dd026756a51e44a2cca6b80b9df8103a",
        "experiments/d20.edi": "0c97d871957341359beee76e7029f77d1bf0ed4eb8e4709733fe794fe3516a1c",
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
        "_metadata.title": "Co2SiO4 D20 cooling scan, 162 files",
        "_metadata.description": "The cooling run of the D20 scan, 497.4 K down to 50.4 K",
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
        "_verbosity.fit": "short"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "873fda837296755c4b0586a54c1b3a838044393f2136bb45e3f69a6e7b3d5bdf",
        "structures/cosio.edi": "4538c66b979d5783c2c3b5ba8c06494a54efeea3fc83c5488e89d5a10c0bb899",
        "experiments/d20.edi": "7053aa291373fc6df17e3d2ced5008a098ef314f65e06a1204f6d0ecbb1ae518",
        "analysis/analysis.edi": "b732d6abb6017d11a7f25d30349975e45b2ba72a25cf13f8c702376ea4d6bbf9"
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
        "_metadata.title": "Co2SiO4 D20 three-temperature sequential scan",
        "_metadata.description": " corpus project",
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
        "_verbosity.fit": "short"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "90b4453599694b4beb76074b1b1f9b2944e36b551345d6ba1b1b1e72e2b2bc1a",
        "structures/cosio.edi": "4538c66b979d5783c2c3b5ba8c06494a54efeea3fc83c5488e89d5a10c0bb899",
        "experiments/d20.edi": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
        "analysis/analysis.edi": "b732d6abb6017d11a7f25d30349975e45b2ba72a25cf13f8c702376ea4d6bbf9"
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
        "_metadata.title": " graded start s2 of refine-lbco-hrpt",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "8d04523f74e1d78a1ef9948f97a84c2bddc4bced0c6b18771c1cf2298bb0263f",
        "structures/lbco.edi": "1c8421e95c44cad8dce012f78e57ed2bcabd783c76443eddf0d5d16873cba5c3",
        "experiments/hrpt.edi": "5063e9ea674694f4ba201a2b7f77b985ae7a8c74111091912f6f9999e15ee2df",
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
        "_metadata.title": " graded start s4 of refine-lbco-hrpt",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "0f1ffd2f044fec55a27dc56a158827d246506e7cdceab58912c0431fe568f5c8",
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
        "_metadata.title": " graded start s3 of refine-ncaf-wish-2bank",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "47ff67e67248bd33c3924c458f8f973f902451c1b36c3a0257b6719d7b9ccb79",
        "structures/ncaf.edi": "f61f4922cf075908b47b4fd3b14c32f7aefef8e339d6161a5fece184396f865b",
        "experiments/wish_4_7.edi": "15a16d72f02eb93f4aa0eda13b5cfb77a05c2abcee6689821caba5b47f37636d",
        "experiments/wish_5_6.edi": "936b75830a0eb724abc277846c574328b303f95568fa74b067bfc812b3224bfc",
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
        "_metadata.title": " 3-bank NCAF WISH joint fit, FullProf-verified",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "b0b564c63fa39e8369bd89bfba31e0288e5fd6bfb9ec737c537d7b0054c73e96",
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
        "_metadata.title": "5-bank NCAF WISH joint fit, free set and exclusions of FullProf tmpl_five_banks_p1.pcr",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "95a8dc39779c96a985966891e022ae4e4b01cfc96057dbfa7414b2d873ec3e3a",
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
        "_metadata.title": "5-bank NCAF WISH joint fit, every value from FullProf tmpl_five_banks_p1.pcr",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "d305abe73a4c83fdefaed9cfe71f0d0739853328190d81cf6ac2f77252dfa136",
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
        "_metadata.title": " graded start s2 of refine-si-sepd",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "8e7e658dd7a5db4a3015299487b181f6641a229fd99dfaae88797a74e547db20",
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
        "_metadata.title": " graded start s5 of refine-si-sepd",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "3ccc4026ad79bb21bba46cb9f323175515950d9d70736e3b8ca617963da7f886",
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
        "_metadata.title": "Diamond, DREAM (ESS) McStas-simulated TOF data",
        "_metadata.description": "?",
        "_metadata.created": "24 Sep 2026 18:42:48",
        "_metadata.last_modified": "24 Sep 2026 18:42:49",
        "_metadata.timestamp": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "b1cbe30308b98db16513d2927910cd116b4d777ccbc922f4621b0a3c6ae1c5ab",
        "structures/diamond.edi": "57650796c81a5963ee142a26847f89d9dac23cb6bc018406c77c6141a68f2613",
        "experiments/dream.edi": "8fd1f452e2d02e32dddef6ef8cfedd101d954092f99a2e302b203d46868c0a9c",
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
        "_metadata.title": "LaB6, Echidna (ANSTO), FCJ asymmetry",
        "_metadata.description": "?",
        "_metadata.created": "26 Sep 2026 10:29:37",
        "_metadata.last_modified": "26 Sep 2026 10:29:38",
        "_metadata.timestamp": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "bfef00c92dddfb3e04cecc03e50c63c8dd7dcb18080365fe04062641d805e1db",
        "structures/lab6.edi": "ae52d392119f81a94e77ba4128ee2afc447fbcd3bdd9cdc6e2fea56eba54074d",
        "experiments/echidna.edi": "133539d1a5bfb8611e3afbe487b7397f817aeb79e65376929ea4681cd91fdb2e",
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
        "_metadata.title": "PbSO4, D1A (ILL), Berar-Baldinozzi asymmetry",
        "_metadata.description": "?",
        "_metadata.created": "26 Sep 2026 10:28:28",
        "_metadata.last_modified": "26 Sep 2026 10:28:29",
        "_metadata.timestamp": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "7dc0e51c1ed6782a661c0f2223d1ee751cd09aaed4fc86f00a2f9bf94cc60dc1",
        "structures/pbso4.edi": "d14b19ea6dc7f6f3a129fa5fb3538f7413fc3cb727950c2f70fb9e2e6e3f2520",
        "experiments/d1a.edi": "f02575053ccb68d9047209eada95ef0042fc632ffdef67024c5bd1198d5a8ddb",
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
        "_metadata.title": "YAlO3 and Al2O3, SPODI (FRM II), two phases"
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
        }
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
      "loaderWarning": "Warning: structures[Al2O3].atom_sites[Al1].adp_iso = -0.13591 is outside its admissible range [0, 10]; loaded as saved (a fit may leave a value there)",
      "files": {
        "project.edi": "20ac0d91bda14553a8c7b18ad5af5bca90557b10c20b068227dbe783685631ae",
        "structures/Al2O3.edi": "f5d727bf0362dae6abfb4c2503669e83085bc897cbb09db913b359eb37999472",
        "structures/YAlO3.edi": "7a4c6c27b6314bca5d179350c2ee75e1e27565a6c59629c17ed11662e29a2ccb",
        "experiments/spodi.edi": "f89b143912601bef9a62b3f61c6ff25c6988759785333e7186244c130b3d5e62",
        "analysis/analysis.edi": "77ef8e7ab8edb6b3f1addcde5a59c0c3b0f8e7cba8e0a4f116b30b4792210066"
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
        "_metadata.title": "Fe (ferrite), BEER (ESS), TOF pseudo-Voigt",
        "_metadata.description": "?",
        "_metadata.created": "26 Sep 2026 10:28:28",
        "_metadata.last_modified": "26 Sep 2026 10:28:29",
        "_metadata.timestamp": "?",
        "_rendering_plot.type": "plotly"
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
      "loaderWarning": "Warning: unsupported _calculator.type \"cryspy\" - using crysta\nWarning: unsupported _minimizer.type \"bumps (lm)\" - using crysta\nWarning: unsupported _rendering_plot.type \"plotly\" - using auto",
      "files": {
        "project.edi": "983169b6363c73f9aedd28527282043c545f532443849b42a3c9f478074aa9df",
        "structures/fe.edi": "9ee23e6fff7c5eb544677380a5c3176ee7425e3e790cbe7b50dca77472a16c29",
        "experiments/beer.edi": "21dcae63234608537b5d9f17a25e2d0554978df3f39d8476660a382e965739dd",
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
        "_metadata.title": "CeCoAl3, POLARIS (ISIS), Chebyshev background",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "061021e84b5f917bc48b283c88f624277c87242c04d42a6034169d0cc7092a0f",
        "structures/cecoal.edi": "f6939b1d7fe11a4b7e8451ec9a4acb468c21522ef4a29af3995b86758e910616",
        "experiments/polaris.edi": "afce3099188fcfab304513b8aaae8cf32cffc4f9c3177df8b7f3dbbd5b87adf0",
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
        "_metadata.title": "CeO2, PEARL (ISIS), polynomial background",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "3ae471fd97bb60f4876bffef1a05a9df3ac28556f5f2183088b01c68127e9fec",
        "structures/ceo2.edi": "aedac6b487103b77e50f106e073b5701214efed16a787a9832391ce2c3b4b79c",
        "experiments/pearl.edi": "a0ecad005d7d2b5729a2822b8cda98b8bfffae586361491dcbc5f8454ca69dd6",
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
        "_metadata.title": "LaB6 (11B), ECHIDNA (ANSTO), TCH x FCJ, polynomial background",
        "_metadata.description": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "0f0754b37ba56b1ce05b6a5e4e545f91f5ef8b78b9b6d840fe01daefb9d6f839",
        "structures/lab6.edi": "06d8ee9eadd4dd9c5f72aed4f264446172a15f81a0571e4a02adfba6156a53fd",
        "experiments/echidna.edi": "6c9fc1b2b342f03c4b15ed7fb41f6afe9f9029ec1b3f05eaa6348e526d70c72e",
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
        "_metadata.title": "LiF, Cu K-alpha1 X-ray, polarization against FullProf",
        "_metadata.description": "?",
        "_metadata.created": "02 Oct 2026 14:28:55",
        "_metadata.last_modified": "02 Oct 2026 14:28:56",
        "_metadata.timestamp": "?"
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
      "loaderWarning": "",
      "files": {
        "project.edi": "efa38eadd5af94f919ccb2c5ba29cd7f775bd5bf01954ac6e5d87fdfa5958866",
        "structures/lif.edi": "b68e864053c85ea3bb0e7a14b37131c7319cd2cd047b89d4dc4d8b30ff4033fe",
        "experiments/cu_ka.edi": "5be14a0525ce8a09124e9f1beaa52fc12f3b49d9bf8201f19b6ac2c68948de5b",
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
        "_metadata.title": "Ferrite and austenite, BEER (ESS, McStas), two phases in two banks"
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
      "loaderWarning": "Warning: unsupported _calculator.type \"cryspy\" - using crysta\nWarning: unsupported _minimizer.type \"lmfit (leastsq)\" - using crysta",
      "files": {
        "project.edi": "d190c5040e2190f0e76c223373752abd50eaf6302d266a7237df6a019c1c3c9e",
        "structures/austenite.edi": "6b3eb1dab5b142687ed34263f04986ab3474bedfcaf9ce0d0ee7831f69929c93",
        "structures/ferrite.edi": "500fcf2007cefefb4b4477e10006596520d8e1cb8e61945d0791ff14ef27521c",
        "experiments/expt_n2.edi": "6e8f4ac836219d4ba503ff5583823b1d12eb523f788e16c03d86b2b5d2bacdda",
        "experiments/expt_s2.edi": "948b6f720ed6d72a5d5f0c5b8b06cae3dca6159f4f9e6edd56739110a2f2290a",
        "analysis/analysis.edi": "e228e179bbb95062d1646300ac68b92cbc0692d9b34a436ed944ef97cdd3df07"
      }
    }
  ],
  "corpus": [
    {
      "project": "docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project",
      "experiment": "d20",
      "sha256": "7053aa291373fc6df17e3d2ced5008a098ef314f65e06a1204f6d0ecbb1ae518",
      "peakType": "cwl-pseudo-voigt",
      "mode": "cwl",
      "peakFields": [
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "mixing_eta_0",
        "mixing_eta_1"
      ],
      "unusedFreeFields": [
        "broad_lorentz_y"
      ],
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
        "_peak.type": "cwl-pseudo-voigt",
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
      "sha256": "0c97d871957341359beee76e7029f77d1bf0ed4eb8e4709733fe794fe3516a1c",
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
      "sha256": "6c9fc1b2b342f03c4b15ed7fb41f6afe9f9029ec1b3f05eaa6348e526d70c72e",
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
      "sha256": "133539d1a5bfb8611e3afbe487b7397f817aeb79e65376929ea4681cd91fdb2e",
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
        "_experiment_type.beam_mode": "constant wavelength",
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
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project",
      "experiment": "hrpt",
      "sha256": "5063e9ea674694f4ba201a2b7f77b985ae7a8c74111091912f6f9999e15ee2df",
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
      "sha256": "f02575053ccb68d9047209eada95ef0042fc632ffdef67024c5bd1198d5a8ddb",
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
        "_experiment_type.beam_mode": "constant wavelength",
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
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-cwl_yap-spodi_3k/project",
      "experiment": "spodi",
      "sha256": "f89b143912601bef9a62b3f61c6ff25c6988759785333e7186244c130b3d5e62",
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
        "_experiment_type.beam_mode": "constant wavelength",
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
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_cecoal-polaris_chebyshev/project",
      "experiment": "polaris",
      "sha256": "afce3099188fcfab304513b8aaae8cf32cffc4f9c3177df8b7f3dbbd5b87adf0",
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
      "sha256": "a0ecad005d7d2b5729a2822b8cda98b8bfffae586361491dcbc5f8454ca69dd6",
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
      "sha256": "8fd1f452e2d02e32dddef6ef8cfedd101d954092f99a2e302b203d46868c0a9c",
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
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_fe_pseudo-voigt/project",
      "experiment": "beer",
      "sha256": "21dcae63234608537b5d9f17a25e2d0554978df3f39d8476660a382e965739dd",
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
        "_background.type": "line-segment"
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
        "_background.type": "line-segment"
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
        "_background.type": "line-segment"
      },
      "loops": {}
    },
    {
      "project": "docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project",
      "experiment": "wish_4_7",
      "sha256": "15a16d72f02eb93f4aa0eda13b5cfb77a05c2abcee6689821caba5b47f37636d",
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
      "sha256": "936b75830a0eb724abc277846c574328b303f95568fa74b067bfc812b3224bfc",
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
      "sha256": "5be14a0525ce8a09124e9f1beaa52fc12f3b49d9bf8201f19b6ac2c68948de5b",
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
      "instrumentFields": [
        "setup_wavelength",
        "calib_twotheta_offset",
        "setup_polarization_coefficient",
        "setup_monochromator_twotheta"
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
          "value": 0.4,
          "free": true,
          "uncertainty": null
        },
        "_instrument.setup_monochromator_twotheta": {
          "value": 20.0,
          "free": true,
          "uncertainty": null
        },
        "_absorption.type": "none",
        "_background.type": "line-segment"
      },
      "loops": {}
    }
  ]
};
