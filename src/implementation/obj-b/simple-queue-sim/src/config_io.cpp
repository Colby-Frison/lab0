// config_io.cpp — Load qconf.csv rows and pick weighted outgoing edges.

#include "config_io.hpp"
#include "job.hpp"

#include <cctype>
#include <fstream>
#include <stdexcept>

namespace {

std::string trim(const std::string& s) {
  size_t b = 0;
  while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  size_t e = s.size();
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}

int parse_numeric_id(const std::string& id) {
  // q0 -> 0, q12 -> 12
  size_t i = 0;
  while (i < id.size() && !std::isdigit(static_cast<unsigned char>(id[i]))) ++i;
  if (i >= id.size()) return 0;
  return std::stoi(id.substr(i));
}

std::vector<Edge> parse_edge_list(const std::string& field) {
  // Accepts [], [q1,q2], or [q1:2.0,q2] (optional :weight).
  std::string s = trim(field);
  if (s.empty() || s == "[]") return {};
  if (s.front() == '[' && s.back() == ']') {
    s = s.substr(1, s.size() - 2);
  }
  s = trim(s);
  if (s.empty()) return {};

  std::vector<Edge> edges;
  size_t start = 0;
  while (start < s.size()) {
    size_t comma = s.find(',', start);
    std::string part = trim(
        comma == std::string::npos ? s.substr(start) : s.substr(start, comma - start));
    if (!part.empty()) {
      Edge e;
      size_t colon = part.find(':');
      if (colon != std::string::npos) {
        e.target_id = trim(part.substr(0, colon));
        e.weight = std::stod(trim(part.substr(colon + 1)));
      } else {
        e.target_id = part;
        e.weight = 1.0;
      }
      edges.push_back(e);
    }
    if (comma == std::string::npos) break;
    start = comma + 1;
  }
  return edges;
}

}  // namespace

// Read the full config table into QueueConfigRow values.
std::vector<QueueConfigRow> load_queue_config(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open config: " + path);

  std::string header;
  if (!std::getline(in, header)) {
    throw std::runtime_error("empty config: " + path);
  }

  std::vector<QueueConfigRow> rows;
  std::string line;
  while (std::getline(in, line)) {
    if (trim(line).empty()) continue;
    auto fields = split_csv_line(line);
    if (fields.size() < 9) {
      throw std::runtime_error("config row needs 9 columns: " + line);
    }
    QueueConfigRow row;
    row.id = trim(fields[0]);
    row.numeric_id = parse_numeric_id(row.id);
    row.max_size = std::stoi(trim(fields[1]));
    row.num_servers = std::stoi(trim(fields[2]));
    row.server_function = trim(fields[3]);
    row.server_function_rate = std::stoi(trim(fields[4]));
    row.source = trim(fields[5]);
    row.sink = trim(fields[6]);
    row.edges_in = parse_edge_list(fields[7]);
    row.edges_out = parse_edge_list(fields[8]);
    rows.push_back(row);
  }
  if (rows.empty()) {
    throw std::runtime_error("no queue systems in config: " + path);
  }
  return rows;
}

// Deterministic weighted round-robin; equal weights if unspecified.
const Edge& pick_outgoing_edge(const std::vector<Edge>& edges, int& rr_state) {
  if (edges.empty()) {
    throw std::runtime_error("pick_outgoing_edge on empty edge list");
  }
  double total = 0.0;
  for (const auto& e : edges) total += e.weight;
  if (total <= 0.0) {
    rr_state = (rr_state + 1) % static_cast<int>(edges.size());
    return edges[rr_state];
  }
  // Deterministic weighted round-robin via cumulative slots of integerized weights.
  // Scale weights to integers (x1000) for stable cycling.
  std::vector<int> slots;
  slots.reserve(edges.size());
  int sum = 0;
  for (const auto& e : edges) {
    int w = static_cast<int>(e.weight * 1000.0 + 0.5);
    if (w < 1) w = 1;
    slots.push_back(w);
    sum += w;
  }
  int pick = rr_state % sum;
  rr_state = (rr_state + 1) % sum;
  int acc = 0;
  for (size_t i = 0; i < edges.size(); ++i) {
    acc += slots[i];
    if (pick < acc) return edges[i];
  }
  return edges.back();
}
