#include "PogemaSystem.h"
#include "WHCAStar.h"
#include "LRAStar.h"
#include "PBS.h"
#include "ECBS.h"

PogemaSystem::PogemaSystem(const PogemaGrid &G, MAPFSolver &solver) : BasicSystem(G, solver), G(G) {}

PogemaSystem::~PogemaSystem()
{
}

void PogemaSystem::initialize(int simulation_time)
{
    this->simulation_time = simulation_time;
    initialize_solvers();
    timestep = 0;
    starts.resize(num_of_drives);
    goal_locations.resize(num_of_drives);
    paths.resize(num_of_drives);
    finished_tasks.resize(num_of_drives);
    current_goal_ids.resize(num_of_drives, 0);
    initialize_start_locations();
    initialize_goal_locations();
}

void PogemaSystem::initialize_start_locations()
{
    for (int k = 0; k < num_of_drives; k++)
    {
        int orientation = -1;
        starts[k] = State(G.start_locations[k], 0, orientation);
        paths[k].emplace_back(starts[k]);
        finished_tasks[k].emplace_back(G.start_locations[k], 0);
    }
}

void PogemaSystem::initialize_goal_locations()
{
    for (int k = 0; k < num_of_drives; k++)
        goal_locations[k].emplace_back(G.current_goal_locations[k], 0);
}

void PogemaSystem::update_goal_locations()
{
    if (!LRA_called)
        new_agents.clear();
    for (int k = 0; k < num_of_drives; k++)
    {
        int curr = paths[k][timestep].location; // current location
        pair<int, int> goal;                    // The last goal location
        if (goal_locations[k].empty())
        {
            goal = make_pair(curr, 0);
        }
        else
        {
            goal = goal_locations[k].back();
        }
        double min_timesteps = G.get_Manhattan_distance(goal.first, curr); // G.heuristics.at(goal)[curr];
        while (min_timesteps <= simulation_window)
        // The agent might finish its tasks during the next planning horizon
        {
            // assign a new task
            pair<int, int> next;
            if(current_goal_ids[k] >= G.goal_locations[k].size())
                break;
            next = make_pair(G.goal_locations[k][current_goal_ids[k] + 1], 0);
            goal_locations[k].emplace_back(next);
            min_timesteps += G.get_Manhattan_distance(next.first, goal.first); // G.heuristics.at(next)[goal];
            goal = next;
            current_goal_ids[k]++;
        }
    }
}

void PogemaSystem::simulate_next_window()
{
    update_start_locations();
    update_goal_locations();
    solve();

    // move drives
    auto new_finished_tasks = move();

    // update tasks
    for (auto task : new_finished_tasks)
    {
        int id, loc, t;
        std::tie(id, loc, t) = task;
        finished_tasks[id].emplace_back(loc, t);
        num_of_tasks++;
        if (hold_endpoints)
            held_endpoints.erase(loc);
    }
    timestep += simulation_window;
}

void PogemaSystem::simulate()
{

    for (; timestep < simulation_time; timestep += simulation_window)
    {
        update_start_locations();
        update_goal_locations();
        solve();

        // move drives
        auto new_finished_tasks = move();

        // update tasks
        for (auto task : new_finished_tasks)
        {
            int id, loc, t;
            std::tie(id, loc, t) = task;
            finished_tasks[id].emplace_back(loc, t);
            num_of_tasks++;
            if (hold_endpoints)
                held_endpoints.erase(loc);
        }

        /*if (congested())
        {
            cout << "***** Too many traffic jams ***" << endl;
            break;
        }*/
    }

    update_start_locations();
    // save_results();
}
