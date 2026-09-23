#pragma once

// metrics_writer.hpp — Dense qmet.csv writer (one row per clock × queue).
// Columns: time-step, queue-sys-id, waiting, in-service, errors-this-step.

#include <fstream>
#include <string>

class MetricsWriter {
 public:
  explicit MetricsWriter(const std::string& path);
  void write_row(int time_step, int queue_sys_id, int num_waiting,
                 int num_in_service, int num_errors);
  void flush();

 private:
  std::ofstream out_;
};
