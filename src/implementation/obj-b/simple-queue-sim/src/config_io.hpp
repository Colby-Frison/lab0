#pragma once

// config_io.hpp — Queue config CSV types and loader (Obj B and multi-queue ready).
// Edges may list targets as [q1,q2] or weighted [q1:2.0,q2].

#include <string>
#include <vector>

// Directed link to another queue system.
struct Edge {
  std::string target_id;
  double weight = 1.0;
};

// One row of the queue configuration CSV.
struct QueueConfigRow {
  std::string id;          // e.g. "q0"
  int numeric_id = 0;      // qmet queue-sys-id
  int max_size = 0;
  int num_servers = 0;
  std::string server_function;
  int server_function_rate = 1;
  std::string source;      // path or empty
  std::string sink;        // path or empty
  std::vector<Edge> edges_in;
  std::vector<Edge> edges_out;
};

// Parse all config rows (header + data). Throws on malformed input.
std::vector<QueueConfigRow> load_queue_config(const std::string& path);

// Deterministic weighted pick; advances rr_state.
const Edge& pick_outgoing_edge(const std::vector<Edge>& edges, int& rr_state);
