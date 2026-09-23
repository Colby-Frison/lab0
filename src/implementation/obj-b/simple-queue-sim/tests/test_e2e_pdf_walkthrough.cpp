#include "simulator.hpp"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

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

static std::vector<std::string> lines_of(const std::string& text) {
  std::vector<std::string> out;
  std::istringstream ss(text);
  std::string line;
  while (std::getline(ss, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (!line.empty()) out.push_back(line);
  }
  return out;
}

int main() {
  SimOptions opts;
  opts.config_path = "tests/fixtures/pdf_walkthrough/qconf.csv";
  opts.qmet_path = "tests/fixtures/pdf_walkthrough/actual_qmet.csv";
  opts.events_path = "tests/fixtures/pdf_walkthrough/actual_events.log";

  Simulator sim(opts);
  sim.run();

  auto expected = lines_of(read_file(
      "tests/fixtures/pdf_walkthrough/expected_events.log"));
  auto actual = lines_of(read_file(opts.events_path));
  CHECK(expected.size() == actual.size());
  size_t n = std::min(expected.size(), actual.size());
  for (size_t i = 0; i < n; ++i) {
    if (expected[i] != actual[i]) {
      std::cerr << "event mismatch at line " << (i + 1) << "\n  expected: "
                << expected[i] << "\n  actual:   " << actual[i] << '\n';
      ++failures;
    }
  }

  auto out_lines =
      lines_of(read_file("tests/fixtures/pdf_walkthrough/out0.wl"));
  // header + 3 jobs
  CHECK(out_lines.size() == 4);
  CHECK(out_lines[1].find("j0,20,") == 0);
  CHECK(out_lines[2].find("j1,30,") == 0);
  CHECK(out_lines[3].find("j2,60,") == 0);

  auto qmet = lines_of(read_file(opts.qmet_path));
  CHECK(qmet.size() >= 62);  // header + times 0..60
  // At t=10: j0 in service, j1 waiting
  bool found_t10 = false;
  for (const auto& row : qmet) {
    if (row.rfind("10,0,", 0) == 0) {
      found_t10 = true;
      CHECK(row == "10,0,1,1,0");
    }
  }
  CHECK(found_t10);

  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_e2e_pdf_walkthrough OK\n";
  return 0;
}
