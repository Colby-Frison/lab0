# Objective F — Multi-queue modelling and analysis

| Scale | Queues | Jobs | Location | Status |
| --- | --- | --- | --- | --- |
| SMALL | 10s | 1k–10k | [`../multi-SMALL/`](../multi-SMALL/README.md) — emergency-department patient flow (11 stations) | Done |
| MEDIUM | 100s | 10k–100k | [`multi-MEDIUM`](./multi-MEDIUM/README.md) - email network (803 queues) | Done |
| LARGE | 1000s | 100k–1M | [`../multi-LARGE/`](../multi-LARGE/README.md) — Internet packet forwarding between 6,474 Autonomous Systems (SNAP `as-733`) | Done |

Each scale directory holds the model, the configs and workloads, the reproducible
driver script, the plots, and the write-up that answers the slide questions
(mapping, metrics, configuration, workload, behaviour at scale, sensitivity,
takeaways).
