import matplotlib.pyplot as plt

# Example data
jobs = ['j0', 'j1', 'j2', 'j3', 'j4']
trace_data = {
    'j0': {'ARRIVE': 5,  'TASK-START': 5,  'EXIT-SERVER': 12, 'DEPART-SINK': 13},
    'j1': {'ARRIVE': 8,  'TASK-START': 12, 'EXIT-SERVER': 18, 'DEPART-SINK': 20},
    'j2': {'ARRIVE': 10, 'TASK-START': 18, 'EXIT-SERVER': 25, 'DEPART-SINK': 26},
    'j3': {'ARRIVE': 12, 'TASK-START': 25, 'EXIT-SERVER': 35, 'DEPART-SINK': 36},
    'j4': {'ARRIVE': 15, 'TASK-START': 35, 'EXIT-SERVER': 42, 'DEPART-SINK': 45},
}

fig, ax = plt.subplots(figsize=(10, 6))
y_ticks = []

# Plot each job
for i, job_id in enumerate(jobs):
    y = i
    y_ticks.append(y)
    
    t_arr = trace_data[job_id]['ARRIVE']
    t_start = trace_data[job_id]['TASK-START']
    t_exit = trace_data[job_id]['EXIT-SERVER']
    t_sink = trace_data[job_id]['DEPART-SINK']
    
    ax.plot([t_arr, t_sink], [y, y], color='gray', linestyle='-', zorder=1)
    
    # Plot specific events
    ax.scatter(t_arr, y, color='skyblue', marker='o', s=100, zorder=2, label='ARRIVE' if i==0 else "")
    ax.scatter(t_start, y, color='orange', marker='^', s=100, zorder=2, label='TASK-START' if i==0 else "")
    ax.scatter(t_exit, y, color='mediumseagreen', marker='s', s=100, zorder=2, label='EXIT-SERVER' if i==0 else "")
    ax.scatter(t_sink, y, color='purple', marker='*', s=150, zorder=2, label='DEPART-SINK' if i==0 else "")

ax.set_yticks(y_ticks)
ax.set_yticklabels(jobs)
ax.set_xlabel('Time Step')
ax.set_title('Event Trace Plot: Job Lifecycle')
ax.grid(True, alpha=0.3, linestyle='--')

# Place the legend outside the plot so it doesn't cover the data
ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.tight_layout()
plt.savefig('etrace-sketch.png')
plt.show()