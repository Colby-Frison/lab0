#include <vector>
#include <string>
#include <sstream>
#include <iostream>

// Using a vector to represent list of tasks
using TaskList = vector<string>;
using namespace std;

// Helper
// Extract 'N' from "0: W 10"
int extractWeight(const string& task) {
    size_t wPos = task.find('W');
    return stoi(task.substr(wPos + 1));
}

// Helper
// Extract prefix before weight (e.g., "0: W ")
string extractPrefix(const string& task) {
    size_t wPos = task.find('W');
    return task.substr(0, wPos + 1) + " ";
}

//--------------------------------------------

// Example function "Sub-X"
// Subtract X from first task, or remove it entirely if N <= X
TaskList applySubX(TaskList tasks, int x) {
    if (tasks.empty()) return tasks;

    string currentTask = tasks.front();
    int currentWeight = extractWeight(currentTask);
    string prefix = extractPrefix(currentTask);

    // Task finished, remove from front
    if (currentWeight <= x) tasks.erase(tasks.begin()); 
    // Task partially done, update
    else tasks.front() = prefix + to_string(currentWeight - x);
    
    return tasks;
}

// Example function "Complete-First"
// Instantly finishes current task at front of queue, regardless of size
TaskList applyCompleteFirst(TaskList tasks) {
    if (!tasks.empty()) tasks.erase(tasks.begin());
    return tasks;
}

// Example function "Multiply-Work" (Simulating real-world setbacks by increasing time)
// Multiply remaining work of current task by a factor
TaskList applyWorkPenalty(TaskList tasks, double multiplier) {
    if (tasks.empty()) return tasks;

    string currentTask = tasks.front();
    int currentWeight = extractWeight(currentTask);
    string prefix = extractPrefix(currentTask);

    int newWeight = static_cast<int>(currentWeight * multiplier);
    tasks.front() = prefix + to_string(newWeight);

    return tasks;
}

int main() {
    TaskList myJobTasks = {"0: W 20", "1: W 10"};

    // Chaining functions
    TaskList stepOne = applySubX(myJobTasks, 10);
    TaskList stepTwo = applySubX(stepOne, 10);
    // stepTwo now equals {"1: W 10"}
    
    return 0;
}