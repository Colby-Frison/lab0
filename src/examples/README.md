(Directory for tech lead stuff)

# Example Directory

This directory contains different examples of what is to be expected for the given object implementations. It provides example files, pseudocodes, sketches, and more to be understand the intent of the system components alongside validating its functionality (note that more examples can be added should any new cases are realized).

## Object A
### Workload Generator
The included CSV files demonstrate the expected output format for synthetic workloads. The workload generator takes a time interval and a statistical distribution (uniform, normal, geometric, or Poisson) via command-line arguments to produce a file of sorted jobs. The resulting files utilize three primary columns: Job Id, arrival time, and Tasks.

The workload example files are based on the inputted distribution of the workload. For reference, the workload generator will apply the given distribution to determine the number of jobs arriving at the current time step, the amount of tasks to place inside each generated job, and the specific work value (`N` in `"<tid>: W N`) for each individual task in a job.

- **Uniform**: This distribution requires an inclusive range of integers for the workload generator to randomly pick a number with equal probability for each calculation. This should create some baseline of constant unpredictability; that is, it should make a large payload (i.e., a job with with 3 tasks of size 3) have the exact likelihood to be generated as a minimal one (i.e., a job with 1 task of size 1).

- **Normal**: This distriubtion requires inputs of a mean and standard deviation for the generator to produce values clustering heavily around the given average. This should create a stable, bell-curve workload. Extreme variations are possible but rare, while most of the generated job counts, task quantities, and work sizes consistently hover around the average.

- **Geometric**: This distribution requires a probability parameter input for the generator to model the number of failures before a successful trial. This produces many small numbers or zeros with an occassional trailing spike(s). It frequently produces very lightweight (or no) elements, followed sometimes by some unusually large payload. 

- **Poisson**: This distribution requires a Poisson mean (denoted lambda) that handles the average rate of jobs per time step for the generator to model the probability of independent events occuring in a fixed interval. This should mimic natural user traffic; it should hover around lambda but can also produce unpredictable clusters (or none at all).

### Workload Visualizer


## Object B


## Object C


## Object E