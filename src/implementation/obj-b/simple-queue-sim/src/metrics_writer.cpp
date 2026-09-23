// metrics_writer.cpp — Append dense qmet.csv rows each clock.

#include "metrics_writer.hpp"

#include <stdexcept>

MetricsWriter::MetricsWriter(const std::string& path) {
  out_.open(path);
  if (!out_) throw std::runtime_error("cannot open qmet: " + path);
  out_ << "time-step,queue-sys-id,num-jobs-in-queue,num-jobs-in-service,num-of-errors\n";
}

void MetricsWriter::write_row(int time_step, int queue_sys_id, int num_waiting,
                              int num_in_service, int num_errors) {
  out_ << time_step << ',' << queue_sys_id << ',' << num_waiting << ','
       << num_in_service << ',' << num_errors << '\n';
}

void MetricsWriter::flush() {
  out_.flush();
}
