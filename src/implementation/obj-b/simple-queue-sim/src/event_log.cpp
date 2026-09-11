#include "event_log.hpp"

void EventLog::open(const std::string& path) {
  out_.open(path);
  // TODO: handle open failure
}

void EventLog::close() {
  if (out_.is_open()) {
    out_.close();
  }
}

void EventLog::arrive(int /*t*/, const std::string& /*job*/,
                      const std::string& /*qsid*/, const std::string& /*edge*/) {
  // TODO: "<t> <job> IN <qsid> ARRIVE-VIA <edge>"
}

void EventLog::depart(int /*t*/, const std::string& /*job*/,
                      const std::string& /*qsid*/, const std::string& /*edge*/) {
  // TODO: DEPART-VIA
}

void EventLog::enter_server(int /*t*/, const std::string& /*job*/,
                            const std::string& /*qsid*/, int /*sid*/) {
  // TODO: ENTERS-SERVER
}

void EventLog::exit_server(int /*t*/, const std::string& /*job*/,
                           const std::string& /*qsid*/, int /*sid*/) {
  // TODO: EXITS-SERVER
}

void EventLog::task_start(int /*t*/, const std::string& /*job*/,
                          const std::string& /*qsid*/, int /*tid*/,
                          const std::string& /*task*/) {
  // TODO: TASK-START
}

void EventLog::task_end(int /*t*/, const std::string& /*job*/,
                        const std::string& /*qsid*/, int /*tid*/,
                        const std::string& /*task*/) {
  // TODO: TASK-END
}

void EventLog::error(int /*t*/, const std::string& /*job*/,
                     const std::string& /*qsid*/,
                     const std::string& /*err_type*/) {
  // TODO: ERROR QUEUE-FULL | NO-OUT-EDGE
}
