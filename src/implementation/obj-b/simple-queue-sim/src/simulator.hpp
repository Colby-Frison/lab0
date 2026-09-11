#pragma once

#include "config_io.hpp"
#include "event_log.hpp"
#include "metrics_writer.hpp"
#include "queue_system.hpp"

#include <string>
#include <unordered_map>
#include <vector>

// Owns all QueueSystems, global clock, and the serve -> move -> admit loop.
class Simulator {
 public:
  bool load_config(const std::string& path);
  void set_outputs(const std::string& qmet_path, const std::string& events_path);
  void set_limit(int limit);  // optional safety cap; <0 means run until drained

  void run();

 private:
  int clock_ = 0;
  int limit_ = -1;
  std::vector<QueueSystem> systems_;
  std::unordered_map<std::string, std::size_t> id_to_index_;  // "q1" -> systems_ index
  EventLog events_;
  MetricsWriter metrics_;

  bool work_remaining() const;
  bool arrival_due_at_clock() const;
  void serve_all();
  void move_all();    // includes sink write + weighted edge routing via id_to_index_
  void admit_all();   // sources + inbound_buffers
  void fill_all();
  void write_metrics();

  QueueSystem* find_system(const std::string& id);
  Edge pick_outgoing_edge(const QueueSystem& qs) const;  // by weight; equal if unspecified
};
