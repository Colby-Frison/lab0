#pragma once

#include <string>
#include <vector>

// A single task string in Obj A form, e.g. "0: W 10".
struct Task {
  int tid = 0;
  int work = 0;

  static Task parse(const std::string& token);
  std::string to_string() const;
};

// One job flowing through the queueing network.
struct Job {
  std::string id;
  int arrival_time = 0;  // source arrival, or departure time when written to sink
  std::vector<Task> tasks;

  bool done() const { return tasks.empty(); }
};
