# pd-xray-cwl_latp_scan-4f — provenance

The owner's LATP project, a constant-wavelength synchrotron X-ray measurement (λ = 0.28457 Å) of
Li1.3Al0.3Ti1.7(PO4)3 with two AlPO4 phases, given to edi on 2026-10-07.

## Sources

| file | origin |
| --- | --- |
| `fullprof/latp.pcr` | the owner's FullProf project after his fit; its header records FullProf's χ² 7.048 |
| `fullprof/s13_150_z20_xrd_sum.dat` | the summed pattern that fit used, as the owner gave it |
| `project/` | the edi project the owner built from `latp.pcr`: its structures, experiment (holding the summed pattern) and analysis, unchanged except for the scan files below |

FullProf ran once, on the owner's machine, when he made `latp.pcr`; no test runs it.

## The scan files

The owner's scan has 8565 files of the same two-column shape (`# Two Theta	Intensity`, then 2θ and intensity); they
are not public. The four files here are made from the summed pattern, keeping its 2θ grid:

```bash
S=fullprof/s13_150_z20_xrd_sum.dat
mk() {  # mk <file> <factor> <leading points made negative>
  { printf '# Two Theta\tIntensity\n'
    awk -v k="$2" -v neg="$3" 'NF==2 {n++; y=$2*k; if (n<=neg) y=-(n%4)-0.5; printf "%s %.5f\n", $1, y}' "$S"; } \
    > project/experiments/latp_scan/"$1"
}
mk pattern_0_0001.txt 1.00 0
mk pattern_0_0002.txt 0.96 0
mk pattern_0_0003.txt 1.04 20
mk pattern_0_0004.txt 0 0
```

## The expected values

- `n_free` (54): the free set FullProf fits in `latp.pcr` (a **reference**).
- The eight `param.*` values: FullProf's, read from `latp.pcr` (**references**), each with a tolerance of two edi
  e.s.d.s of the last fitted file (`pattern_0_0003.txt`).
- `reduced_chi_square` and `iterations`: **regression pins** of this project's own sequential fit, measured by
  `python -m edi fit --report machine` with `OMP_NUM_THREADS=1` on edi `ddb1219` linked against crysta
  `d703cd2c`.
