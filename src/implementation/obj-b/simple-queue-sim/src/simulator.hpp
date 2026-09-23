#pragma once

// simulator.hpp — Global orchestrator for one or more QueueSystems.
// Owns the clock, shared event/qmet writers, and the canonical per-tick phase
// order: serve → move → fill → admit → fill → record.

#include "event_log.hpp"
#include "metrics_writer.hpp"
#include "queue_system.hpp"

#include <string>
#include <unordered_map>
#include <vector>

// CLI / run options; source and sink paths come from the config CSV, not here.
struct SimOptions {
  std::string config_path;
  std::string qmet_path;
  std::string events_path;
  int limit = -1;  // <0 means run until drained
};

class Simulator {
 public:
  // Load config rows into systems_ and open shared output writers.
  explicit Simulator(SimOptions opts);

  // Input-driven main loop until no work remains (or --limit is hit).
  void run();

 private:
  bool work_remaining() const;
  QueueSystem* find_system(const std::string& id);

  SimOptions opts_;
  std::vector<QueueSystem> systems_;  // Obj B: size 1; Obj E: many
  std::unordered_map<std::string, size_t> id_to_index_;
  int clock_ = 0;
  EventLog events_;
  MetricsWriter qmet_;
};
