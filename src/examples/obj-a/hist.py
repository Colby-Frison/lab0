import numpy as np
import matplotlib.pyplot as plt

time_steps = 50
interval = np.arange(time_steps)
workloads = {
    "Fixed": [],
    "Uniform": [],
    "Normal": [],
    "Geometric": [],
    "Poisson": []
}

# Generate workload data
for t in interval:
    # Exactly 2 jobs
    workloads["Fixed"].extend([t] * 2)
    # Randomly between 1-5 jobs
    workloads["Uniform"].extend([t] * np.random.randint(1, 6))
    # Centered on 3 jobs (0 minimum)
    normal_jobs = max(0, int(np.round(np.random.normal(loc=3, scale=1))))
    workloads["Normal"].extend([t] * normal_jobs)
    # Failures before a success (-1 to allow 0 jobs)
    geo_jobs = np.random.geometric(p=0.4) - 1
    workloads["Geometric"].extend([t] * geo_jobs)
    # Approx. mean of 2
    poisson_jobs = np.random.poisson(lam=2)
    workloads["Poisson"].extend([t] * poisson_jobs)

for dist_name, data in workloads.items():
    plt.figure(figsize=(10, 5))
    plt.hist(data, bins=time_steps, range=(0, time_steps), color='skyblue', edgecolor='black', alpha=0.9)
    
    plt.title(f'Workload Histogram - {dist_name}')
    plt.xlabel('Arrival Time (Time Step)')
    plt.ylabel('Number of Jobs')
    plt.xticks(np.arange(0, time_steps + 1, 10))
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    filename = f'histogram_{dist_name.lower()}.png'
    plt.savefig(filename, dpi=300)
    plt.show()