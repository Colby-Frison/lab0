#pragma once

// workload_io.hpp — Streaming Obj A source reads and persistent sink writes.
// SourceStream keeps one-row lookahead so large workloads are not loaded fully.

#include "job.hpp"

#include <fstream>
#include <memory>
#include <optional>
#include <string>

// Read a sorted source .wl one row ahead of the admit loop.
class SourceStream {
 public:
  explicit SourceStream(const std::string& path);
  bool has_job() const { return lookahead_.has_value(); }
  const Job& peek() const;
  Job pop();
  bool exhausted() const { return exhausted_ && !lookahead_.has_value(); }

 private:
  void advance();
  std::ifstream in_;
  std::optional<Job> lookahead_;
  bool exhausted_ = false;
  bool header_skipped_ = false;
};

// Append completed jobs (Tasks=[]) with departure time in the arrival column.
class SinkWriter {
 public:
  explicit SinkWriter(const std::string& path);
  void write_completed(const Job& job, int departure_time);
  void flush();

 private:
  std::ofstream out_;
  bool header_written_ = false;
};
