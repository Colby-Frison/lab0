#pragma once

// event_log.hpp — Shared plain-text event log for all queue systems.
// One line per state change (ARRIVE-VIA, TASK-END, DEPART-VIA, errors, …).

#include <fstream>
#include <string>

class EventLog {
 public:
  explicit EventLog(const std::string& path);
  void log(const std::string& line);
  void flush();

 private:
  std::ofstream out_;
};
