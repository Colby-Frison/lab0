# Base configuration (`base-100k`)

| item | value |
|---|---|
| ASes (queues) | 6,474 |
| links (both directions) | 25,144 |
| stub ASes (degree 1) | 2,384 |
| source stubs | 500 |
| sinks | every AS (6,474) |
| servers | `max(1, ceil(degree / 70))`: total 6,555, 28 ASes with more than 1, max 21 |
| queue size | `max(8, 4 x servers)` |
| server function | `Sub-1`, rate 1 |
| packet | one task `W 4` = 4 AS visits |
| edge weight | `0.001` (one round-robin slot per link) |
