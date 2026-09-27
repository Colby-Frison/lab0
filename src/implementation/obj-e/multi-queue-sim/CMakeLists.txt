cmake_minimum_required(VERSION 3.16)
project(multi_queue_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Same discrete-time engine as Obj B. Multi-queue is a multi-row config,
# not a second simulator. Do not fork these sources.
set(ENGINE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../obj-b/simple-queue-sim")

set(SIM_SOURCES
  ${ENGINE_DIR}/src/job.cpp
  ${ENGINE_DIR}/src/server_function.cpp
  ${ENGINE_DIR}/src/config_io.cpp
  ${ENGINE_DIR}/src/workload_io.cpp
  ${ENGINE_DIR}/src/event_log.cpp
  ${ENGINE_DIR}/src/metrics_writer.cpp
  ${ENGINE_DIR}/src/queue_system.cpp
  ${ENGINE_DIR}/src/simulator.cpp
)

add_library(multi_queue_sim_lib STATIC ${SIM_SOURCES})
target_include_directories(multi_queue_sim_lib PUBLIC "${ENGINE_DIR}/src")

add_executable(multi-queue-sim ${ENGINE_DIR}/src/main.cpp)
target_link_libraries(multi-queue-sim PRIVATE multi_queue_sim_lib)
