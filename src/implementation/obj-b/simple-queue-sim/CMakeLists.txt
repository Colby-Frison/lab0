cmake_minimum_required(VERSION 3.16)
project(simple_queue_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SIM_SOURCES
  src/job.cpp
  src/server_function.cpp
  src/config_io.cpp
  src/workload_io.cpp
  src/event_log.cpp
  src/metrics_writer.cpp
  src/queue_system.cpp
  src/simulator.cpp
)

add_library(simple_queue_sim_lib STATIC ${SIM_SOURCES})
target_include_directories(simple_queue_sim_lib PUBLIC src)

add_executable(simple-queue-sim src/main.cpp)
target_link_libraries(simple-queue-sim PRIVATE simple_queue_sim_lib)

enable_testing()

add_executable(test_job_parse tests/test_job_parse.cpp)
target_link_libraries(test_job_parse PRIVATE simple_queue_sim_lib)
add_test(NAME test_job_parse COMMAND test_job_parse)

add_executable(test_subx tests/test_subx.cpp)
target_link_libraries(test_subx PRIVATE simple_queue_sim_lib)
add_test(NAME test_subx COMMAND test_subx)

add_executable(test_config_io tests/test_config_io.cpp)
target_link_libraries(test_config_io PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_config_io
  COMMAND test_config_io
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_executable(test_e2e_pdf_walkthrough tests/test_e2e_pdf_walkthrough.cpp)
target_link_libraries(test_e2e_pdf_walkthrough PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_e2e_pdf_walkthrough
  COMMAND test_e2e_pdf_walkthrough
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_executable(test_queue_full tests/test_queue_full.cpp)
target_link_libraries(test_queue_full PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_queue_full
  COMMAND test_queue_full
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_executable(test_chain_visit tests/test_chain_visit.cpp)
target_link_libraries(test_chain_visit PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_chain_visit
  COMMAND test_chain_visit
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_executable(test_transfer_smoke tests/test_transfer_smoke.cpp)
target_link_libraries(test_transfer_smoke PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_transfer_smoke
  COMMAND test_transfer_smoke
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_executable(test_multi_server tests/test_multi_server.cpp)
target_link_libraries(test_multi_server PRIVATE simple_queue_sim_lib)
add_test(
  NAME test_multi_server
  COMMAND test_multi_server
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
