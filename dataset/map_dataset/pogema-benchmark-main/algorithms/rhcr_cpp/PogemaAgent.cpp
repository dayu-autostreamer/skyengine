//cppimport
#include "PogemaAgent.h"

namespace py = pybind11;

PYBIND11_MODULE(PogemaAgent, m) {
    py::class_<PogemaAgent>(m, "PogemaAgent")
            .def(py::init<>())
            .def("act", &PogemaAgent::act)
            .def("init", &PogemaAgent::init)
            ;
}

<%
cfg['sources'] = ['common.cpp', 'BasicGraph.cpp', 'BasicSystem.cpp', 
                  'ECBS.cpp', 'ECBSNode.cpp', 'LRAStar.cpp', 'MAPFSolver.cpp', 
                  'PBS.cpp', 'PBSNode.cpp', 'PogemaGraph.cpp', 'PogemaSystem.cpp', 
                  'PriorityGraph.cpp', 'ReservationTable.cpp', 'SIPP.cpp', 
                  'SingleAgentSolver.cpp', 'StateTimeAStar.cpp', 'States.cpp', 'WHCAStar.cpp']
cfg['extra_compile_args'] = ['-std=c++17']
setup_pybind11(cfg)
%>