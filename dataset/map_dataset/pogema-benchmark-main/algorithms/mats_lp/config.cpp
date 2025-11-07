//cppimport
#include "config.h"

PYBIND11_MODULE(config, m) {
    py::class_<Config>(m, "Config")
        .def(py::init<>())
        .def_readwrite("gamma", &Config::gamma)
        .def_readwrite("num_expansions", &Config::num_expansions)
        .def_readwrite("steps_limit", &Config::steps_limit)
        .def_readwrite("use_move_limits", &Config::use_move_limits)
        .def_readwrite("agents_as_obstacles", &Config::agents_as_obstacles)
        .def_readwrite("render", &Config::render)
        .def_readwrite("reward_type", &Config::reward_type)
        .def_readwrite("collision_system", &Config::collision_system)
        .def_readwrite("on_target", &Config::on_target)
        .def_readwrite("random_action_chance", &Config::random_action_chance)
        .def_readwrite("obs_radius", &Config::obs_radius)
        .def_readwrite("ppo_only", &Config::ppo_only)
        .def_readwrite("use_nn_module", &Config::use_nn_module)
        .def_readwrite("agents_to_plan", &Config::agents_to_plan)
        .def_readwrite("path_to_weights", &Config::path_to_weights)
        .def_readwrite("num_threads", &Config::num_threads)
        .def_readwrite("progressed_reward", &Config::progressed_reward)
        .def_readwrite("pb_c_init", &Config::pb_c_init)
        ;
}

<%
cfg['extra_compile_args'] = ['-std=c++17']
setup_pybind11(cfg)
%>