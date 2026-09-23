#pragma once

// queue_system.hpp — One queueing node (waiting line + N servers + I/O + edges).
// Simulator calls the phase helpers in order; visit completion is separate from
// job done (Tasks == []).

#include "config_io.hpp"
#include "event_log.hpp"
#include "job.hpp"
#include "server_function.hpp"
#include "workload_io.hpp"

#include <deque>
#include <memory>
#include <optional>
#include <string>
#include <vector>

// Job staged for admission at another QS at available_time (usually clock+1).
struct Transfer {
  Job job;
  std::string from_qsid;
  std::string to_qsid;
  int available_time = 0;
};

// One server slot inside a QueueSystem.
struct Server {
  int id = 0;
  std::optional<Job> job;
  int rate_timer = 0;       // counts down to next plan-function application
  int chain_index = 0;      // which ServicePlan function is next
  bool visit_complete = false;
  bool busy() const { return job.has_value(); }
};

// Full queue-system state for one Sys ID (e.g. q0).
struct QueueSystem {
  std::string id;
  int numeric_id = 0;  // numeric id written to qmet.csv
  int max_size = 0;    // waiting capacity only (in-service is separate)
  ServicePlan plan;
  std::string source_path;
  std::string sink_path;
  std::vector<Edge> edges_out;
  int edge_rr_state = 0;  // deterministic weighted routing cursor

  std::deque<Job> waiting;
  std::vector<Server> servers;
  std::unique_ptr<SourceStream> source;
  std::unique_ptr<SinkWriter> sink;

  // Dual buffers: next_transfers become current_transfers after RECORD.
  std::deque<Transfer> current_transfers;
  std::deque<Transfer> next_transfers;
  int errors_this_step = 0;

  void init_from_config(const QueueConfigRow& row);
  bool work_remaining() const;
  int num_in_service() const;
  Server* first_idle_server();  // lowest idle sid, or nullptr

  // Advance busy servers by one clock; apply the plan when rate_timer hits 0.
  void serve_tick(int clock, EventLog& events);
  // Route every visit-complete job to sink, a peer edge, or NO-OUT-EDGE.
  void move_completed(int clock, EventLog& events,
                      std::vector<Transfer>& staged_out);
  // Work-conserving FCFS fill from the waiting deque.
  void fill_idle_servers(int clock, EventLog& events);
  // Admit source arrivals due at clock (idle server, wait, or QUEUE-FULL).
  void admit_sources(int clock, EventLog& events);
  // Admit transfers whose available_time == clock.
  void admit_transfers(int clock, EventLog& events);
  // Place a job on a server and emit ENTERS-SERVER / TASK-START.
  void start_job_on_server(Server& s, Job job, int clock, EventLog& events);
};
