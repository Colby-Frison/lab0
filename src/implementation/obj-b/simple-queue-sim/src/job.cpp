#include "job.hpp"

#include <stdexcept>

Task Task::parse(const std::string& /*token*/) {
  // TODO: parse "tid: W N"
  throw std::logic_error("Task::parse not implemented");
}

std::string Task::to_string() const {
  // TODO: format "tid: W N"
  return {};
}
