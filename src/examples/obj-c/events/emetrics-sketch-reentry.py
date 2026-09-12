import matplotlib.pyplot as plt
import numpy as np
from collections import deque

num_jobs = 100

arrival_times = np.random.randint(0, num_jobs+1, size=num_jobs)
arrival_times = np.sort(arrival_times)
arrivals = [{'job_id': i, 'arr_time': t, 'visit_num': 1} for i, t in enumerate(arrival_times)]

q0_queue = deque()
q0_server_free_at = -1
current_job = None
drops = 0
metrics = []

# Main algo
for t in range(200):
    # Move completed jobs out
    if q0_server_free_at == t:
        if np.random.rand() < 0.5:      # 50% chance of re-entry
            current_job['visit_num'] += 1
            current_job['arr_time'] = t  # The new arrival time
            
            if len(q0_queue) < 15: q0_queue.append(current_job)
            else: drops += 1
        
        q0_server_free_at = -1
        current_job = None

    # Add new jobs
    while arrivals and arrivals[0]['arr_time'] == t:
        new_job = arrivals.pop(0)
        if len(q0_queue) < 15: q0_queue.append(new_job)
        else: drops += 1
            
    # Send jobs
    if q0_server_free_at == -1 and q0_queue:
        job = q0_queue.popleft()
        response_time = t - job['arr_time']
        
        # Log metrics for this specific visit
        metrics.append({
            'job_id': job['job_id'],
            'arrival': job['arr_time'],
            'response': response_time,
            'visit_num': job['visit_num']
        })
        
        current_job = job
        q0_server_free_at = t + np.random.randint(2, 6)
        
# Separate data for visual contrast
first_visits = [m for m in metrics if m['visit_num'] == 1]
re_entries = [m for m in metrics if m['visit_num'] > 1]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Histogram
ax1.hist([m['arrival'] for m in first_visits], bins=20, color='skyblue', 
         edgecolor='black', alpha=0.8, label='1st Visit')
if re_entries:
    ax1.hist([m['arrival'] for m in re_entries], bins=20, color='orange', 
             edgecolor='black', alpha=0.8, label='Re-entries')
ax1.set_title(f'Histogram (Drops: {drops})')
ax1.set_ylabel('Frequency')
ax1.legend()

# Scatter Plot
ax2.scatter([m['arrival'] for m in first_visits], [m['response'] for m in first_visits], 
            color='steelblue', edgecolor='gray', s=30, label='1st Visit')
if re_entries:
    ax2.scatter([m['arrival'] for m in re_entries], [m['response'] for m in re_entries], 
                color='darkorange', edgecolor='black', marker='^', s=45, label='Re-entries')

ax2.set_title('Scatter Plot (Queue Capacity: 15)')
ax2.set_xlabel('Arrival Time')
ax2.set_ylabel('Response Time')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.suptitle(f'Derived Job Metrics: System q0 ({num_jobs} jobs)')
plt.tight_layout()
plt.savefig('emetrics-sketch-reentry.png')
plt.show()