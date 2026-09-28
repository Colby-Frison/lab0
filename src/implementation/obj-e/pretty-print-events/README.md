# pretty-print-events

Reads a simulator event log and prints one column per queue. A clock with several events uses extra rows. The time value appears only on the first of those rows.

```text
python pretty_print_events.py events.log
python pretty_print_events.py events.log --out pp-events.log
python pretty_print_events.py events.log --out pp-events.log --no-color
```

From Git Bash or WSL, `./pretty-print-events events.log` does the same thing. If you omit the path, the tool reads stdin, or `events.log` in the current directory when stdin is a terminal.

The layout matches the [dslogs](https://gist.github.com/JJGO/e64c0e8aedb5d464b5f79d3b12197338) pretty-printer the lab points at: each queue is a horizontal column, the whole message is colored by event type. `--out` writes that same view to a `.log`, color codes included, so `less -R pp-events.log` shows the colors. `--no-color` turns them off. On a terminal, and when `less` is installed, the view opens in `less -R`.

| Event | Color |
|-------|--------|
| `ARRIVE-VIA` | bright cyan |
| `DEPART-VIA` | magenta |
| `ENTERS-SERVER` | yellow |
| `EXITS-SERVER` | dim yellow |
| `TASK-START` | bright green |
| `TASK-END` | green |
| `ERROR` | bold red |

A two-queue hop looks like this, without the color codes. Each queue starts at a fixed column. The column is as wide as the longest event in the log, so `ARRIVE-VIA`, `TASK-START`, and `TASK-END` stay on one line.

```text
 0 q0 j0 ARRIVE-VIA in0.wl
   q0 j0 ENTERS-SERVER 0
   q0 j0 TASK-START 0 "W 20"
10 q0 j0 TASK-END 0 "W 20"
   q0 j0 EXITS-SERVER 0
   q0 j0 DEPART-VIA q1
11                        q1 j0 ARRIVE-VIA q0
```

Queue studio menu entry 10 runs this on the event log from the current session.
