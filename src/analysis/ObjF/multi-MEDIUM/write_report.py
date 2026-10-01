"""Refresh the measured-results sections from the saved scenario summaries."""

from pathlib import Path
import pandas as pd
import analysis_tools as at
import email_model as model


def write_report():
    """Refresh report results from the complete set of saved scenario summaries."""
    root = model.HERE
    summaries = pd.read_csv(root / "results/summary.csv").set_index("scenario")
    if not set(model.scenarios()).issubset(summaries.index):
        return
    baseline = summaries.loc["base-30k"]
    hot = summaries.loc["hot+20"]
    cold = summaries.loc["cold+20"]
    surge = summaries.loc["load-surge"]
    cut = summaries.loc["srv-30"]
    sorted_route = summaries.loc["routing-sorted"]

    def table(names, columns=None):
        columns = columns or [
            "jobs",
            "total_servers",
            "latency_mean",
            "latency_p90",
            "drop_pct",
            "throughput",
        ]
        return at.markdown(summaries.loc[names, columns].reset_index())

    queue_summary = pd.read_csv(root / "results/base-30k/per-queue.csv").sort_values(
        "mean_waiting", ascending=False
    )
    results_section = f"""<!-- GENERATED RESULTS -->
## 6. Results

These are measured results from one matched workload seed. System dashboard throughput is a completion count per 10-tick window; summary-table throughput is completions per tick over the full run. Decimal places support reproducibility; they do not represent uncertainty bounds. Latency values are ticks, drop percentages use all generated jobs, and throughput is completed requests per tick over the entire run.

### 6.1 Baseline: 30,000 work requests

![Baseline latency and throughput](results/base-30k/resplot.png)

All {int(baseline.completed):,} requests completed, with {int(baseline.dropped):,} drops. Mean latency was **{baseline.latency_mean:.3f} ticks**, median **{baseline.latency_median:.0f}**, and P90 **{baseline.latency_p90:.0f}**. Throughput was **{baseline.throughput:.3f} completed requests/tick**. Mean waiting across a completed journey was {baseline.latency_mean-11:.3f} ticks above the 11-tick no-waiting floor.

The six nodes with highest full-run mean waiting were:

{at.markdown(queue_summary.head(6)[['queue','servers','utilization','mean_waiting','errors','mean_wait','p90_wait','L','lambda_W']])}

Node q{int(queue_summary.iloc[0]['queue'])} had the largest mean waiting queue. It is the strongest local congestion candidate in this run, although the network completed every request. The all-node heatmap and USE panels show why a network-wide average alone would obscure this concentration.

![All-node waiting](results/base-30k/all-queues.png)

### 6.2 Scale: 10k / 30k / 100k requests

![Scale comparison](results/scale-comparison.png)

{table(['scale-10k','base-30k','scale-100k'])}

Mean latency is similar across these runs and P90 is 13 ticks in each. Increasing the job count at fixed arrival intensity mainly lengthens the observation period. Full-run throughput approaches the offered rate as startup and drain become a smaller share. This is evidence of consistent behavior over these finite runs, not a proof of steady-state stability.

### 6.3 Load: the same requests at half and 1.5 times the intensity

![Load comparison](results/load-comparison.png)

{table(['load-quiet','base-30k','load-surge'])}

The quiet case approaches the 11-tick service-and-transfer floor. The surge case has mean latency **{surge.latency_mean:.3f} ticks**, P90 **{surge.latency_p90:.0f}**, and **{int(surge.dropped):,} drops ({surge.drop_pct:.3f}%)**. It processes more requests per tick because demand is greater, but some buffers fill. Thus higher measured throughput does not by itself mean better service.

### 6.4 Sensitivity: −30% through +100% servers

![Server sensitivity](results/sensitivity-servers.png)

{table(['srv-30','srv-20','srv-10','base-30k','srv+25','srv+50','srv+100'],['requested_resource_change_pct','actual_resource_change_pct','total_servers','latency_mean','latency_p90','drop_pct','throughput'])}

At the largest cut, **{int(cut.total_servers):,} servers** produce **{int(cut.dropped):,} drops ({cut.drop_pct:.3f}%)**, mean completion latency **{cut.latency_mean:.3f} ticks**, and throughput **{cut.throughput:.3f}**. The exact node allocations are in the scenario configs; cuts affect a seeded subset of nodes because resources are discrete.

Added servers have limited room to improve the baseline because it already completes all arrivals near the 11-tick floor. They primarily reduce waiting rather than create more demand. The drop column is necessary when interpreting cuts: latency excludes rejected jobs.

### 6.5 Targeted alternatives and routing

![Targeted alternatives](results/targeted-comparison.png)

{table(['base-30k','hot+20','cold+20','depth-50','routing-sorted'])}

Adding 20 servers to the highest-waiting nodes changes mean latency from **{baseline.latency_mean:.3f}** to **{hot.latency_mean:.3f}** ticks. The same 20-server budget at the lowest-waiting nodes gives **{cold.latency_mean:.3f}** ticks. The targeted addition is only **{hot.actual_resource_change_pct:.3f}%** of baseline capacity. These nodes were selected using the baseline itself, so this comparison needs held-out workloads before it supports a general staffing rule.

The depth scenario changes waiting slots, leaving service capacity unchanged. Read its latency and drop percentage together. Sorted-neighbor routing gives **{sorted_route.latency_mean:.3f} ticks** mean latency and **{sorted_route.drop_pct:.3f}%** drops. It preserves the same graph and long-run equal-neighbor routing policy, but changes transient handoff order. This comparison demonstrates why initialization choices belong in the model description.

## 7. Does this make sense for the real problem?

Within the stated hypothetical workflow, yes: concentrated incoming handoffs create local waiting; more demand can fill finite inboxes; capacity at already-idle nodes contributes little; and more servers cannot eliminate the fixed work and transfer time.

The model does not include priorities, worker skills, deadlines, correlated tasks, retries, or time-varying staffing. Four identical contributions simplify real workflows considerably. An observed email edge only demonstrates past communication; it does not prove that either colleague can process every request. Uniform external origins and deterministic equal routing are assumptions. No real-world operational recommendation or wall-clock forecast follows directly from these synthetic numbers.

The workload seed is shared across scenarios. Arrival times, source assignments and processing requirements are matched, but changing capacity can change which job receives the next round-robin edge. Therefore exact job routes need not stay identical between server scenarios. No confidence intervals are claimed from this one-seed comparison.

## 8. Takeaways

1. **Inspect individual queues.** Network-average spare capacity can coexist with localized waiting.
2. **Distinguish scale from load.** More requests at the same rate lengthen a run; faster arrivals stress capacity.
3. **Place resources where waiting occurs.** Compare the same extra-server budget at busy and quiet nodes before assuming a uniform increase is efficient.
4. **Report drops beside latency.** A request that overflows an inbox disappears from completion latency but remains an unmet request.
5. **Respect the 11-tick floor.** Once waiting is small, shorter processing or fewer handoffs are the remaining latency levers in this model.
6. **Validate routing assumptions.** A harmless-looking neighbor order can change finite-run congestion even with identical graph edges.
7. **Validate job accounting.** Finished simulations alone are insufficient; drops, transit, completion sinks and queue-time integrals must agree.

## 9. Artifacts, validation, and reproduction

```text
multi-MEDIUM/
  README.md               this SMALL-style report
  email_model.py         observed graph, synthetic model, scenario/config writers
  analysis_tools.py      model validation, queue summaries, USE and heatmap
  implementation_tools.py  calls shared Objective A/C/E scripts and checks outputs
  run_analysis.py        build -> smoke checks -> simulate -> analyze -> compare
  write_report.py        refresh measured results from summary CSVs
  requirements.txt       Python dependencies
  data/                  original SNAP edge list
  workloads/             simulator input streams, shared by matching scenarios
  configs/               per-scenario simulator CSVs
  results/               per-scenario dashboards and cross-scenario comparisons
  runs/                  compressed raw outputs, derived metrics and sink archives
```

The SNAP edge list is included. If it is missing, the driver downloads it and verifies its checksum.

From this directory:

```sh
python3 -m pip install -r requirements.txt
python3 run_analysis.py --list
python3 run_analysis.py
python3 run_analysis.py --scenarios base-30k,srv+50
python3 run_analysis.py --scenarios base-30k --skip-sim
python3 write_report.py
```

Requires a C++17 compiler named `c++`. The driver builds the repository's existing simulator into the temporary directory. It raises the Unix file-descriptor limit when available so 803 sources and sinks can be open together. Workload/config paths are relative to this directory, and the driver sets that working directory automatically. Normal reruns overwrite generated files; `--skip-sim` compares the saved config and workload files with the current model before reusing the raw run. Run without Python's `-O` because validation uses assertions.

Run `base-30k` before targeted `hot+20`/`cold+20` if starting without results. Compressed raw logs are `events.log.gz` and `qmet.csv.gz`; completion files are in `sinks.tar.gz`. The driver temporarily restores these files when revalidating. All artifacts are retained within this analysis directory, and its `.gitignore` overrides the repository's blanket exclusion of `runs/`.

### Validation

Checks run in memory and stop the pipeline if they fail; no verification JSON or tool logs are written. Smoke checks use a temporary directory that is removed afterward. The driver first checks a known three-node route with one job (four visits, 11 ticks), then a deliberate overflow (100 simultaneous arrivals; 33 complete and 67 are rejected). It checks graph integrity, every routing choice, every transfer delay, sink contents, four visits per completed job, service duration, queue/server bounds, full drain, and exact job conservation.

Per-node integrated waiting/service counters equal independently reconstructed event durations. Full-run `L` equals visit throughput times mean turnaround. At network level, occupancy includes transit, and the lifetime sum includes both completed and dropped requests. This avoids applying completion-only Little's law to a loss system. Source checksum and graph integrity are checked in `email_model.graph()`. The model preserves matched workload prefixes and checks server allocations when it runs.

### Accessory-tool coverage

| Capability | Implementation and saved demonstration |
|---|---|
| Workload creation and visualization | Model-specific generation; Objective A `workload_visualizer.py` produces `workload.png` and `workload-scatter.png` |
| Config from real network | `email_model.graph`, `routing`, `write_inputs`; 803-node configs |
| Multi-queue simulation | Existing Obj B C++ engine; raw events, queue metrics, sinks |
| Derive system metrics | Objective C `derive_sys_metrics.py`; `sysmetrics.csv` contains latency percentiles and completion counts per window |
| Plot system metrics | Objective C `plot_sys_metrics.py`; `resplot.png` in every scenario |
| Derive visit metrics | Objective C `derive_event_metrics.py`; `emetrics.csv.gz`, cross-checked against independent validation |
| Model job accounting | Local `derive_and_validate`; `jobs.csv.gz` tracks completed and dropped lifetimes |
| Plot visit histograms/scatter | Objective C `plot_derive_event_metrics.py`; three baseline `emetrics-*.png` plots |
| Filter by queue | Objective C `filter_by_queue.py`; `filtered-queue.csv` |
| Filter by job | Objective C `filter_by_job.py`; `trace-jobs.log` |
| Compute USE | Local helper (no shared implementation yet); all-node `quse.csv.gz`, windows 10/100/1,000; partial startup windows |
| Plot USE | Local helper (no shared implementation yet); three per-scenario top-12 panels; baseline all-node waiting heatmap |
| Create event trace | Objective C `create_event_trace.py`; `etrace.png` for the filtered jobs |
| Pretty-print events | Objective E `pretty_print_events.py`; `pretty-events.txt` with one column per queue |

`implementation_tools.py` invokes the shared scripts under `src/implementation/` as command-line tools. Failed commands report their diagnostics in the terminal. Intermediate plot inputs are temporary files and are removed after plotting. Compressed event logs are expanded in a temporary directory because the shared event CLIs read plain text. Shared visit metrics must exactly match the independent model reconstruction; system percentiles are checked within 0.0051 ticks because the shared CLI writes two decimal places. Filters are checked against the original rows and event lines. USE, model-specific validation, queue summaries, and cross-scenario comparisons remain local.

The location remains `src/analysis/ObjF/multi-MEDIUM/`, matching the directory already created on this branch. The assignment quote specifies `./analysis/multi-MEDIUM/`; reconcile that literal path before final submission. Further work could repeat the study with independent seeds and evaluate targeted allocations on held-out workloads.
"""
    report_path = root / "README.md"
    intro = report_path.read_text().split("<!-- GENERATED RESULTS -->")[0]
    report_path.write_text(intro + results_section)


if __name__ == "__main__":
    write_report()
