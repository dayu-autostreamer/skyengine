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
#include "config.h"
#include "environment.h"
#include "BS_thread_pool.hpp"
#include "NN_Module.h"
#include "MinMaxStats.h"
#include <fstream>
#define INITIAL_VALUE_OF_NODE 0
#define ENV_NUM_ACTIONS 5

class Node
{
public:
    int visit_count;
    double prior;
    double value_sum;
    std::vector<std::vector<int>> masked_actions;
    double reward;
    std::vector<Node*> children;
    Node* parent;

    explicit Node():visit_count(0), prior(0), value_sum(INITIAL_VALUE_OF_NODE), reward(0), parent(nullptr){}
    double get_value()
    {
        if(visit_count == 0)
            return 0;
        return value_sum/visit_count;
    }

    std::vector<double> get_distribution(int agent_idx = -1)
    {
        if(agent_idx == -1)
        {
            std::vector<double> result(0);
            double total_visits(0);
            for(auto child: children) {
                result.push_back(child->visit_count);
                total_visits += child->visit_count;
            }
            for(size_t i = 0; i < result.size(); i++)
                result[i] /= total_visits;
            return result;
        }
        else
        {
            std::vector<double> action_scores(ENV_NUM_ACTIONS, 0);
            double total_visits(0);
            for(size_t k = 0; k < children.size(); k++)
            {
                auto actions = get_actions(k);
                int a = actions[agent_idx];
                action_scores[a] += children[k]->visit_count;
                total_visits += children[k]->visit_count;
            }
            for(size_t i = 0; i < action_scores.size(); i++)
                action_scores[i] /= total_visits;
            return action_scores;
        }
    }

    std::vector<int> get_actions(int node_idx)
    {
        int child(node_idx);
        std::vector<int> actions;
        for(size_t agent_idx = 0; agent_idx < masked_actions.size(); agent_idx++)
        {
            actions.push_back(masked_actions[agent_idx][child % masked_actions[agent_idx].size()]);
            child = child / masked_actions[agent_idx].size();
        }
        return actions;
    }

    std::vector<int> select_action(bool use_argmax = false)
    {
        int best_child(0);
        if(use_argmax)
        {
            for(size_t k = 0; k < children.size(); k++)
                if(children[k]->visit_count > children[best_child]->visit_count)
                    best_child = k;
        }
        else
        {
            std::vector<int> score(children.size(), 0);
            std::random_device rd;
            std::mt19937 gen(rd());
            for(size_t k = 0; k < children.size(); k++)
                score[k] = children[k]->visit_count;
            std::discrete_distribution<int> d(score.begin(), score.end());
            best_child = d(gen);
        }
        return get_actions(best_child);
    }

};

class MCTSCost2Go {
public:
    std::list<Node> all_nodes;
    Config cfg;
    NN_module ppo;
    std::vector<int> active_agents;
    std::default_random_engine engine;
    std::mt19937 generator;
    Environment env;
    MinMaxStats minMaxStats;
    explicit MCTSCost2Go(const Environment& env_, Config cfg_)
    {
        env.grid = env_.grid;
        env.collision_system = env_.collision_system;
        env.on_target = env_.on_target;
        env.cost2go = env_.cost2go;
        cfg = std::move(cfg_);
        ppo = NN_module(cfg.path_to_weights);
        generator.seed(0);
    }
    Node* safe_insert_node(Node* parent);
    float evaluate_node(Node* node, float reward, std::vector<std::vector<int>> available_actions, std::vector<int> sorted_agents);
    float ucb_score(Node *parent, Node* child);
    void add_exploration_noise(Node* node, float frac=0.25);
    Node* lookahead_search(std::vector<int> sorted_agents, bool debug=false);
    int run(const Environment &env_, std::vector<int> active_agents_, int agent_idx);
    void show_children(Node* node, int show_max_agents=3);
    void print_input(std::vector<float> input, int obs_radius=3);
};