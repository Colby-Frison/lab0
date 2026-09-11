#include "config_io.hpp"

#include <stdexcept>

std::vector<QueueConfigRow> load_queue_config(const std::string& /*path*/) {
  // TODO: parse CSV columns from PDF §B / examples/obj-b/*-config-*.csv
  throw std::logic_error("load_queue_config not implemented");
}
