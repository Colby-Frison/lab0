# Event Metrics: Derive and Plot

## Goal

Given the event log (`events.log`) produced by the simulator, trace individual jobs through specific queues to calculate detailed timing metrics (wait, service, response, and turnaround times). Output this ledger to `emetrics.csv`, and then generate a visualization (`emetrics.png`) to analyze latency distributions and bottleneck queues.

## CLI sketch

```bash
# Derive the event metrics
derive-emetrics \
  --events events.log \
  [--out emetrics.csv]        # default: emetrics.csv

# Generate the visual
plot-emetrics \
  --emetrics emetrics.csv \
  [--out emetrics.png]        # default: emetrics.png
```

## Event Metric Definitions

This schema extracts lifecycles grouped by `(Job id, Queue-sys-id)`, meaning a single job will have multiple rows if it traverses a multi-queue network.

| Metric | Derivation from `events.log` | Insight |
| --- | --- | --- |
| **Job id** | The unique identifier for the job | Tracking specific units of work |
| **Queue-sys-id** | The specific queue system being measured | Identifying network bottlenecks |
| **Arrival-time** | Timestamp of the `ARRIVE-VIA` event | When the job entered this specific queue |
| **Time-in-queue** | `ENTERS-SERVER`−`ARRIVE-VIA` | The delay caused by waiting for an idle server |
| **Time-in-service** | `EXITS-SERVER`−`ENTERS-SERVER` | The active processing time for this queue's server function |
| **Response-time** | Time from arrival until the *first* task starts (`TASK-START`−`ARRIVE-VIA`) | How quickly the system responds to a new arrival |
| **Turn-around-time** | Time from arrival to departure for this queue (`DEPART-VIA`−`ARRIVE-VIA`) | Total time spent in this specific node |

## Worked example (tiny)

Input `events.log`:

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
5 j0 IN q0 ENTERS-SERVER 0
5 j0 IN q0 TASK-START 0 "W 10"
15 j0 IN q0 TASK-END 0 "W 10"
15 j0 IN q0 EXITS-SERVER 0
15 j0 IN q0 DEPART-VIA q1
```

Possible `emetrics.csv` output:

```csv
Job id,Queue-sys-id,Arrival-time,Time-in-queue,Time-in-service,Response-time,Turn-around-time
j0,q0,0,5,10,5,15

```

## Implementation plan

1. Parse CLI parameters for both scripts.
2. In `derive-emetrics`, read `events.log` line-by-line and split into tokens.
3. Maintain a `jobs_in_queue` dictionary keyed by `(job_id, queue_id)` to avoid collisions if a job enters multiple queues or re-enters the same queue.
4. Track the timestamps: set the arrival time on `ARRIVE-VIA`, and update the start time on `TASK-START`.
5. When a job hits `EXITS-SERVER`, calculate the final time differences, write the completed row to the CSV, and delete the tracking key from the dictionary.
6. In `plot-emetrics`, ingest `emetric.csv` using `pandas` and set up a two-panel vertical subplot.
7. Extract all unique queue IDs and iterate through them, applying a dataframe mask for each queue.
    * **Top Panel**: Plot a histogram of `arrival-time` to visualize workload density per queue over time.
    * **Bottom Panel**: Plot a scatter graph of `arrival-time` vs `response-time` to correlate arrival bursts with latency spikes. 
8. Save the figure to the `--out` path.  

---

# Event Tracing: Plot Job Lifecycles

## Goal

Consume the event log (`events.log`) to generate a visual Gantt-style chart (`etrace.png`). This tool maps jobs' lifecycles across a time axis, providing an intuitive visualization of wait times, processing duration, and network handoffs.

## CLI sketch

```bash
create-etrace \
  --events events.log \
  [--limit N]                 # optional: only plot the first N jobs
  [--out etrace.png]          # default: etrace.png
```

## Visual Mapping Definitions

The trace plot translates text log tokens into specific visual markers.

| Event Type | Visual Representation | Intended insight |
| --- | --- | --- |
| **Job Lifeline** | A solid horizontal gray line spanning from the job's first event to its last | Shows the total time a job existed in the simulated network |
| **ARRIVE-VIA** | Circle marker | When a job entered a queue |
| **TASK-START** | Triangle marker | When a job actually began processing (the gap between circle and triangle is the wait time) |
| **EXITS-SERVER** | Square marker | When a job finished processing |
| **DEPART-VIA** | Star marker | When a job left the system entirely |

## Implementation plan

1. Parse CLI parameters.
2. Read `events.log` line-by-line to extract timestamps, job IDs, and event types.
3. Track the minimum (first appearance) and maximum (last appearance) time step for each unique Job ID to define the start and end coordinates for the gray horizontal lifelines.
4. Set up a `matplotlib` figure. Map the unique Job IDs to discrete Y-axis ticks.
5. Draw the horizontal lifelines using `ax.plot()` for each job.
6. Iterate through the parsed events. For every event that matches a defined marker type, use `ax.scatter()` to draw the corresponding shape and color at `(X=time-step, Y=job_y_coordinate)`.
7. Format the chart (e.g., add a grid, set Y-axis labels to the Job IDs, place a legend).
8. Save the layout to the `--out` path.