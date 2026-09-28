# Create Config from Network

Convert a graph stored as Matrix Market (`.mtx`) or a plain `u v [weight]` edge list into the nine-column `qconf.csv` consumed by `simple-queue-sim`.

## Usage

```bash
python create_config_from_network.py \
  --network network.mtx \
  --out qconf.csv \
  [--queue-size 8] \
  [--servers 1] \
  [--function Sub-10] \
  [--rate 10]
```

Useful topology options:

| Option | Meaning |
|---|---|
| `--undirected` | Add a reverse queue edge for every input edge |
| `--ignore-weights` | Treat every route as equal weight |
| `--source NODE=FILE` | Assign a workload source to an original graph node; repeatable |
| `--sink NODE=FILE` | Assign a sink to an original graph node; repeatable |
| `--no-auto-endpoints` | Disable automatic source/sink inference |
| `-v`, `--verbose` | Print graph counts and the node-to-queue mapping |

Without `--no-auto-endpoints`, zero-in-degree nodes receive `inN.wl` and zero-out-degree nodes receive `outN.wl`, where `N` is the generated queue number. Explicit `--source` and `--sink` assignments override those filenames. The source workload files must exist before the simulator is run.

## Supported input

Formal coordinate Matrix Market files are supported for `pattern`, `integer`, and `real` fields with `general` or `symmetric` topology. Matrix indices are one-based, and declared isolated nodes are retained. For example:

```text
%%MatrixMarket matrix coordinate real general
4 4 4
1 2 2.0
1 3 1.0
2 4 1.0
3 4 1.0
```

Plain edge lists may use arbitrary node IDs:

```text
# source target optional-weight
1740 5413 2.0
1740 701 1.0
```

Blank lines and `%`/`#` comments are ignored as appropriate. Weights must be finite and positive unless `--ignore-weights` is used. Exact duplicate edges are collapsed; duplicates with conflicting weights are rejected.

## Example

From the repository root:

```bash
python src/implementation/obj-e/create-config-network/create_config_from_network.py \
  --network src/examples/obj-e/network-dummy.mtx \
  --out /tmp/qconf.csv \
  --verbose
```

The example maps Matrix Market nodes `1..5` to queues `q0..q4`. Node 1 becomes the source, node 5 becomes the sink, and the weighted branch from node 1 is written as `[q1:2,q2:1]`.