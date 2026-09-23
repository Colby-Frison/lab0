#include "server_function.hpp"

#include <iostream>

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
    std::vector<Task> tasks = {Task::parse("0: W 10")};
    apply_sub_x(tasks, 10);
    CHECK(tasks.empty());
  }
  {
    std::vector<Task> tasks = {Task::parse("0: W 20")};
    apply_sub_x(tasks, 10);
    CHECK(tasks.size() == 1);
    CHECK(tasks[0].work == 10);
  }
  {
    std::vector<Task> tasks = {Task::parse("0: W 10"), Task::parse("1: W 10")};
    apply_sub_x(tasks, 10);
    CHECK(tasks.size() == 1);
    CHECK(tasks[0].tid == 1);
  }
  {
    auto plan = ServicePlan::parse("Sub-10*", 10);
    CHECK(plan.repeat_until_done);
    CHECK(plan.functions.size() == 1);
    CHECK(plan.functions[0].x == 10);
    CHECK(plan.rate == 10);
  }
  {
    auto plan = ServicePlan::parse("Sub-5,Sub-10", 5);
    CHECK(!plan.repeat_until_done);
    CHECK(plan.functions.size() == 2);
    CHECK(plan.functions[0].x == 5);
    CHECK(plan.functions[1].x == 10);
  }
  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "test_subx OK\n";
  return 0;
}
