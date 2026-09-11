cmake_minimum_required(VERSION 3.16)
project(simple_queue_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(simple-queue-sim
  src/main.cpp
  src/job.cpp
  src/server_function.cpp
  src/queue_system.cpp
  src/simulator.cpp
  src/workload_io.cpp
  src/event_log.cpp
  src/metrics_writer.cpp
  src/config_io.cpp
)

target_include_directories(simple-queue-sim PRIVATE src)
