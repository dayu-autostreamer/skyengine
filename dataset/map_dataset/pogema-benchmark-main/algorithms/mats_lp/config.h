#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
#include <string>
namespace py = pybind11;

class Config
{
public:
    double gamma;
    int num_expansions;
    int steps_limit;
    bool use_move_limits;
    bool agents_as_obstacles;
    bool render;
    double random_action_chance;
    int obs_radius;
    std::string collision_system;
    std::string reward_type;
    std::string on_target;
    double pb_c_init;
    bool ppo_only;
    bool use_nn_module;
    int agents_to_plan;
    std::string path_to_weights;
    int num_threads;
    double progressed_reward;
};