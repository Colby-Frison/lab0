#pragma once

// server_function.hpp — Pure service-plan types and Sub-X task mutation.
// Plans may be chained (Sub-5,Sub-10) and optionally end with '*' to repeat
// until Tasks is empty (repeat_until_done).

#include "job.hpp"

#include <string>
#include <vector>

enum class ServerFnKind { SubX };

// One step in a service plan (currently only Sub-X).
struct ServerFn {
  ServerFnKind kind = ServerFnKind::SubX;
  int x = 0;
};

// Ordered functions + rate + optional '*' repeat policy.
struct ServicePlan {
  std::vector<ServerFn> functions;
  bool repeat_until_done = false;
  int rate = 1;

  // Parse e.g. "Sub-10*", "Sub-5,Sub-10" with the configured rate.
  static ServicePlan parse(const std::string& text, int rate);
};

// Subtract x from the front task's work, or remove it if work <= x.
void apply_sub_x(std::vector<Task>& tasks, int x);

// Dispatch one ServerFn onto a task list.
void apply_plan_function(std::vector<Task>& tasks, const ServerFn& fn);
