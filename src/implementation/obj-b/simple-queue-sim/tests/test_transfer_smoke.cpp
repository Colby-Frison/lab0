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
  opts.config_path = "tests/fixtures/transfer/qconf.csv";
  opts.qmet_path = "tests/fixtures/transfer/actual_qmet.csv";
  opts.events_path = "tests/fixtures/transfer/actual_events.log";

  Simulator sim(opts);
  sim.run();

  std::string events = read_file(opts.events_path);
  CHECK(events.find("DEPART-VIA q1") != std::string::npos);
  CHECK(events.find("ARRIVE-VIA q0") != std::string::npos);
  CHECK(events.find("DEPART-VIA out1.wl") != std::string::npos);

  // DEPART at t, ARRIVE at t+1
  bool depart10 = events.find("\n10 j0 IN q0 DEPART-VIA q1") != std::string::npos ||
                  events.find("10 j0 IN q0 DEPART-VIA q1") == 0;
  // Also allow if file starts with other lines — search substring with newline
  CHECK(events.find("10 j0 IN q0 DEPART-VIA q1") != std::string::npos);
  CHECK(events.find("11 j0 IN q1 ARRIVE-VIA q0") != std::string::npos);

  auto out = read_file("tests/fixtures/transfer/out1.wl");
  CHECK(out.find("j0,") != std::string::npos);

  (void)depart10;
  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_transfer_smoke OK\n";
  return 0;
}
