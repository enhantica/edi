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
      "datasets": [],
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
      "datasets": [],
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
        "project.edi": "873fda837296755c4b0586a54c1b3a838044393f2136bb45e3f69a6e7b3d5bdf",
        "structures/cosio.edi": "4538c66b979d5783c2c3b5ba8c06494a54efeea3fc83c5488e89d5a10c0bb899",
        "experiments/d20.edi": "53ba4c8c28755334c633f23040fa411149d66294dc102862918ff461b09eca73",
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
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
      "datasets": [],
      "loaderWarning": "Warning: unsupported _calculator.type \"cryspy\" - using crysta\nWarning: unsupported _minimizer.type \"lmfit (leastsq)\" - using crysta",
      "files": {
        "project.edi": "d190c5040e2190f0e76c223373752abd50eaf6302d266a7237df6a019c1c3c9e",
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
        "_metadata.title": "Y2O3, beta ADPs, scale against FullProf",
        "_metadata.description": "?",
        "_metadata.created": "06 Oct 2026 16:43:16",
        "_metadata.last_modified": "06 Oct 2026 16:43:17",
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
        "project.edi": "539e990301b80e0b83d75d930100d367c10d60aa79458fbe0dd678753e5aa95c",
        "structures/y2o3.edi": "dcacdbe2ddd6490b390aa7b4b36eeaf7e09d43b62f6b31b25a52121ffa295382",
        "experiments/y2o3.edi": "f848804c0238d76eb03f43f2a06688f52cf87d1caa8f38dbcf29e0402e755e1d",
        "analysis/analysis.edi": "64a5254af5f390f3c3a49e84affc9bd4a6a074d2fe50ea5f97e5864c444c7f71"
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
      "project": "docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project",
      "experiment": "y2o3",
      "sha256": "f848804c0238d76eb03f43f2a06688f52cf87d1caa8f38dbcf29e0402e755e1d",
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
      "peakDefaults": {
        "mixing_eta_0": {
          "value": 0.0,
          "free": false
        },
        "mixing_eta_1": {
          "value": 0.0,
          "free": false
        }
      },
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
        "_experiment_type.beam_mode": "constant wavelength",
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
        "_peak.type": "cwl-pseudo-voigt",
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
      "peakDefaults": {},
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
    },
    {
      "project": "tests/fixtures/e04_t1/eta-project",
      "experiment": "experiment",
      "sha256": "a94c5639ffca3c53fd3d6db38eacda16568759cc78dcc4c79df5ccbcde636a35",
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
        "setup_monochromator_twotheta"
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
        }
      },
      "loops": {}
    },
    {
      "project": "tests/fixtures/e04_t1/gaussian-project",
      "experiment": "experiment",
      "sha256": "32bfd9823e869dc1a0ba8b4130cda3f5fb43c18b26e34fdca3330a6a3d693fea",
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
        "setup_monochromator_twotheta"
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
        }
      },
      "loops": {}
    },
    {
      "project": "tests/fixtures/e04_t1/lorentzian-project",
      "experiment": "experiment",
      "sha256": "ef0df1539dcbfde3dd7f9db110433f11823e77092b43937f55ea651a5685aed2",
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
        "setup_monochromator_twotheta"
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
        }
      },
      "loops": {}
    }
  ]
};
