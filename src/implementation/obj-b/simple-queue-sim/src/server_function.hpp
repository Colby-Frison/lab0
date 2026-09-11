#pragma once

#include "job.hpp"

#include <memory>
#include <string>
#include <vector>

// Mutates a job's task list (e.g. Sub-X). Chains apply over successive rate windows.
class ServerFunction {
 public:
  virtual ~ServerFunction() = default;
  virtual std::vector<Task> apply(std::vector<Task> tasks) const = 0;
};

class SubX final : public ServerFunction {
 public:
  explicit SubX(int x);
  std::vector<Task> apply(std::vector<Task> tasks) const override;

 private:
  int x_;
};

// Parses "Sub-10" or "Sub-5,Sub-10" into an ordered chain.
std::vector<std::unique_ptr<ServerFunction>> parse_server_functions(
    const std::string& spec);
