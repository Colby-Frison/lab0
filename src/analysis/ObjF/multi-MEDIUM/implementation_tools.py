"""Call the shared Objective A/C/E scripts from the MEDIUM study.

Only file conversion, scenario selection, and independent cross-checks live here.
The shared scripts own metric derivation, filtering, and their associated plots.
"""

import gzip
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
IMPLEMENTATION = HERE.parents[3] / "src/implementation"
TOOLS = {
    "derive-system": "obj-c/derive-sys-metrics/derive_sys_metrics.py",
    "plot-system": "obj-c/plot-sys-metrics/plot_sys_metrics.py",
    "derive-visits": "obj-c/derive-event-metrics/derive_event_metrics.py",
    "plot-visits": "obj-c/plot-derive-event-metrics/plot_derive_event_metrics.py",
    "filter-jobs": "obj-c/filter-by-job/filter_by_job.py",
    "filter-queues": "obj-c/filter-by-queue/filter_by_queue.py",
    "trace": "obj-c/create-event-trace/create_event_trace.py",
    "pretty-print": "obj-e/pretty-print-events/pretty_print_events.py",
    "workload-plot": "obj-a/workload-visualizer/workload_visualizer.py",
}


def run_tool(name, arguments):
    """Run a repository CLI; show diagnostics only if it fails."""
    script = IMPLEMENTATION / TOOLS[name]
    command = [sys.executable, str(script), *map(str, arguments)]
    process = subprocess.run(command, cwd=HERE, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(f"{name} failed:\n{process.stdout}{process.stderr}")


def check_visit_metrics(actual, visits):
    """Compare the shared CSV with the model's independent event reconstruction."""
    expected = visits.rename(
        columns={
            "job": "Job-id",
            "queue": "Queue-sys-id",
            "arrival": "arrival-time",
            "wait": "time-in-queue",
            "service": "time-in-service",
        }
    ).copy()
    expected["Queue-sys-id"] = "q" + expected["Queue-sys-id"].astype(str)
    expected["response-time"] = expected["time-in-queue"]
    expected["turnaround-time"] = (
        expected["time-in-queue"] + expected["time-in-service"]
    )
    pd.testing.assert_frame_equal(
        actual.reset_index(drop=True),
        expected[actual.columns].reset_index(drop=True),
        check_dtype=False,
    )


def check_system_metrics(actual, completed, horizon):
    """Check window counts and percentiles, allowing the CLI's two-decimal rounding."""
    window_starts = np.arange(0, horizon, 10)
    assert np.array_equal(actual["time-step"], window_starts)
    groups = completed.groupby((completed.departure // 10) * 10).latency
    expected = groups.agg(
        mean="mean",
        median="median",
        p10=lambda values: values.quantile(0.1),
        p90=lambda values: values.quantile(0.9),
        count="size",
    ).reindex(window_starts)
    assert np.array_equal(actual.throughput, expected["count"].fillna(0))
    for column, expected_column in [
        ("Avg-response-time", "mean"),
        ("median-response-time", "median"),
        ("10-response-time", "p10"),
        ("90-response-time", "p90"),
    ]:
        np.testing.assert_allclose(
            actual[column],
            expected[expected_column],
            atol=0.0051,
            rtol=0,
            equal_nan=True,
        )


def create_outputs(
    scenario,
    run_dir,
    result_dir,
    events,
    visits,
    job_metrics,
    queue_metrics,
    jobs,
    busiest_nodes,
):
    """Produce shared-tool artifacts and check them against the validated run."""
    completed = job_metrics[job_metrics.status == "completed"]
    horizon = int(queue_metrics["time-step"].max()) + 1

    # The event CLIs use ordinary text files. Expand gzip only for this invocation.
    with tempfile.TemporaryDirectory(prefix="objf-shared-tools-") as temporary:
        temporary_dir = Path(temporary)
        plain_events = events
        if events.suffix == ".gz":
            plain_events = temporary_dir / "events.log"
            with gzip.open(events, "rb") as source, plain_events.open(
                "wb"
            ) as destination:
                shutil.copyfileobj(source, destination)

        visit_csv = temporary_dir / "emetrics.csv"
        run_tool("derive-visits", ["--events", plain_events, "--out", visit_csv])
        event_metrics = pd.read_csv(visit_csv)
        check_visit_metrics(event_metrics, visits)
        with visit_csv.open("rb") as source, gzip.open(
            run_dir / "emetrics.csv.gz", "wb"
        ) as destination:
            shutil.copyfileobj(source, destination)

        system_csv = run_dir / "sysmetrics.csv"
        run_tool(
            "derive-system",
            ["--events", plain_events, "--out", system_csv, "--window", 10, "--dense"],
        )
        check_system_metrics(pd.read_csv(system_csv), completed, horizon)
        run_tool(
            "plot-system",
            [
                "--sysmetrics",
                system_csv,
                "--out",
                result_dir / "resplot.png",
                "--title",
                f"{scenario.name}: latency and completions per 10-tick window",
            ],
        )

        # Keep the same outcome-based job selection used by the original study.
        ordered = completed.sort_values(["latency", "job"])
        positions = sorted(
            {
                int(quantile * (len(ordered) - 1))
                for quantile in [0, 0.25, 0.5, 0.75, 0.9, 0.99, 1]
            }
        )
        selected_jobs = ordered.iloc[positions].job.tolist()
        dropped = job_metrics[job_metrics.status == "dropped"]
        if len(dropped):
            selected_jobs.append(dropped.iloc[0].job)
        trace_log = result_dir / "trace-jobs.log"
        run_tool(
            "filter-jobs",
            [
                "--events",
                plain_events,
                "--jobs",
                ",".join(selected_jobs),
                "--out",
                trace_log,
            ],
        )
        run_tool(
            "trace",
            ["--events", trace_log, "--out", result_dir / "etrace.png"],
        )
        run_tool(
            "pretty-print",
            [trace_log, "--out", result_dir / "pretty-events.txt", "--no-color"],
        )

        # This filter uses pandas and can read compressed qmet input directly.
        queue_csv = run_dir / "qmet.csv"
        if not queue_csv.exists():
            queue_csv = run_dir / "qmet.csv.gz"
        filtered_csv = result_dir / "filtered-queue.csv"
        run_tool(
            "filter-queues",
            ["--qmet", queue_csv, "--qid", busiest_nodes[0], "--out", filtered_csv],
        )
        pd.testing.assert_frame_equal(
            pd.read_csv(filtered_csv),
            queue_metrics[
                queue_metrics["queue-sys-id"] == busiest_nodes[0]
            ].reset_index(drop=True),
            check_dtype=False,
        )
        # Verify the filter kept the full event sequence, not only a matching ID.
        wanted = set(selected_jobs)
        with plain_events.open() as source:
            expected_lines = [
                line for line in source if line.split(maxsplit=2)[1] in wanted
            ]
        assert trace_log.read_text().splitlines(keepends=True) == expected_lines

        if scenario.name == "base-30k":
            selected_visits = event_metrics[
                event_metrics["Queue-sys-id"].isin(
                    [f"q{node}" for node in busiest_nodes]
                )
            ]
            selected_csv = temporary_dir / "selected-visits.csv.gz"
            selected_visits.to_csv(selected_csv, index=False)
            for output_name, option, columns in [
                ("emetrics-hist.png", "--hist", "arrival-time"),
                ("emetrics-scatter.png", "--scat", "arrival-time,response-time"),
                (
                    "emetrics-scatter-turnaround.png",
                    "--scat",
                    "arrival-time,turnaround-time",
                ),
            ]:
                run_tool(
                    "plot-visits",
                    [
                        selected_csv,
                        result_dir / output_name,
                        option,
                        columns,
                        "--bins",
                        50,
                        "--title",
                        "Baseline: pooled visits from the 12 busiest queues",
                    ],
                )
            workload_csv = temporary_dir / "visualizer-workload.csv"
            visualizer_jobs = jobs.rename(
                columns={"job": "Job Id", "arrival": "arrival time"}
            ).copy()
            visualizer_jobs["Tasks"] = '["0: W 4"]'
            visualizer_jobs.to_csv(workload_csv, index=False)
            run_tool(
                "workload-plot",
                [
                    workload_csv,
                    "--hist",
                    "arrival time",
                    "--bins",
                    50,
                    "--out",
                    result_dir / "workload.png",
                ],
            )
            # The shared scatter plot uses large markers. Save a reproducible
            # sample for legibility; the histogram and simulation use all jobs.
            scatter_csv = temporary_dir / "visualizer-workload-sample.csv"
            visualizer_jobs.sample(
                n=min(1000, len(visualizer_jobs)), random_state=scenario.seed
            ).to_csv(scatter_csv, index=False)
            run_tool(
                "workload-plot",
                [
                    scatter_csv,
                    "--scat",
                    "arrival time,source",
                    "--title",
                    "Baseline: source assignments (1,000 sampled requests)",
                    "--out",
                    result_dir / "workload-scatter.png",
                ],
            )
