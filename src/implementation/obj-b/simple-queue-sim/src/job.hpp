#pragma once

// job.hpp — Obj A workload types: Task ("tid: W N") and Job CSV row helpers.
// Dual timestamps keep original source arrival separate from per-queue arrival.

#include <string>
#include <vector>

// One task string in Obj A form, e.g. "0: W 10".
struct Task {
  int tid = 0;
  int work = 0;

  static Task parse(const std::string& token);
  std::string to_string() const;
};

// One workload row: id, arrivals, ordered task list.
struct Job {
  std::string id;                 // e.g. "j0"
  int source_arrival_time = 0;    // original source arrival (or sink departure)
  int queue_arrival_time = 0;     // arrival into the current queue system
  std::vector<Task> tasks;

  static Job parse_csv_row(const std::string& line);
  std::string to_csv_row() const;
  bool done() const { return tasks.empty(); }
};

// Split a CSV line respecting quotes and [...] edge/list fields.
std::vector<std::string> split_csv_line(const std::string& line);
