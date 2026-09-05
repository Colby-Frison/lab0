import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

time_steps = 100
arrival_times = np.repeat(np.arange(time_steps), 2) # Assume 2 jobs per time step
total_jobs = len(arrival_times)

# len(Tasks) for each job
task_counts = {
    # Exactly 3 tasks
    "Fixed": np.full(total_jobs, 3),
    # 1-5 tasks
    "Uniform": np.random.randint(1, 6, size=total_jobs),
    # Centered on 3, minimum 1
    "Normal": np.maximum(1, np.round(np.random.normal(loc=3, scale=1, size=total_jobs)).astype(int)),
    # Failures before success, minimum 1
    "Geometric": np.random.geometric(p=0.4, size=total_jobs),
    # Minimum 1, centered around 2
    "Poisson": np.maximum(1, np.random.poisson(lam=2, size=total_jobs))
}

for dist_name, counts in task_counts.items():
    df = pd.DataFrame({
        'arrival time': arrival_times,
        'len(Tasks)': counts
    })
    
    fig, ax = plt.subplots(figsize=(10, 5))
    df.plot.scatter(x='arrival time', y='len(Tasks)', ax=ax, color='coral', edgecolor='black', alpha=0.7, s=30)
    
    ax.set_title(f'Workload Scatter Plot - {dist_name} Task Size')
    ax.set_xlabel('Arrival Time (Time Step)')
    ax.set_ylabel('Number of Tasks in Job')
    
    ax.set_xticks(np.arange(0, time_steps + 1, 10))
    ax.set_ylim(0, df['len(Tasks)'].max() + 1)
    ax.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    filename = f'scatter_{dist_name.lower()}.png'
    plt.savefig(filename, dpi=300)
    plt.show()