| id | station | group | servers | function | rate (steps) | waiting cap | routes to (slots) |
|---|---|---|---|---|---|---|---|
| q0 | registration | intake | 3 clerks | `Sub-1` | 1 | 15 | q1:1 |
| q1 | triage | intake | 3 nurses | `Sub-1` | 1 | 10 | q2:4, q3:2, q4:2, q5:1, q6:1, q7:1 |
| q2 | fast_track | treatment | 2 providers | `Sub-3*` | 1 | 8 | q9:1 |
| q3 | pod_a | treatment | 3 beds | `Sub-2*` | 2 | 3 | q8:1 |
| q4 | pod_b | treatment | 3 beds | `Sub-2*` | 2 | 3 | q8:1 |
| q5 | lab | diagnostics | 1 analyzers | `Sub-1` | 4 | 10 | q3:1, q4:1 |
| q6 | xray | diagnostics | 1 machines | `Sub-1` | 2 | 5 | q3:1, q4:1 |
| q7 | ct | diagnostics | 1 scanners | `Sub-1` | 3 | 5 | q3:1, q4:1 |
| q8 | disposition | exit | 2 physicians | `Sub-1` | 1 | 10 | q9:4, q10:1 |
| q9 | discharge | exit | 3 nurses | `Sub-3*` | 1 | 10 | sink `out_discharge.wl` |
| q10 | admit | exit | 2 boarding beds | `Sub-3*` | 6 | 3 | sink `out_admit.wl` |
