#include "server_function.hpp"

#include <stdexcept>

SubX::SubX(int x) : x_(x) {}

std::vector<Task> SubX::apply(std::vector<Task> tasks) const {
  // TODO: subtract x_ from first task, or erase if work <= x_
  (void)x_;
  return tasks;
}

std::vector<std::unique_ptr<ServerFunction>> parse_server_functions(
    const std::string& /*spec*/) {
  // TODO: split on commas, parse Sub-N tokens
  throw std::logic_error("parse_server_functions not implemented");
}
