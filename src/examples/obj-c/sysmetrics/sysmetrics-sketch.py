import matplotlib.pyplot as plt
import numpy as np

# Example data
time_steps = np.arange(0, 100)
data = np.sin(time_steps / 15) * 50 + 20 + np.random.normal(0, 5, 100) # Data with noise

throughput = np.clip(data, 10, 80) # Simulate throughput 
# Simulate latency
# p10: consistent list of latency of 5 + noise, stays low even when throughput is high
p10_response = np.full(100, 5.0) + np.random.normal(0, 0.5, 100)
# median: baseline of p10 + linear correlation to throughput + noise, rises slightly
median_response = p10_response + (throughput / 4) + np.random.normal(0, 2, 100)
# p90: baseline of median + spikes when throughput is high + noise, spikes when throughput > 60
p90_response = median_response + np.where(throughput > 60, throughput * 1.5, 10) + np.random.normal(0, 5, 100)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

# Latency
ax1.plot(time_steps, p90_response, color='red', linewidth=2, label='P90')
ax1.plot(time_steps, median_response, color='gold', linewidth=2, label='Median')
ax1.plot(time_steps, p10_response, color='green', linewidth=2, label='P10')
ax1.set_ylabel('Latency')
ax1.set_title('Response time (latency) vs time-step')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)

# Throughput
ax2.plot(time_steps, throughput, color='blue', linewidth=2)
ax2.set_ylabel('Throughput')
ax2.set_xlabel('time-step')
ax2.set_title('Throughput vs time-step')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('resplot.png')
plt.show()