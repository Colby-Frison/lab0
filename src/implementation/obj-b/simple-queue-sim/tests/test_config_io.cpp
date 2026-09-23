#include "config_io.hpp"

#include <fstream>
#include <iostream>
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

int main() {
  const char* path = "tests/fixtures/_tmp_config.csv";
  {
    std::ofstream out(path);
    out << "Sys ID,Queue Max Size,Num. Servers,Server Function,Server "
           "Function Rate,Source,Sink,Edges in,Edges out\n";
    out << "q0,8,1,Sub-10,10,in0.wl,out0.wl,[],[]\n";
    out << "q1,4,2,\"Sub-5,Sub-10\",5,,out1.wl,[q0],[q2:2.0,q3]\n";
  }
  auto rows = load_queue_config(path);
  CHECK(rows.size() == 2);
  CHECK(rows[0].id == "q0");
  CHECK(rows[0].numeric_id == 0);
  CHECK(rows[0].edges_out.empty());
  CHECK(rows[1].server_function == "Sub-5,Sub-10");
  CHECK(rows[1].edges_out.size() == 2);
  CHECK(rows[1].edges_out[0].target_id == "q2");
  CHECK(rows[1].edges_out[0].weight == 2.0);
  CHECK(rows[1].edges_out[1].target_id == "q3");

  int rr = 0;
  const Edge& a = pick_outgoing_edge(rows[1].edges_out, rr);
  CHECK(!a.target_id.empty());

  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_config_io OK\n";
  return 0;
}
