#include "PogemaGraph.h"
#include <fstream>
#include <boost/tokenizer.hpp>
#include "StateTimeAStar.h"
#include <sstream>
#include <random>
#include <chrono>

void PogemaGrid::init_map(const vector<vector<int>>& grid)
{
	rows = grid.size();
	cols = grid.front().size();
	move[0] = 1;
	move[1] = -cols;
	move[2] = -1;
	move[3] = cols;

	types.resize(rows*cols);
	weights.resize(rows*cols);

	for (int i = 0; i < rows; i++)
	{
		for (int j = 0; j < cols; j++)
		{
			int id = cols * i + j;
			weights[id].resize(5, WEIGHT_MAX);
			if (grid[i][j] == 1) // obstacle
			{
				types[id] = "Obstacle";
			}
			else
			{
				types[id] = "Travel";
				weights[id][4] = 1;
			}
		}
	}

	for (int i = 0; i < cols * rows; i++)
	{
		if (types[i] == "Obstacle")
		{
			continue;
		}
		for (int dir = 0; dir < 4; dir++)
		{
			if (0 <= i + move[dir] && i + move[dir] < cols * rows && get_Manhattan_distance(i, i + move[dir]) <= 1 && types[i + move[dir]] != "Obstacle")
				weights[i][dir] = 1;
			else
				weights[i][dir] = WEIGHT_MAX;
		}
	}
}

void PogemaGrid::init_agents(const vector<pair<int, int>>& start_locations, const vector<vector<pair<int, int>>>& goal_locations)
{
    this->start_locations.clear();
    set<int> endpoints;
    for(auto s: start_locations)
    {
        this->start_locations.push_back(s.first*cols + s.second);
        endpoints.insert(s.first*cols + s.second);
    }
    for(auto agent_goals: goal_locations)
    {
        vector<int> goals;
        for(auto g: agent_goals)
        {
            goals.push_back(g.first*cols + g.second);
            endpoints.insert(g.first*cols + g.second);
        }
        this->goal_locations.push_back(goals);
        this->current_goal_locations.push_back(goals.front());
    }
    for(auto e: endpoints)
        heuristics[e] = compute_heuristics(e);
}