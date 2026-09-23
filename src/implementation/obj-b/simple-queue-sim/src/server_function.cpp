// server_function.cpp — Sub-X semantics and ServicePlan string parsing.

#include "server_function.hpp"

#include <cctype>
#include <stdexcept>

namespace {

std::string trim(const std::string& s) {
  size_t b = 0;
  while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  size_t e = s.size();
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}

}  // namespace

// Sub-X: reduce or remove the front task (PDF §B).
void apply_sub_x(std::vector<Task>& tasks, int x) {
  if (tasks.empty()) return;
  if (tasks.front().work <= x) {
    tasks.erase(tasks.begin());
  } else {
    tasks.front().work -= x;
  }
}

void apply_plan_function(std::vector<Task>& tasks, const ServerFn& fn) {
  switch (fn.kind) {
    case ServerFnKind::SubX:
      apply_sub_x(tasks, fn.x);
      break;
  }
}

// Trailing '*' sets repeat_until_done; commas separate chain steps.
ServicePlan ServicePlan::parse(const std::string& text, int rate) {
  ServicePlan plan;
  plan.rate = rate;
  std::string s = trim(text);
  if (s.empty()) {
    throw std::runtime_error("empty server function");
  }
  if (!s.empty() && s.back() == '*') {
    plan.repeat_until_done = true;
    s.pop_back();
    s = trim(s);
  }

  size_t start = 0;
  while (start < s.size()) {
    size_t comma = s.find(',', start);
    std::string part = trim(
        comma == std::string::npos ? s.substr(start) : s.substr(start, comma - start));
    if (!part.empty()) {
      if (part.rfind("Sub-", 0) == 0) {
        ServerFn fn;
        fn.kind = ServerFnKind::SubX;
        fn.x = std::stoi(part.substr(4));
        plan.functions.push_back(fn);
      } else {
        throw std::runtime_error("unsupported server function: " + part);
      }
    }
    if (comma == std::string::npos) break;
    start = comma + 1;
  }
  if (plan.functions.empty()) {
    throw std::runtime_error("no server functions in plan: " + text);
  }
  return plan;
}
