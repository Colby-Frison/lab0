import matplotlib.pyplot as plt
import numpy as np

num_jobs = 100

arrival_times = np.random.randint(0, num_jobs+1, size=num_jobs)
arrival_times = np.sort(arrival_times)

response_times = np.zeros(num_jobs)
server_free_at = 0
for i in range(num_jobs):
    arrival = arrival_times[i]
    wait_time = max(0, server_free_at - arrival) # Calculate wait time if server is busy
    response_times[i] = wait_time

    # Simulate a random task size; server becomes free after finishing task
    task_duration = np.random.randint(1, 20)
    server_free_at = arrival + wait_time + task_duration

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

# Histogram
ax1.hist(arrival_times, bins=25, color='skyblue', edgecolor='black', alpha=0.8)
ax1.set_title('Histogram - Arrival Times')
ax1.set_ylabel('Frequency')

# Scatter Plot
ax2.scatter(arrival_times, response_times, color='blue', edgecolor='gray', s=30)
ax2.set_title('Scatter Plot - Arrival Time vs Response Time')
ax2.set_xlim(0, 100)
ax2.set_xlabel('Arrival Time')
ax2.set_ylabel('Response Time')
ax2.grid(True, alpha=0.3)

plt.suptitle('Derived Job Metrics: System q0 Times Under Load (100 jobs total)')
plt.tight_layout()
plt.savefig('emetrics-sketch-simple.png')
plt.show()