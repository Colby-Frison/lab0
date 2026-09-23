// job.cpp — Parse/serialize Obj A CSV rows and bracket-aware field splitting.

#include "job.hpp"

#include <cctype>
#include <sstream>
#include <stdexcept>

namespace {

std::string trim(const std::string& s) {
  size_t b = 0;
  while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  size_t e = s.size();
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}

std::string unescape_csv_field(const std::string& field) {
  if (field.size() >= 2 && field.front() == '"' && field.back() == '"') {
    std::string out;
    out.reserve(field.size() - 2);
    for (size_t i = 1; i + 1 < field.size(); ++i) {
      if (field[i] == '"' && i + 1 < field.size() - 1 && field[i + 1] == '"') {
        out.push_back('"');
        ++i;
      } else {
        out.push_back(field[i]);
      }
    }
    return out;
  }
  return field;
}

std::string escape_csv_field(const std::string& field) {
  bool need_quotes = field.find_first_of(",\"\n\r") != std::string::npos;
  if (!need_quotes) return field;
  std::string out = "\"";
  for (char c : field) {
    if (c == '"') out += "\"\"";
    else out.push_back(c);
  }
  out.push_back('"');
  return out;
}

std::vector<std::string> parse_task_list_literal(const std::string& literal) {
  std::string s = trim(literal);
  if (s == "[]") return {};
  if (s.size() < 2 || s.front() != '[' || s.back() != ']') {
    throw std::runtime_error("invalid Tasks field: " + literal);
  }
  s = s.substr(1, s.size() - 2);
  std::vector<std::string> tokens;
  std::string cur;
  bool in_string = false;
  for (size_t i = 0; i < s.size(); ++i) {
    char c = s[i];
    if (in_string) {
      if (c == '\\' && i + 1 < s.size()) {
        cur.push_back(s[++i]);
      } else if (c == '"') {
        in_string = false;
        tokens.push_back(cur);
        cur.clear();
      } else {
        cur.push_back(c);
      }
    } else {
      if (c == '"') {
        in_string = true;
      } else if (c == ',') {
        // separator between strings
      } else if (!std::isspace(static_cast<unsigned char>(c))) {
        // bare token until comma (unlikely for Obj A, but tolerate)
        cur.push_back(c);
        while (i + 1 < s.size() && s[i + 1] != ',') {
          ++i;
          cur.push_back(s[i]);
        }
        tokens.push_back(trim(cur));
        cur.clear();
      }
    }
  }
  return tokens;
}

std::string format_task_list_literal(const std::vector<Task>& tasks) {
  if (tasks.empty()) return "[]";
  std::ostringstream oss;
  oss << '[';
  for (size_t i = 0; i < tasks.size(); ++i) {
    if (i) oss << ", ";
    oss << '"' << tasks[i].to_string() << '"';
  }
  oss << ']';
  return oss.str();
}

}  // namespace

// Split CSV fields; commas inside quotes or [...] do not create new columns.
std::vector<std::string> split_csv_line(const std::string& line) {
  std::vector<std::string> fields;
  std::string cur;
  bool in_quotes = false;
  int bracket_depth = 0;
  for (size_t i = 0; i < line.size(); ++i) {
    char c = line[i];
    if (in_quotes) {
      if (c == '"') {
        if (i + 1 < line.size() && line[i + 1] == '"') {
          cur.push_back('"');
          ++i;
        } else {
          in_quotes = false;
        }
      } else {
        cur.push_back(c);
      }
    } else {
      if (c == '"') {
        in_quotes = true;
      } else if (c == '[') {
        cur.push_back(c);
        ++bracket_depth;
      } else if (c == ']') {
        cur.push_back(c);
        if (bracket_depth > 0) --bracket_depth;
      } else if (c == ',' && bracket_depth == 0) {
        fields.push_back(cur);
        cur.clear();
      } else {
        cur.push_back(c);
      }
    }
  }
  fields.push_back(cur);
  return fields;
}

// Parse "<tid>: W <N>" into structured Task fields.
Task Task::parse(const std::string& token) {
  // Expected: "<tid>: W <N>"
  std::string s = trim(token);
  size_t colon = s.find(':');
  if (colon == std::string::npos) {
    throw std::runtime_error("invalid task token: " + token);
  }
  Task t;
  t.tid = std::stoi(s.substr(0, colon));
  size_t wpos = s.find('W', colon);
  if (wpos == std::string::npos) {
    throw std::runtime_error("invalid task token (no W): " + token);
  }
  t.work = std::stoi(trim(s.substr(wpos + 1)));
  return t;
}

std::string Task::to_string() const {
  return std::to_string(tid) + ": W " + std::to_string(work);
}

// Build a Job from one Obj A CSV data line (three columns).
Job Job::parse_csv_row(const std::string& line) {
  auto fields = split_csv_line(line);
  if (fields.size() < 3) {
    throw std::runtime_error("workload row needs 3 columns: " + line);
  }
  Job j;
  j.id = trim(fields[0]);
  j.source_arrival_time = std::stoi(trim(fields[1]));
  j.queue_arrival_time = j.source_arrival_time;
  std::string tasks_field = fields[2];
  // split_csv_line already unescaped quotes inside fields when tracking quotes;
  // but fields[2] may still be the raw content without outer quotes.
  // Reconstruct: if original had doubled quotes, split_csv_line already decoded.
  auto tokens = parse_task_list_literal(trim(tasks_field));
  for (const auto& tok : tokens) {
    j.tasks.push_back(Task::parse(tok));
  }
  return j;
}

// Serialize back to Obj A CSV with quoted Tasks JSON-style list.
std::string Job::to_csv_row() const {
  std::string tasks_lit = format_task_list_literal(tasks);
  // Always quote Tasks so nested quotes are doubled (Obj A style).
  std::string quoted_tasks = "\"";
  for (char c : tasks_lit) {
    if (c == '"') quoted_tasks += "\"\"";
    else quoted_tasks.push_back(c);
  }
  quoted_tasks.push_back('"');
  return id + "," + std::to_string(source_arrival_time) + "," + quoted_tasks;
}
