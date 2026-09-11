#include "workload_io.hpp"

#include <stdexcept>

namespace workload_io {

std::vector<Job> read(const std::string& /*path*/) {
  // TODO: parse Obj A CSV
  throw std::logic_error("workload_io::read not implemented");
}

void write(const std::string& /*path*/, const std::vector<Job>& /*jobs*/) {
  // TODO: write Obj A CSV
  throw std::logic_error("workload_io::write not implemented");
}

void append_sink_job(const std::string& /*path*/, const Job& /*job*/,
                     int /*depart_time*/) {
  // TODO: append completed job with empty Tasks
  throw std::logic_error("workload_io::append_sink_job not implemented");
}

}  // namespace workload_io
