//cppimport
#include "environment.h"

PYBIND11_MODULE(environment, m) {
    py::class_<Environment>(m, "Environment")
            .def(py::init<int, std::string, std::string, float>())
            .def("all_done", &Environment::all_done)
            .def("sample_actions", &Environment::sample_actions)
            .def("precompute_cost2go", &Environment::precompute_cost2go)
            .def("step", &Environment::step)
            .def("step_back", &Environment::step_back)
            .def("set_seed", &Environment::set_seed)
            .def("reset_seed", &Environment::reset_seed)
            .def("create_grid", &Environment::create_grid)
            .def("add_obstacle", &Environment::add_obstacle)
            .def("add_agent", &Environment::add_agent)
            .def("render", &Environment::render)
            .def("get_num_agents", &Environment::get_num_agents)
            .def("reached_goal", &Environment::reached_goal)
            ;
}

<%
cfg['extra_compile_args'] = ['-std=c++17']
setup_pybind11(cfg)
%>