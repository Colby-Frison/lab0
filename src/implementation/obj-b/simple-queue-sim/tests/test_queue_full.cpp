#include "simulator.hpp"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << " " << #cond      \
                << '\n';                                                       \
      ++failures;                                                              \
    }                                                                          \
  } while (0)

static std::string read_file(const std::string& path) {
  std::ifstream in(path);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

int main() {
  SimOptions opts;
  opts.config_path = "tests/fixtures/queue_full/qconf.csv";
  opts.qmet_path = "tests/fixtures/queue_full/actual_qmet.csv";
  opts.events_path = "tests/fixtures/queue_full/actual_events.log";

  Simulator sim(opts);
  sim.run();

  std::string events = read_file(opts.events_path);
  CHECK(events.find("ERROR QUEUE-FULL") != std::string::npos);

  std::string qmet = read_file(opts.qmet_path);
  CHECK(qmet.find(",1") != std::string::npos);  // some error count
  bool saw_error_row = false;
  std::istringstream ss(qmet);
  std::string line;
  std::getline(ss, line);  // header
  while (std::getline(ss, line)) {
    if (line.empty()) continue;
    // time,qid,wait,svc,errors
    auto last = line.find_last_of(',');
    int errs = std::stoi(line.substr(last + 1));
    if (errs > 0) saw_error_row = true;
  }
  CHECK(saw_error_row);

  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_queue_full OK\n";
  return 0;
}
