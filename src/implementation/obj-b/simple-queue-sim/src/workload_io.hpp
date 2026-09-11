#pragma once

#include "job.hpp"

#include <string>
#include <vector>

// Read/write Obj A workload CSV (Job Id, arrival time, Tasks).
namespace workload_io {

std::vector<Job> read(const std::string& path);
void write(const std::string& path, const std::vector<Job>& jobs);
void append_sink_job(const std::string& path, const Job& job, int depart_time);

}  // namespace workload_io
