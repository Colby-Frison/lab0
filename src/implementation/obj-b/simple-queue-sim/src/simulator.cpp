// simulator.cpp — Tick loop and inter-queue transfer routing.
// Each clock value is processed exactly once; transfers staged at t become
// admissible at t+1 via next_transfers → current_transfers commit.

#include "simulator.hpp"

#include "config_io.hpp"

#include <sstream>
#include <stdexcept>

// Build every QueueSystem from the config and index them by Sys ID.
Simulator::Simulator(SimOptions opts)
    : opts_(std::move(opts)),
      events_(opts_.events_path),
      qmet_(opts_.qmet_path) {
  auto rows = load_queue_config(opts_.config_path);
  systems_.resize(rows.size());
  for (size_t i = 0; i < rows.size(); ++i) {
    systems_[i].init_from_config(rows[i]);
    id_to_index_[systems_[i].id] = i;
  }
}

// Look up a queue by Sys ID (e.g. "q1") for DEPART routing.
QueueSystem* Simulator::find_system(const std::string& id) {
  auto it = id_to_index_.find(id);
  if (it == id_to_index_.end()) return nullptr;
  return &systems_[it->second];
}

// True while any QS still has source work, waiting jobs, busy servers, or transfers.
bool Simulator::work_remaining() const {
  for (const auto& qs : systems_) {
    if (qs.work_remaining()) return true;
  }
  return false;
}

// Canonical one-pass-per-clock contract (see design README / obj_b.pseudocode).
void Simulator::run() {
  while (work_remaining()) {
    if (opts_.limit >= 0 && clock_ >= opts_.limit) break;

    for (auto& qs : systems_) qs.errors_this_step = 0;

    // 1. SERVE — finish in-system service before same-timestamp arrivals.
    for (auto& qs : systems_) qs.serve_tick(clock_, events_);

    // 2. MOVE — visit-complete jobs leave; peer transfers staged for clock+1.
    std::vector<Transfer> staged;
    for (auto& qs : systems_) qs.move_completed(clock_, events_, staged);
    for (auto& tr : staged) {
      QueueSystem* dest = find_system(tr.to_qsid);
      if (!dest) {
        std::ostringstream oss;
        oss << clock_ << ' ' << tr.job.id << " IN " << tr.from_qsid
            << " ERROR NO-OUT-EDGE";
        events_.log(oss.str());
        QueueSystem* src = find_system(tr.from_qsid);
        if (src) src->errors_this_step += 1;
        continue;
      }
      dest->next_transfers.push_back(std::move(tr));
    }

    // 3. FILL — dispatch jobs that were already waiting (FCFS).
    for (auto& qs : systems_) qs.fill_idle_servers(clock_, events_);

    // 4. ADMIT — sources first, then due transfers (config order).
    for (auto& qs : systems_) qs.admit_sources(clock_, events_);
    for (auto& qs : systems_) qs.admit_transfers(clock_, events_);

    // 5. FILL again — new arrivals can enter an idle server immediately.
    for (auto& qs : systems_) qs.fill_idle_servers(clock_, events_);

    // 6. RECORD — one dense qmet row per queue for this clock.
    for (auto& qs : systems_) {
      qmet_.write_row(clock_, qs.numeric_id,
                      static_cast<int>(qs.waiting.size()), qs.num_in_service(),
                      qs.errors_this_step);
    }

    // Commit staged transfers so they are visible next clock (not this one).
    for (auto& qs : systems_) {
      for (auto& tr : qs.next_transfers) {
        qs.current_transfers.push_back(std::move(tr));
      }
      qs.next_transfers.clear();
    }

    clock_ += 1;
  }

  for (auto& qs : systems_) {
    if (qs.sink) qs.sink->flush();
  }
  events_.flush();
  qmet_.flush();
}
