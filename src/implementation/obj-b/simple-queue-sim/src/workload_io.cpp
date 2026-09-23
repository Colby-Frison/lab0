// workload_io.cpp — SourceStream (lookahead) and SinkWriter implementations.

#include "workload_io.hpp"

#include <stdexcept>

namespace {

std::string trim_line(std::string s) {
  while (!s.empty() && (s.back() == '\r' || s.back() == '\n')) s.pop_back();
  return s;
}

}  // namespace

// Open the source file and prime lookahead with the first job (if any).
SourceStream::SourceStream(const std::string& path) {
  if (path.empty()) {
    exhausted_ = true;
    return;
  }
  in_.open(path);
  if (!in_) throw std::runtime_error("cannot open source workload: " + path);
  advance();
}

const Job& SourceStream::peek() const {
  if (!lookahead_) throw std::runtime_error("SourceStream::peek on empty stream");
  return *lookahead_;
}

// Consume the lookahead job and read the next row.
Job SourceStream::pop() {
  if (!lookahead_) throw std::runtime_error("SourceStream::pop on empty stream");
  Job j = *lookahead_;
  advance();
  return j;
}

// Skip blank lines / header; parse the next Job into lookahead_.
void SourceStream::advance() {
  lookahead_.reset();
  if (!in_.is_open() || exhausted_) return;
  std::string line;
  while (std::getline(in_, line)) {
    line = trim_line(line);
    if (line.empty()) continue;
    if (!header_skipped_) {
      header_skipped_ = true;
      if (line.find("Job Id") != std::string::npos) continue;
    }
    lookahead_ = Job::parse_csv_row(line);
    return;
  }
  exhausted_ = true;
}

// Create/truncate the sink and write the Obj A header.
SinkWriter::SinkWriter(const std::string& path) {
  if (path.empty()) return;
  out_.open(path);
  if (!out_) throw std::runtime_error("cannot open sink workload: " + path);
  out_ << "Job Id,arrival time,Tasks\n";
  header_written_ = true;
}

// Write a completed job; arrival column holds the departure clock.
void SinkWriter::write_completed(const Job& job, int departure_time) {
  if (!out_.is_open()) return;
  Job row = job;
  row.source_arrival_time = departure_time;
  row.tasks.clear();
  out_ << row.to_csv_row() << '\n';
}

void SinkWriter::flush() {
  if (out_.is_open()) out_.flush();
}
