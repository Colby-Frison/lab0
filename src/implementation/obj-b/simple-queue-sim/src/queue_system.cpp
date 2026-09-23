// queue_system.cpp — Per-queue phase helpers used by Simulator each clock.
// Visit complete (service plan finished here) is not the same as job done
// (Tasks empty). Bare plans leave after one chain pass; '*' repeats until done.

#include "queue_system.hpp"

#include <filesystem>
#include <sstream>
#include <stdexcept>

namespace {

// Format the work token used in TASK-START / TASK-END event lines.
std::string task_work_token(const Task& t) {
  return "\"W " + std::to_string(t.work) + "\"";
}

// Event-log label for a source/sink path: basename only (e.g. in0.wl).
// Full paths stay in source_path/sink_path for actual file I/O.
std::string event_path_label(const std::string& path) {
  if (path.empty()) return path;
  return std::filesystem::path(path).filename().string();
}

}  // namespace

// Wire config row into servers, plan, optional source/sink streams.
void QueueSystem::init_from_config(const QueueConfigRow& row) {
  id = row.id;
  numeric_id = row.numeric_id;
  max_size = row.max_size;
  plan = ServicePlan::parse(row.server_function, row.server_function_rate);
  source_path = row.source;
  sink_path = row.sink;
  edges_out = row.edges_out;

  servers.clear();
  servers.reserve(row.num_servers);
  for (int i = 0; i < row.num_servers; ++i) {
    Server s;
    s.id = i;
    servers.push_back(s);
  }

  if (!source_path.empty()) {
    source = std::make_unique<SourceStream>(source_path);
  }
  if (!sink_path.empty()) {
    sink = std::make_unique<SinkWriter>(sink_path);
  }
}

// Any local work that should keep the global loop running.
bool QueueSystem::work_remaining() const {
  if (source && source->has_job()) return true;
  if (!waiting.empty()) return true;
  for (const auto& s : servers) {
    if (s.busy()) return true;
  }
  if (!current_transfers.empty() || !next_transfers.empty()) return true;
  return false;
}

int QueueSystem::num_in_service() const {
  int n = 0;
  for (const auto& s : servers) {
    if (s.busy()) ++n;
  }
  return n;
}

// Prefer the lowest-numbered idle server for deterministic multi-server fills.
Server* QueueSystem::first_idle_server() {
  for (auto& s : servers) {
    if (!s.busy()) return &s;
  }
  return nullptr;
}

// Start service: reset timers and log ENTERS-SERVER + TASK-START.
void QueueSystem::start_job_on_server(Server& s, Job job, int clock,
                                      EventLog& events) {
  s.job = std::move(job);
  s.rate_timer = plan.rate;
  s.chain_index = 0;
  s.visit_complete = false;

  std::ostringstream oss;
  oss << clock << ' ' << s.job->id << " IN " << id << " ENTERS-SERVER " << s.id;
  events.log(oss.str());

  if (!s.job->tasks.empty()) {
    const Task& t = s.job->tasks.front();
    std::ostringstream tss;
    tss << clock << ' ' << s.job->id << " IN " << id << " TASK-START " << t.tid
        << ' ' << task_work_token(t);
    events.log(tss.str());
  }
}

// Decrement rate timers; when a window ends, apply the next plan function.
void QueueSystem::serve_tick(int clock, EventLog& events) {
  for (auto& s : servers) {
    if (!s.busy() || s.visit_complete) continue;

    s.rate_timer -= 1;
    if (s.rate_timer > 0) continue;

    // Rate window complete: apply next plan function.
    Job& j = *s.job;
    Task ended;
    bool had_front = !j.tasks.empty();
    if (had_front) ended = j.tasks.front();

    if (s.chain_index < 0 ||
        s.chain_index >= static_cast<int>(plan.functions.size())) {
      s.chain_index = 0;
    }
    apply_plan_function(j.tasks, plan.functions[s.chain_index]);

    // TASK-END reports the front task as it was before this application.
    if (had_front) {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " TASK-END " << ended.tid
          << ' ' << task_work_token(ended);
      events.log(oss.str());
    }

    s.chain_index += 1;
    bool chain_finished =
        s.chain_index >= static_cast<int>(plan.functions.size());

    if (plan.repeat_until_done) {
      // '*': keep applying until Tasks is empty, then visit completes.
      if (j.tasks.empty()) {
        s.visit_complete = true;
      } else {
        if (chain_finished) s.chain_index = 0;
        s.rate_timer = plan.rate;
        const Task& t = j.tasks.front();
        std::ostringstream oss;
        oss << clock << ' ' << j.id << " IN " << id << " TASK-START " << t.tid
            << ' ' << task_work_token(t);
        events.log(oss.str());
      }
    } else {
      // Bare plan: visit ends after one full chain even if tasks remain.
      if (chain_finished) {
        s.visit_complete = true;
      } else {
        s.rate_timer = plan.rate;
        if (!j.tasks.empty()) {
          const Task& t = j.tasks.front();
          std::ostringstream oss;
          oss << clock << ' ' << j.id << " IN " << id << " TASK-START " << t.tid
              << ' ' << task_work_token(t);
          events.log(oss.str());
        }
      }
    }
  }
}

// Clear visit-complete servers: sink if done, else stage peer transfer, else error.
void QueueSystem::move_completed(int clock, EventLog& events,
                                 std::vector<Transfer>& staged_out) {
  for (auto& s : servers) {
    if (!s.busy() || !s.visit_complete) continue;

    Job j = std::move(*s.job);
    {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " EXITS-SERVER " << s.id;
      events.log(oss.str());
    }

    if (j.done() && sink) {
      sink->write_completed(j, clock);
      std::ostringstream oss;
      // Prefer basename in the event log so lines stay readable/portable when
      // configs use absolute paths (e.g. from run scripts). Full sink_path is
      // still used above for I/O.
      // oss << clock << ' ' << j.id << " IN " << id << " DEPART-VIA " << sink_path;
      oss << clock << ' ' << j.id << " IN " << id << " DEPART-VIA "
          << event_path_label(sink_path);
      events.log(oss.str());
    } else if (!edges_out.empty()) {
      // Unfinished (or done-without-sink) work follows a weighted outgoing edge.
      const Edge& e = pick_outgoing_edge(edges_out, edge_rr_state);
      {
        std::ostringstream oss;
        oss << clock << ' ' << j.id << " IN " << id << " DEPART-VIA "
            << e.target_id;
        events.log(oss.str());
      }
      Transfer tr;
      tr.job = std::move(j);
      tr.from_qsid = id;
      tr.to_qsid = e.target_id;
      tr.available_time = clock + 1;  // visible to peer next clock only
      staged_out.push_back(std::move(tr));
    } else {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " ERROR NO-OUT-EDGE";
      events.log(oss.str());
      errors_this_step += 1;
    }

    s.job.reset();
    s.rate_timer = 0;
    s.chain_index = 0;
    s.visit_complete = false;
  }
}

// Pull from the waiting head onto idle servers (never skips older waiters).
void QueueSystem::fill_idle_servers(int clock, EventLog& events) {
  while (!waiting.empty()) {
    Server* s = first_idle_server();
    if (!s) break;
    Job j = std::move(waiting.front());
    waiting.pop_front();
    start_job_on_server(*s, std::move(j), clock, events);
  }
}

// Admit every source job whose arrival time equals the current clock.
void QueueSystem::admit_sources(int clock, EventLog& events) {
  if (!source) return;
  while (source->has_job() && source->peek().source_arrival_time == clock) {
    Job j = source->pop();
    j.queue_arrival_time = clock;
    {
      std::ostringstream oss;
      // Prefer basename in the event log so lines stay readable/portable when
      // configs use absolute paths (e.g. from run scripts). Full source_path is
      // still used for opening the SourceStream.
      // oss << clock << ' ' << j.id << " IN " << id << " ARRIVE-VIA "
      //     << source_path;
      oss << clock << ' ' << j.id << " IN " << id << " ARRIVE-VIA "
          << event_path_label(source_path);
      events.log(oss.str());
    }

    // Prefer an idle server over consuming waiting capacity.
    Server* s = first_idle_server();
    if (s) {
      start_job_on_server(*s, std::move(j), clock, events);
    } else if (static_cast<int>(waiting.size()) < max_size) {
      waiting.push_back(std::move(j));
    } else {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " ERROR QUEUE-FULL";
      events.log(oss.str());
      errors_this_step += 1;
    }
  }
}

// Same admission rules for peer transfers due at this clock.
void QueueSystem::admit_transfers(int clock, EventLog& events) {
  while (!current_transfers.empty() &&
         current_transfers.front().available_time == clock) {
    Transfer tr = std::move(current_transfers.front());
    current_transfers.pop_front();
    Job j = std::move(tr.job);
    j.queue_arrival_time = clock;
    {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " ARRIVE-VIA "
          << tr.from_qsid;
      events.log(oss.str());
    }

    Server* s = first_idle_server();
    if (s) {
      start_job_on_server(*s, std::move(j), clock, events);
    } else if (static_cast<int>(waiting.size()) < max_size) {
      waiting.push_back(std::move(j));
    } else {
      std::ostringstream oss;
      oss << clock << ' ' << j.id << " IN " << id << " ERROR QUEUE-FULL";
      events.log(oss.str());
      errors_this_step += 1;
    }
  }
}
