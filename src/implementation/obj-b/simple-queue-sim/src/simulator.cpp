#include "simulator.hpp"

#include "config_io.hpp"
#include "workload_io.hpp"

#include <stdexcept>

bool Simulator::load_config(const std::string& path) {
  // TODO: load_queue_config(path) -> build systems_, id_to_index_,
  //       workload_io::read each source into source_jobs, size servers
  (void)path;
  throw std::logic_error("Simulator::load_config not implemented");
}

void Simulator::set_outputs(const std::string& qmet_path,
                            const std::string& events_path) {
  metrics_.open(qmet_path);
  events_.open(events_path);
}

void Simulator::set_limit(int limit) { limit_ = limit; }

void Simulator::run() {
  // TODO: input-driven loop — serve -> move -> admit (see obj_b.pseudocode)
  throw std::logic_error("Simulator::run not implemented");
}

bool Simulator::work_remaining() const { return false; }
bool Simulator::arrival_due_at_clock() const { return false; }
void Simulator::serve_all() {}
void Simulator::move_all() {}
void Simulator::admit_all() {}
void Simulator::fill_all() {}
void Simulator::write_metrics() {}

QueueSystem* Simulator::find_system(const std::string& /*id*/) { return nullptr; }

Edge Simulator::pick_outgoing_edge(const QueueSystem& qs) const {
  // TODO: weighted choice; equal weights if unspecified
  if (qs.edges_out.empty()) {
    return {};
  }
  return qs.edges_out.front();
}
