# make-queue-inputs

CLI that writes an Obj A workload and a matching multi-queue `qconf.csv`.

The first queue reads `in0.wl`, applies `Sub-X` once, and forwards to the next queue. The last queue uses `Sub-X*` and writes `out_final.wl`.

```text
python make_queue_inputs.py --out-dir runs/auto --queues 2 --interval 0:9 --dist fixed --fixed-work 20
```

`scripts/run-queue.ps1` under `multi-queue-sim` calls this utility and then runs the simulator.
