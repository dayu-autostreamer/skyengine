#pragma once
#include "BasicGraph.h"
#include <set>

class PogemaGrid :
	public BasicGraph
{
public:
	vector<int> start_locations;
	vector<int> current_goal_locations;
    vector<vector<int>> goal_locations;
    bool load_map(string fname) { return false; }
    void init_map(const vector<vector<int>>& grid);
    void init_agents(const vector<pair<int, int>>& start_locations, const vector<vector<pair<int, int>>>& goal_locations);
};
