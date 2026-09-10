import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Example data
time_steps = np.arange(0, 1000)

# Utilization hits 1.0 (100%) during a burst
util_10 = np.clip(np.sin(time_steps / 100) + np.random.normal(0, 0.1, 1000), 0, 1)
util_100 = pd.Series(util_10).rolling(window=100, min_periods=1).mean()
util_1000 = pd.Series(util_10).rolling(window=1000, min_periods=1).mean()

# Saturation builds when Utilization is maxed out
sat_10 = np.where(util_10 > 0.95, np.random.uniform(2, 10, 1000), 0)
sat_10 = pd.Series(sat_10).rolling(window=10).mean().fillna(0)
sat_100 = sat_10.rolling(window=100, min_periods=1).mean()
sat_1000 = sat_10.rolling(window=1000, min_periods=1).mean()

# Errors trigger when Saturation hits  max queue size (e.g., 5)
err_10 = np.where(sat_10 > 4.5, np.random.uniform(0, 3, 1000), 0)
err_100 = pd.Series(err_10).rolling(window=100, min_periods=1).mean()
err_1000 = pd.Series(err_10).rolling(window=1000, min_periods=1).mean()

# 2. Plotting the USE Metrics
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
color_10 = '#add8e6' 
color_100 = '#4169e1'
color_1000 = '#00008b'

# Subplot Utilization
ax1.plot(time_steps, util_10, color=color_10, alpha=0.5, label='Util(10)')
ax1.plot(time_steps, util_100, color=color_100, label='Util(100)')
ax1.plot(time_steps, util_1000, color=color_1000, linestyle='--', label='Util(1000)')
ax1.set_ylabel('Utilization (%)')
ax1.set_ylim(0, 1.1)
ax1.legend(loc='upper right')

# Subplot Saturation
ax2.fill_between(time_steps, sat_10, color=color_10, alpha=0.3, label='Sat(10)')
ax2.plot(time_steps, sat_100, color=color_100, label='Sat(100)')
ax2.plot(time_steps, sat_1000, color=color_1000, linestyle='--', label='Sat(1000)')
ax2.set_ylabel('Saturation (Queue Length)')
ax2.legend(loc='upper right')

# Subplot Errors
ax3.plot(time_steps, err_10, color=color_10, alpha=0.5, label='Errors(10)')
ax3.plot(time_steps, err_100, color=color_100, label='Errors(100)')
ax3.plot(time_steps, err_1000, color=color_1000, linestyle='--', label='Errors(1000)')
ax3.set_ylabel('Error Rate')
ax3.set_xlabel('Time Step')
ax3.legend(loc='upper right')

plt.suptitle('USE Metrics: System q0 Performance Under Load')
plt.tight_layout()
plt.savefig('use.png')
plt.show()