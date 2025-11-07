#pragma once
#include "PogemaSystem.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

class PogemaAgent
{
public:
    PogemaSystem *system;
    SingleAgentSolver *path_planner;
    MAPFSolver *solver;
    int current_step;
    vector<vector<int>> actions;
    PogemaGrid G;
    PogemaAgent()
    {
        system = nullptr;
        path_planner = nullptr;
        solver = nullptr;
    }
    ~PogemaAgent()
    {
        if (path_planner)
            delete path_planner;
        if (solver)
            delete solver;
        if (system)
            delete system;
    }

    void init(vector<vector<int>> grid, vector<pair<int, int>> starts, vector<vector<pair<int, int>>> goals, int simulation_window, int planning_window, int time_limit, int simulation_time, std::string low_level, std::string high_level)
    {
        G.init_map(grid);
        G.init_agents(starts, goals);
        if (low_level == "SIPP")
            path_planner = new SIPP();
        else
            path_planner = new StateTimeAStar();
        if (high_level == "ECBS")
        {
            ECBS *ecbs = new ECBS(G, *path_planner);
            ecbs->potential_function = "SOC";
            ecbs->potential_threshold = 1.1;
            ecbs->suboptimal_bound = 1.1;
            solver = ecbs;
        }
        else
        {
            PBS *pbs = new PBS(G, *path_planner);
            pbs->lazyPriority = false;
            pbs->prioritize_start = false;
            pbs->setRT(true, false);
            solver = pbs;
        }
        solver->screen = 0;
        system = new PogemaSystem(G, *solver);
        system->outfile = "../exp/test";
        system->screen = 0;
        system->log = false;
        system->num_of_drives = starts.size();
        system->time_limit = time_limit;
        system->simulation_window = simulation_window;
        system->planning_window = planning_window;
        system->travel_time_window = 0;
        system->consider_rotation = false;
        system->k_robust = 0;
        system->hold_endpoints = false;
        system->useDummyPaths = false;
        system->seed = 0;
        srand(system->seed);
        current_step = 0;
        system->initialize(simulation_time);
    }

    std::vector<int> act()
    {
        if (system->num_of_drives == 1)
        {
            ReservationTable rt(G);
            system->paths[0] = path_planner->run(G, system->starts[0], system->goal_locations[0], rt);
        }
        else
        {
            if (current_step >= system->timestep)
                system->simulate_next_window();
        }
        vector<int> agent_actions;
        for (int k = 0; k < system->num_of_drives; k++)
        {
            auto prev_pos = system->paths[k][current_step];
            auto cur_pos = system->paths[k][current_step + 1];
            if (cur_pos.location == prev_pos.location)
                agent_actions.push_back(0);
            else if (cur_pos.location - prev_pos.location == -G.cols)
                agent_actions.push_back(1);
            else if (cur_pos.location - prev_pos.location == G.cols)
                agent_actions.push_back(2);
            else if (cur_pos.location - prev_pos.location == -1)
                agent_actions.push_back(3);
            else if (cur_pos.location - prev_pos.location == 1)
                agent_actions.push_back(4);
        }
        current_step++;
        return agent_actions;
    }
};
