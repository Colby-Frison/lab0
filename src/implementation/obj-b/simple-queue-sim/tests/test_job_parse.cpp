#include "job.hpp"

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
  {
    Task t = Task::parse("0: W 10");
    CHECK(t.tid == 0);
    CHECK(t.work == 10);
    CHECK(t.to_string() == "0: W 10");
  }
  {
    std::string line = R"(j0,0,"[""0: W 10"", ""1: W 10""]")";
    Job j = Job::parse_csv_row(line);
    CHECK(j.id == "j0");
    CHECK(j.source_arrival_time == 0);
    CHECK(j.tasks.size() == 2);
    CHECK(j.tasks[0].tid == 0 && j.tasks[0].work == 10);
    CHECK(j.tasks[1].tid == 1 && j.tasks[1].work == 10);
    Job again = Job::parse_csv_row(j.to_csv_row());
    CHECK(again.id == j.id);
    CHECK(again.tasks.size() == 2);
    CHECK(again.tasks[0].work == 10);
  }
  {
    Job j = Job::parse_csv_row("j1,20,[]");
    CHECK(j.id == "j1");
    CHECK(j.source_arrival_time == 20);
    CHECK(j.tasks.empty());
  }
  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_job_parse OK\n";
  return 0;
}
