#pragma once

#include <string>
#include <vector>

// One directed link to another queue system (PDF: weight equal if unspecified).
struct Edge {
  std::string target_id;  // e.g. "q1"
  double weight = 1.0;
};

// One row of the queue configuration CSV (PDF §B).
struct QueueConfigRow {
  std::string id;  // e.g. "q0"
  int numeric_id = 0;  // qmet queue-sys-id (q0 -> 0)
  int max_size = 0;
  int num_servers = 0;
  std::string server_function;  // e.g. "Sub-10" or "Sub-5,Sub-10"
  int server_function_rate = 1;
  std::string source;  // path or empty
  std::string sink;    // path or empty
  std::vector<Edge> edges_in;
  std::vector<Edge> edges_out;
};

// Parse qconf.csv into rows (Obj B: one row; Obj E: many).
std::vector<QueueConfigRow> load_queue_config(const std::string& path);
