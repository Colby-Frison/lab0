#pragma once

#include "job.hpp"
#include "server_function.hpp"
#include "config_io.hpp"

#include <deque>
#include <memory>
#include <optional>
#include <string>
#include <vector>

struct Server {
  int id = 0;  // sid in event log (ENTERS-SERVER / EXITS-SERVER)
  std::optional<Job> job;
  int rate_timer = 0;
  std::size_t chain_index = 0;

  bool busy() const { return job.has_value(); }
};

// One node in the queueing network (Obj B: usually a single instance).
class QueueSystem {
 public:
  std::string id;
  int numeric_id = 0;  // for qmet.csv
  int max_size = 0;
  int rate = 1;
  std::string source_path;
  std::string sink_path;
  std::vector<Edge> edges_in;
  std::vector<Edge> edges_out;

  std::deque<Job> source_jobs;  // loaded from source_path; consumed by admit
  std::deque<Job> waiting;
  std::vector<Server> servers;
  std::deque<Job> inbound_buffer;  // from upstream DEPART (Obj E)
  std::vector<std::unique_ptr<ServerFunction>> functions;
  int errors_this_step = 0;

  // Helpers used by Simulator (serve -> move -> admit / fill)
  void serve_tick();                 // advance rate timers; apply fn; TASK-END/START
  void move_completed(/* log + route via Simulator */);
  void fill_idle_servers_from_waiting();
  bool has_source_due(int clock) const;
  bool work_remaining() const;
};
