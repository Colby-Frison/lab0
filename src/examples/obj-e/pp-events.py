from collections import defaultdict
import re
import os
import subprocess

output_dir = "./src/examples/obj-e"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'pp-events.txt')

log_data = [
    {"Time": 5,  "Job ID": "j0", "Queue": "q0", "Event": "ARRIVE-VIA",    "Details": "in0.wl"},
    {"Time": 5,  "Job ID": "j0", "Queue": "q0", "Event": "ENTERS-SERVER", "Details": "0"},
    {"Time": 5,  "Job ID": "j0", "Queue": "q0", "Event": "TASK-START",    "Details": "0 W 7"},
    {"Time": 8,  "Job ID": "j1", "Queue": "q0", "Event": "ARRIVE-VIA",    "Details": "in0.wl"},
    {"Time": 12, "Job ID": "j0", "Queue": "q0", "Event": "TASK-END",      "Details": "0 W 7"},
    {"Time": 12, "Job ID": "j0", "Queue": "q0", "Event": "EXITS-SERVER",  "Details": "0"},
    {"Time": 12, "Job ID": "j0", "Queue": "q0", "Event": "DEPART-VIA",    "Details": "q1"},
    {"Time": 12, "Job ID": "j1", "Queue": "q0", "Event": "ENTERS-SERVER", "Details": "0"},
    {"Time": 12, "Job ID": "j1", "Queue": "q0", "Event": "TASK-START",    "Details": "0 W 8"},
    {"Time": 12, "Job ID": "j0", "Queue": "q1", "Event": "ARRIVE-VIA",    "Details": "q0"},
    {"Time": 12, "Job ID": "j0", "Queue": "q1", "Event": "ENTERS-SERVER", "Details": "0"},
    {"Time": 12, "Job ID": "j0", "Queue": "q1", "Event": "TASK-START",    "Details": "0 W 7"},
    {"Time": 19, "Job ID": "j0", "Queue": "q1", "Event": "TASK-END",      "Details": "0 W 7"},
    {"Time": 19, "Job ID": "j0", "Queue": "q1", "Event": "EXITS-SERVER",  "Details": "0"},
    {"Time": 19, "Job ID": "j0", "Queue": "q1", "Event": "DEPART-VIA",    "Details": "out.wl"},
    {"Time": 20, "Job ID": "j1", "Queue": "q0", "Event": "TASK-END",      "Details": "0 W 8"},
    {"Time": 20, "Job ID": "j1", "Queue": "q0", "Event": "EXITS-SERVER",  "Details": "0"},
    {"Time": 20, "Job ID": "j1", "Queue": "q0", "Event": "DEPART-VIA",    "Details": "q1"},
    {"Time": 20, "Job ID": "j1", "Queue": "q1", "Event": "ARRIVE-VIA",    "Details": "q0"},
    {"Time": 20, "Job ID": "j1", "Queue": "q1", "Event": "ENTERS-SERVER", "Details": "0"},
    {"Time": 20, "Job ID": "j1", "Queue": "q1", "Event": "TASK-START",    "Details": "0 W 8"},
    {"Time": 28, "Job ID": "j1", "Queue": "q1", "Event": "TASK-END",      "Details": "0 W 8"},
    {"Time": 28, "Job ID": "j1", "Queue": "q1", "Event": "EXITS-SERVER",  "Details": "0"},
    {"Time": 28, "Job ID": "j1", "Queue": "q1", "Event": "DEPART-VIA",    "Details": "out.wl"}
]

COLORS = {
    "ARRIVE-VIA": "\033[92m",    # Green
    "ENTERS-SERVER": "\033[96m", # Cyan
    "TASK-START": "\033[94m",    # Blue
    "TASK-END": "\033[93m",      # Yellow
    "EXITS-SERVER": "\033[95m",  # Magenta
    "DEPART-VIA": "\033[91m",    # Red
    "RESET": "\033[0m"           # White
}

# Helper to remove ANSI codes to measure visible length of a string
def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

queues = sorted(set(row["Queue"] for row in log_data))
columns = ["Time"] + queues
grouped_events = defaultdict(lambda: defaultdict(list))

for row in log_data:
    time_step = row["Time"]
    queue_id = row["Queue"]
    color = COLORS.get(row["Event"], "")
    reset = COLORS["RESET"] if color else ""
    event = f"[{row['Job ID']}] {color}{row['Event']}{reset} ({row['Details']})"
    grouped_events[time_step][queue_id].append(event)

# Calculate dynamic column widths based purely on visible text length
col_widths = {col: len(col) for col in columns}
for time_step, queues_dict in grouped_events.items():
    col_widths["Time"] = max(col_widths["Time"], len(str(time_step)))
    
    for queue_id, events in queues_dict.items():
        for event in events:
            col_widths[queue_id] = max(col_widths[queue_id], len(strip_ansi(event)))

# Generate terminal log
with open(output_file, 'w') as f:
    # Header
    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    f.write(header + "\n")
    f.write("-" * len(header) + "\n")
    
    # Print data w/ exact space padding
    for time_step in sorted(grouped_events.keys()):
        max_events = max(len(grouped_events[time_step][queue_id]) for queue_id in queues)
        for i in range(max_events):
            time_val = str(time_step) if i == 0 else ""
            line_parts = [time_val.ljust(col_widths["Time"])]
            
            for queue_id in queues:
                colored_text = grouped_events[time_step][queue_id][i] if i < len(grouped_events[time_step][queue_id]) else ""
                visible_len = len(strip_ansi(colored_text))
                
                # Add spaces based on visible length (w/o ANSI codes)
                padding = " " * (col_widths[queue_id] - visible_len)
                line_parts.append(colored_text + padding)
                
            f.write(" | ".join(line_parts) + "\n")

try:
    subprocess.run(["less", "-R", output_file])
except KeyboardInterrupt:
    pass