#pragma once
#include "BasicSystem.h"
#include "PogemaGraph.h"

class PogemaSystem :
	public BasicSystem
{
public:
	PogemaSystem(const PogemaGrid& G, MAPFSolver& solver);
	~PogemaSystem();

	void simulate();
	void simulate_next_window();
	void initialize(int simulation_time);


private:
	const PogemaGrid& G;
	unordered_set<int> held_endpoints;
    vector<int> current_goal_ids;
	void initialize_start_locations();
	void initialize_goal_locations();
	void update_goal_locations();
};
