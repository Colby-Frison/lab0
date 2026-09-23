// event_log.cpp — Append-only event log file writer.

#include "event_log.hpp"

#include <stdexcept>

EventLog::EventLog(const std::string& path) {
  out_.open(path);
  if (!out_) throw std::runtime_error("cannot open event log: " + path);
}

void EventLog::log(const std::string& line) {
  out_ << line << '\n';
}

void EventLog::flush() {
  out_.flush();
}
