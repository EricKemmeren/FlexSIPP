#define BOOST_PYTHON_STATIC_LIB
#include <boost/python.hpp>

#include <chrono>
#include <filesystem>
#include <iostream>
#include <ostream>
#include <string>

#include "constants.hpp"
#include "graph.hpp"
#include "repeat.hpp"
#include "structs.hpp"

std::string search(std::string start, std::string goal, std::string graph_str, double start_time_d=0, double max_search_time_d=1000) {
    intervalTime_t start_time = start_time_d;
    intervalTime_t max_search_time = max_search_time_d;
    Location source_loc(start);
    Location goal_loc(goal);

    Graph g = read_graph(graph_str);

    bool foundStart = false;
    bool foundGoal = false;
    for (GraphNode n: g.node_array) {
        if (n.state.loc == source_loc) foundStart = true;
        if (n.state.loc == goal_loc) foundGoal = true;
    }
    if (!foundStart) {
        std::cout << "[ERROR] Start location {" << source_loc.name << "} does not exist in graph\n";
    }
    if (!foundGoal) {
        std::cout << "[ERROR] Goal location {" << goal_loc.name << "} does not exist in graph\n";
    }

    GraphNode *source = find_earliest(g, source_loc, start_time);

    MetaData m;
    gamma_t initial_gamma(g.n_agents + 1);

    auto search_start_time = std::chrono::high_resolution_clock::now();
    auto res = rePEAT::search(source, goal_loc, m, start_time, initial_gamma, max_search_time);
    auto search_time = std::chrono::high_resolution_clock::now();
    auto search_duration = std::chrono::duration_cast<std::chrono::milliseconds >(
            search_time - search_start_time);

    std::stringstream ss;

    std::flush(std::cerr);
    ss << "{";
    ss << "\"MetaData\":" << m << ", ";
    ss << "\"Result\":" << res << ", ";
    ss << "\"earliest start\":" << start_time << ", ";
    ss << "\"max delay\":" << max_search_time << ", ";
    ss << "\"Search time\": " << search_duration.count();
    ss << "}";
    std::flush(ss);
    std::string output = std::move(ss).str();
    return output;
}

BOOST_PYTHON_MODULE(search) {
    boost::python::def("search", search);
}