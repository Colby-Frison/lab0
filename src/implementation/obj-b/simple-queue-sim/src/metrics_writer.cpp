#include "metrics_writer.hpp"

void MetricsWriter::open(const std::string& path) {
  out_.open(path);
  header_written_ = false;
  // TODO: handle open failure
}

void MetricsWriter::close() {
  if (out_.is_open()) {
    out_.close();
  }
}

void MetricsWriter::write_row(int /*time_step*/, int /*queue_sys_id*/,
                              int /*num_jobs_in_queue*/,
                              int /*num_jobs_in_service*/,
                              int /*num_of_errors*/) {
  // TODO: write header once, then CSV row
}
