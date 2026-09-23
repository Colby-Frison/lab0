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
  // Bare chain Sub-5,Sub-10: visit completes after two applications even if
  // tasks remain; with no edges, unfinished work yields NO-OUT-EDGE.
  SimOptions opts;
  opts.config_path = "tests/fixtures/chain_visit/qconf.csv";
  opts.qmet_path = "tests/fixtures/chain_visit/actual_qmet.csv";
  opts.events_path = "tests/fixtures/chain_visit/actual_events.log";

  Simulator sim(opts);
  sim.run();

  std::string events = read_file(opts.events_path);
  CHECK(events.find("TASK-END") != std::string::npos);
  CHECK(events.find("EXITS-SERVER") != std::string::npos);
  CHECK(events.find("ERROR NO-OUT-EDGE") != std::string::npos);
  CHECK(events.find("DEPART-VIA") == std::string::npos);

  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_chain_visit OK\n";
  return 0;
}
