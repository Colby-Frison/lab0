#include "queue_system.hpp"

void QueueSystem::serve_tick() {
  // TODO: decrease rate_timer; apply functions[chain_index] when window completes
}

void QueueSystem::move_completed() {
  // TODO: for each server with job.done(), EXITS-SERVER then sink / edge / ERROR
  // Routing to peer inbound_buffer is coordinated by Simulator (needs peer lookup)
}

void QueueSystem::fill_idle_servers_from_waiting() {
  // TODO: idle server + nonempty waiting -> ENTERS-SERVER, TASK-START
}

bool QueueSystem::has_source_due(int /*clock*/) const {
  // TODO: !source_jobs.empty() && source_jobs.front().arrival_time == clock
  return false;
}

bool QueueSystem::work_remaining() const {
  // TODO: source_jobs, waiting, busy servers, or inbound_buffer nonempty
  return false;
}
