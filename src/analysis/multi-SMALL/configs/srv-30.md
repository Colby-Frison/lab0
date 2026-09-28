| id | station | group | servers | function | rate (steps) | waiting cap | routes to (slots) |
|---|---|---|---|---|---|---|---|
| q0 | registration | intake | 2 clerks | `Sub-1` | 1 | 30 | q1:1 |
| q1 | triage | intake | 2 nurses | `Sub-1` | 1 | 20 | q2:4, q3:2, q4:2, q5:1, q6:1, q7:1 |
| q2 | fast_track | treatment | 2 providers | `Sub-3*` | 1 | 15 | q9:1 |
| q3 | pod_a | treatment | 2 beds | `Sub-2*` | 2 | 6 | q8:1 |
| q4 | pod_b | treatment | 2 beds | `Sub-2*` | 2 | 6 | q8:1 |
| q5 | lab | diagnostics | 1 analyzers | `Sub-1` | 4 | 20 | q3:1, q4:1 |
| q6 | xray | diagnostics | 1 machines | `Sub-1` | 2 | 10 | q3:1, q4:1 |
| q7 | ct | diagnostics | 1 scanners | `Sub-1` | 3 | 10 | q3:1, q4:1 |
| q8 | disposition | exit | 1 physicians | `Sub-1` | 1 | 20 | q9:4, q10:1 |
| q9 | discharge | exit | 2 nurses | `Sub-3*` | 1 | 20 | sink `out_discharge.wl` |
| q10 | admit | exit | 1 boarding beds | `Sub-3*` | 6 | 6 | sink `out_admit.wl` |
