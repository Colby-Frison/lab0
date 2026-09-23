// main.cpp — CLI entrypoint: parse flags, construct Simulator, run until drained.
// Source/sink paths are read from the config CSV, not from these flags.

#include "simulator.hpp"

#include <iostream>
#include <string>

namespace {

void usage(const char* argv0) {
  std::cerr
      << "Usage: " << argv0
      << " --config qconf.csv [--limit T] --qmet qmet.csv --events job.log\n";
}

}  // namespace

int main(int argc, char** argv) {
  SimOptions opts;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    auto need = [&](const char* name) -> std::string {
      if (i + 1 >= argc) {
        std::cerr << "missing value for " << name << '\n';
        usage(argv[0]);
        std::exit(2);
      }
      return argv[++i];
    };
    if (arg == "--config") {
      opts.config_path = need("--config");
    } else if (arg == "--qmet") {
      opts.qmet_path = need("--qmet");
    } else if (arg == "--events") {
      opts.events_path = need("--events");
    } else if (arg == "--limit") {
      opts.limit = std::stoi(need("--limit"));
    } else if (arg == "--help" || arg == "-h") {
      usage(argv[0]);
      return 0;
    } else {
      std::cerr << "unknown argument: " << arg << '\n';
      usage(argv[0]);
      return 2;
    }
  }

  if (opts.config_path.empty() || opts.qmet_path.empty() ||
      opts.events_path.empty()) {
    usage(argv[0]);
    return 2;
  }

  try {
    Simulator sim(std::move(opts));
    sim.run();
  } catch (const std::exception& ex) {
    std::cerr << "error: " << ex.what() << '\n';
    return 1;
  }
  return 0;
}
