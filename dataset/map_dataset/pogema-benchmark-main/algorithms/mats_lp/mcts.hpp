#pragma once
#include <iostream>
#include <list>
#include <utility>
#include <vector>
#include <numeric>
#include <cmath>
#include <string>
#include <chrono>
#include <unordered_map>
#include <mutex>
#include <deque>
#include <utility>
#include <functional>
#include <chrono>
#include <algorithm>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
#include "BS_thread_pool.hpp"
#include "NN_Module.h"
#include "MCTSCost2Go.h"

class Decentralized_MCTS
{
    std::vector<MCTSCost2Go> agents;
    std::vector<std::vector<std::pair<int, int>>> reference_paths;
    int merging_range;
    Config cfg;
    NN_module actor;
    std::mt19937 generator;
    std::vector<int> find_and_sort_agents(int agent_idx);
    std::map<int, int> get_actions(std::vector<std::vector<int>> active_agents);
    int cur_step;
public:
    Environment env;
    explicit Decentralized_MCTS() {cur_step=0;};
    std::vector<int> act();
    void set_env(Environment env_, int merging_range_);
    void set_config(const Config& config);
};