import matplotlib.pyplot as plt
import numpy as np
from collections import deque

num_jobs = 150

arrival_times = np.random.randint(0, num_jobs+1, size=num_jobs)
arrival_times = np.sort(arrival_times)
arrivals = list(arrival_times)

q0_queue = deque()
q0_server_free_at = -1
errors = 0
successful_jobs = []
dropped_jobs = []

# Main algo
for t in range(200):
    # Move completed jobs out of server
    if q0_server_free_at == t: q0_server_free_at = -1

    # Add new jobs
    while arrivals and arrivals[0] == t:
        job_arr = arrivals.pop(0)
        if len(q0_queue) < 15: q0_queue.append(job_arr)
        else:
            errors += 1
            dropped_jobs.append(job_arr)
            
    # Send new jobs to empty servers
    if q0_server_free_at == -1 and q0_queue:
        arr_t = q0_queue.popleft()
        response_time = t - arr_t
        successful_jobs.append({'arrival': arr_t, 'response': response_time})
        q0_server_free_at = t + np.random.randint(1, 5) # Simulate task execution time


plot_arrivals = [j['arrival'] for j in successful_jobs]
plot_responses = [j['response'] for j in successful_jobs]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Histogram
ax1.hist(plot_arrivals, bins=30, color='skyblue', edgecolor='black', alpha=0.8, label='Processed')
if dropped_jobs:
    ax1.hist(dropped_jobs, bins=30, color='salmon', edgecolor='black', alpha=0.8, label='Dropped')
ax1.set_title(f'Histogram (Drops: {errors})')
ax1.set_ylabel('Frequency')
ax1.legend()

# Scatter Plot
ax2.scatter(plot_arrivals, plot_responses, color='steelblue', edgecolor='gray', s=30)
ax2.set_title('Scatter Plot (Queue Capacity: 15)')
ax2.set_xlabel('Arrival Time')
ax2.set_ylabel('Response Time')
ax2.grid(True, alpha=0.3)

plt.suptitle(f'Derived Job Metrics: System q0 ({num_jobs} jobs)')
plt.tight_layout()
plt.savefig('emetrics-sketch-cap.png')
plt.show()