#include "simulator.hpp"

#include <iostream>
#include <string>

namespace {

void print_usage(const char* argv0) {
  std::cerr
      << "Usage: " << argv0
      << " --config qconf.csv [--limit T] --qmet qmet.csv --events job.log\n";
}

}  // namespace

int main(int argc, char** argv) {
  std::string config;
  std::string qmet;
  std::string events;
  int limit = -1;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    auto need = [&](const char* name) -> std::string {
      if (i + 1 >= argc) {
        std::cerr << "Missing value for " << name << "\n";
        print_usage(argv[0]);
        std::exit(2);
      }
      return argv[++i];
    };

    if (arg == "--config") {
      config = need("--config");
    } else if (arg == "--qmet") {
      qmet = need("--qmet");
    } else if (arg == "--events") {
      events = need("--events");
    } else if (arg == "--limit") {
      limit = std::stoi(need("--limit"));
    } else if (arg == "--help" || arg == "-h") {
      print_usage(argv[0]);
      return 0;
    } else {
      std::cerr << "Unknown argument: " << arg << "\n";
      print_usage(argv[0]);
      return 2;
    }
  }

  if (config.empty() || qmet.empty() || events.empty()) {
    print_usage(argv[0]);
    return 2;
  }

  Simulator sim;
  sim.set_outputs(qmet, events);
  sim.set_limit(limit);

  try {
    sim.load_config(config);
    sim.run();
  } catch (const std::exception& ex) {
    std::cerr << "simple-queue-sim: " << ex.what() << "\n";
    return 1;
  }

  return 0;
}
