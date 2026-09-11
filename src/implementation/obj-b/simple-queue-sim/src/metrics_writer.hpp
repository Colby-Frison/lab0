#pragma once

#include <fstream>
#include <string>

// Writes qmet.csv rows for every queue system each clock step.
class MetricsWriter {
 public:
  void open(const std::string& path);
  void close();

  void write_row(int time_step, int queue_sys_id, int num_jobs_in_queue,
                 int num_jobs_in_service, int num_of_errors);

 private:
  std::ofstream out_;
  bool header_written_ = false;
};
