# Initial prefix-cache diagnostic

The initial implementation allocated three arrays of shape `(fleet + 1, n + 2)`
at every local-search call. It preserved the moves but was usually slower.
The following rounded median timings were captured in the first profiling output;
they are not a second experiment or reconstructed per-repetition raw data.

| Instance | Cached seconds | Full seconds | Full / cached |
|---|---:|---:|---:|
| C1_10_3 | 0.003967 | 0.001972 | 0.497120 |
| C2_10_3 | 0.004238 | 0.002108 | 0.497251 |
| R1_10_3 | 0.008400 | 0.006966 | 0.829274 |
| R2_10_3 | 0.013260 | 0.014179 | 1.069297 |
| RC1_10_3 | 0.004661 | 0.002875 | 0.616765 |
| RC2_10_3 | 0.006013 | 0.004502 | 0.748711 |

The next implementation sizes these arrays to the current longest route and
grows them safely if an exchange creates a longer route. Its full paired raw
measurements are in `fixed_work.csv`.
