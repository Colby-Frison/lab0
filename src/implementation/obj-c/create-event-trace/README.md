# Create Event Trace

Generate a Gantt-style PNG showing job lifecycles from an Objective B (or Objective E) simulator event log. The implementation follows
[`src/design/obj-c/events/create-etrace.pseudo`](../../../design/obj-c/events/create-etrace.pseudo)
and the shared Objective C event-log grammar.

## Usage

```bash
python create_event_trace.py \
  --events events.log \
  [--limit N] \
  [--out etrace.png] \
  [--verbose]
```

| Flag | Meaning |
|---|---|
| `--events` | Simulator event log to read (required) |
| `--limit N` | Plot only the first `N` distinct jobs appearing in the log |
| `--out` | Output image path; defaults to `etrace.png` |
| `-v`, `--verbose` | Report malformed input lines and print a plot summary to stderr |

The tool requires Python 3 and `matplotlib`. It uses matplotlib's noninteractive `Agg` backend, so it also works in terminals and CI environments without a display server.

## Input

Each nonblank event-log line uses the simulator's standard format:

```text
<time> <job-id> IN <queue-system-id> <event-type> [details...]
```

For example:

```text
0 j0 IN q0 ARRIVE-VIA in0.wl
0 j0 IN q0 TASK-START 0 "W 20"
20 j0 IN q0 EXITS-SERVER 0
20 j0 IN q0 DEPART-VIA out0.wl
```

Blank lines are ignored. Malformed lines are skipped and are reported when `--verbose` is enabled. If no valid events remain, the command exits with an error instead of producing an empty chart.

## Visual mapping

Each job gets one horizontal gray lifeline from its earliest event to its latest event anywhere in the queue network. All matching lifecycle events are plotted, so a job moving through several queues can have multiple arrival, exit, and departure markers.

| Event token | Marker | Meaning |
|---|---|---|
| `ARRIVE-VIA` | Blue circle | Job arrived at a queue |
| `TASK-START` | Orange triangle | Processing began |
| `EXITS-SERVER` | Green square | Processing at a server finished |
| `DEPART-VIA` | Purple star | Job departed toward another queue or a sink |

Other valid events, such as `ENTERS-SERVER`, `TASK-END`, and `ERROR`, contribute to the first/last-event lifeline bounds but do not receive their own marker. Jobs appear from top to bottom in the order in which they first occur in the log. `--limit` uses that same order.

## Example

From `src/implementation/obj-c`:

```bash
python create-event-trace/create_event_trace.py \
  --events ../../examples/obj-b/events-single.log \
  --out /tmp/etrace.png \
  --verbose
```

To focus on the first two jobs in a larger multi-queue run:

```bash
python create-event-trace/create_event_trace.py \
  --events ../../examples/obj-b/events-multi.log \
  --limit 2 \
  --out /tmp/etrace-first-two.png
```
