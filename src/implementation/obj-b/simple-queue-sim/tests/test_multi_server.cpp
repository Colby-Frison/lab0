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
  opts.config_path = "tests/fixtures/multi_server/qconf.csv";
  opts.qmet_path = "tests/fixtures/multi_server/actual_qmet.csv";
  opts.events_path = "tests/fixtures/multi_server/actual_events.log";

  Simulator sim(opts);
  sim.run();

  std::string events = read_file(opts.events_path);
  CHECK(events.find("ENTERS-SERVER 0") != std::string::npos);
  CHECK(events.find("ENTERS-SERVER 1") != std::string::npos);
  // Both jobs start at t=0 on distinct servers
  CHECK(events.find("0 j0 IN q0 ENTERS-SERVER 0") != std::string::npos);
  CHECK(events.find("0 j1 IN q0 ENTERS-SERVER 1") != std::string::npos);

  auto out = read_file("tests/fixtures/multi_server/out0.wl");
  CHECK(out.find("j0,") != std::string::npos);
  CHECK(out.find("j1,") != std::string::npos);

  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_multi_server OK\n";
  return 0;
}
