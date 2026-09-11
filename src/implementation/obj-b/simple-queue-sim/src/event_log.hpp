#pragma once

#include <fstream>
#include <string>

// Shared event log for all queue systems (PDF token format).
class EventLog {
 public:
  void open(const std::string& path);
  void close();

  void arrive(int t, const std::string& job, const std::string& qsid,
              const std::string& edge);
  void depart(int t, const std::string& job, const std::string& qsid,
              const std::string& edge);
  void enter_server(int t, const std::string& job, const std::string& qsid,
                    int sid);
  void exit_server(int t, const std::string& job, const std::string& qsid,
                   int sid);
  void task_start(int t, const std::string& job, const std::string& qsid,
                  int tid, const std::string& task);
  // Lab PDF p.12 says TASK-STOP; sample log (p.13) and examples use TASK-END — emit TASK-END.
  void task_end(int t, const std::string& job, const std::string& qsid, int tid,
                const std::string& task);
  void error(int t, const std::string& job, const std::string& qsid,
             const std::string& err_type);

 private:
  std::ofstream out_;
};
