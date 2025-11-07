#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
#include <vector>
#include <iostream>
#include <random>
#include <chrono>
#include <map>
#include <unordered_map>
#include <set>
#include <queue>
#include <string>
#include <list>
#define OBSTACLE 1
#define TRAVERSABLE 0
#define INF 1e7
namespace py = pybind11;

template <typename Enumeration>
auto as_integer(Enumeration const value)
-> typename std::underlying_type<Enumeration>::type
{
    return static_cast<typename std::underlying_type<Enumeration>::type>(value);
}

enum class Collision_system
{
    block_both,
    priority,
    soft
};

enum class On_target
{
    finish,
    nothing,
    restart
};

class Environment_settings
{
public:
    std::map<std::string, Collision_system> collision_system;
    std::map<std::string, On_target> on_target;
    Environment_settings()
    {
        collision_system = {{"block_both", Collision_system::block_both}, {"priority", Collision_system::priority}, {"soft", Collision_system::soft}};
        on_target = {{"finish", On_target::finish}, {"nothing", On_target::nothing}, {"restart", On_target::restart}};
    }
};

class Agent
{
public:
    std::pair<int, int> start;
    std::pair<int, int> cur_position;
    std::pair<int, int> goal;
    std::vector<std::pair<int, int>> all_goals;
    int cur_goal_id;
    bool reached;
    bool terminated;
    int furthest_reached;
    int already_reached;
    std::vector<int> made_actions;
    std::list<std::pair<int, int>> prev_positions;
    explicit Agent()
    {
        cur_goal_id = 0;
        reached = false;
        terminated = false;
    }
    explicit Agent(std::pair<int, int> start_, std::vector<std::pair<int, int>> all_goals_, int cur_cost2go)
    {
        start = start_;
        cur_position = start;
        goal = all_goals_[0];
        all_goals = all_goals_;
        cur_goal_id = 0;
        reached = false;
        terminated = false;
        furthest_reached = cur_cost2go;
        already_reached = cur_cost2go;
    }
};

class Environment
{
public:
    std::vector<Agent> agents;
    std::default_random_engine engine;
    std::vector<std::pair<int, int>> moves = {{0,0}, {-1, 0}, {1,0}, {0,-1}, {0,1}};
    std::vector<std::vector<int>> grid;
    Collision_system collision_system;
    On_target on_target;
    std::map<std::pair<int, int>, std::vector<std::vector<int16_t>>> cost2go;
    int obs_radius;
    double progressed_reward;
    explicit Environment(int obs_radius_ = 5, std::string collision_system_value = "soft", std::string on_target_value = "nothing", double progressed_reward_ = 0.1)
    {
        collision_system = Environment_settings().collision_system[collision_system_value];
        on_target = Environment_settings().on_target[on_target_value];
        obs_radius = obs_radius_;
        progressed_reward = progressed_reward_;
    }

    Environment(const Environment& other)
    {
        agents = other.agents;
        engine = other.engine;
        grid = other.grid;
        collision_system = other.collision_system;
        on_target = other.on_target;
        cost2go = other.cost2go;
        obs_radius = other.obs_radius;
        reset_seed();
    }

    void set_seed(const int seed)
    {
        if(seed < 0)
            engine.seed(std::chrono::system_clock::now().time_since_epoch().count());
        else
            engine.seed(seed);
    }

    float run_simulation(int simulation_depth = 128)
    {
        std::default_random_engine initial_engine_state = engine;
        auto initial_agents_state = agents;
        float reward(0);
        for(int i = 0; i < simulation_depth; i++)
        {
            auto actions = sample_actions(agents.size(), true, false);
            reward += step(actions);
        }
        engine = initial_engine_state;
        agents = initial_agents_state;
        return reward;
    }

    void reset_seed()
    {
        engine.seed(std::chrono::system_clock::now().time_since_epoch().count());
    }

    size_t get_num_agents()
    {
        return agents.size();
    }

    void add_agent(std::pair<int, int> start, std::vector<std::pair<int, int>> goals)
    {
        for(auto goal: goals)
            if(cost2go.find(goal) == cost2go.end())
                cost2go[goal] = get_cost_matrix(goal.first, goal.second);
        
        agents.emplace_back(start, goals, static_cast<int>(cost2go[goals[0]][start.first][start.second]));
        agents.back().already_reached = cost2go[goals[0]][start.first][start.second];
        agents.back().furthest_reached = agents.back().already_reached;
    }

    void reset()
    {
        agents.clear();
    }

    void add_agents(const Environment& other, std::vector<int> active_agents)
    {
        agents.clear();
        for(auto a:active_agents)
            agents.push_back(other.agents[a]);
    }

    void set_next_goal(size_t agent_idx)
    {
        if(static_cast<int>(agents[agent_idx].all_goals.size()) > agents[agent_idx].cur_goal_id + 1)
            agents[agent_idx].cur_goal_id++;
        else
            return;
        agents[agent_idx].goal = agents[agent_idx].all_goals[agents[agent_idx].cur_goal_id];
        agents[agent_idx].terminated = false;
        agents[agent_idx].reached = false;
        agents[agent_idx].already_reached = static_cast<int>(cost2go[agents[agent_idx].goal][agents[agent_idx].cur_position.first][agents[agent_idx].cur_position.second]);
        agents[agent_idx].furthest_reached = agents[agent_idx].already_reached;
    }

    void precompute_cost2go()
    {
        for(size_t i = obs_radius; i < grid.size()-obs_radius; i++)
            for(size_t j = obs_radius; j < grid[0].size()-obs_radius; j++)
                if(grid[i][j] == TRAVERSABLE)
                    cost2go[std::make_pair(i,j)] = get_cost_matrix(i,j);
        for(size_t i = 0; i < agents.size(); i++)
        {
            agents[i].already_reached = static_cast<int>(cost2go[agents[i].goal][agents[i].start.first][agents[i].start.second]);
            agents[i].furthest_reached = agents[i].already_reached;
        }
    }

    std::vector<std::vector<int16_t>> get_cost_matrix(int si, int sj)
    {
        std::queue<std::pair<int, int>> fringe;
        fringe.push({si, sj});
        auto result = std::vector<std::vector<int16_t>>(grid.size(), std::vector<int16_t>(grid[0].size(), -1));
        result[si][sj] = 0;
        while(!fringe.empty())
        {
            auto pos = fringe.front();
            fringe.pop();
            for(const auto& move: moves)
            {
                int new_i(pos.first + move.first), new_j(pos.second + move.second);
                if(grid[new_i][new_j] == TRAVERSABLE && result[new_i][new_j] < 0)
                {
                    result[new_i][new_j] = result[pos.first][pos.second] + 1;
                    fringe.push(std::make_pair(new_i, new_j));
                }
            }
        }
        return result;
    }

    void create_grid(int height, int width)
    {
        grid = std::vector<std::vector<int>>(height, std::vector<int>(width,TRAVERSABLE));
    }

    void add_obstacle(int i, int j)
    {
        grid[i][j] = OBSTACLE;
    }

    bool reached_goal(size_t i) const
    {
        if(i < agents.size())
            return agents[i].reached;
        else
            return false;
    }

    int get_num_done()
    {
        int num_done(0);
        for(auto a: agents)
            num_done += a.reached;
        return num_done;
    }

    void revert_action(int agent_idx, int next_loc, std::unordered_map<int, std::set<int>>& used_cells, std::vector<int>& actions)
    {
        actions[agent_idx] = 0;
        used_cells[next_loc].erase(agent_idx);
        int loc = agents[agent_idx].cur_position.first * grid[0].size() + agents[agent_idx].cur_position.second;
        if(used_cells.count(loc) > 0)
        {
            int other_agent = *used_cells[loc].begin();
            used_cells[loc].insert(agent_idx);
            revert_action(other_agent, loc, used_cells, actions);
        }
        else
            used_cells[loc].insert(agent_idx);
    }

    void cooperate_actions(std::vector<int>& actions)
    {
        std::unordered_map<int, std::set<int>> used_cells;
        std::map<std::pair<int, int>, std::set<int>> used_edges;

        for(size_t i = 0; i < agents.size(); i++) {
            int loc = agents[i].cur_position.first * grid[0].size() + agents[i].cur_position.second;
            int next_loc = (agents[i].cur_position.first + moves[actions[i]].first) * grid[0].size() + agents[i].cur_position.second + moves[actions[i]].second;
            used_cells[next_loc].insert(i);
            used_edges[{loc, next_loc}].insert(i);
            if(next_loc != loc)
                used_edges[{next_loc, loc}].insert(i);
        }
        for(size_t i = 0; i < agents.size(); i++) {
            int loc = agents[i].cur_position.first * grid[0].size() + agents[i].cur_position.second;
            int next_loc = (agents[i].cur_position.first + moves[actions[i]].first) * grid[0].size() + agents[i].cur_position.second + moves[actions[i]].second;
            if(used_edges[{loc, next_loc}].size() > 1)
            {
                used_cells[next_loc].erase(i);
                used_cells[loc].insert(i);
                actions[i] = 0;
            }
        }
        for(int i = agents.size() - 1; i >= 0; i--) {
            int next_loc = (agents[i].cur_position.first + moves[actions[i]].first) * grid[0].size() + agents[i].cur_position.second + moves[actions[i]].second;
            if(used_cells[next_loc].size() > 1 || grid[agents[i].cur_position.first + moves[actions[i]].first][agents[i].cur_position.second + moves[actions[i]].second])
                revert_action(i, next_loc, used_cells, actions);
        }
    }

    float move_agent(int agent_id, int action)
    {
        agents[agent_id].prev_positions.push_back(agents[agent_id].cur_position);
        if(!check_action(agent_id, action, false))
            return 0;
        if((agents[agent_id].reached && on_target != On_target::nothing) || action == 0)
            return 0;
        auto new_pos = std::make_pair(agents[agent_id].cur_position.first + moves[action].first,
                                      agents[agent_id].cur_position.second + moves[action].second);
        for (size_t i = 0; i < agents.size(); i++)
        {
            if(agents[i].reached && on_target != On_target::nothing)
                continue;
            if (agents[agent_id].cur_position.first == new_pos.first && agents[agent_id].cur_position.second == new_pos.second)
                return 0;
        }
        float reward(0);
        if(agents[agent_id].furthest_reached > static_cast<int>(cost2go[agents[agent_id].goal][new_pos.first][new_pos.second]))
            reward += progressed_reward / agents.size();
        agents[agent_id].cur_position = new_pos;
        if(agents[agent_id].cur_position.first == agents[agent_id].goal.first && agents[agent_id].cur_position.second == agents[agent_id].goal.second)
        {
            agents[agent_id].reached = true;
        }
        else
            agents[agent_id].reached = false;
        return reward;
    }

    void move_agent_back(int agent_id)
    {
        agents[agent_id].cur_position = agents[agent_id].prev_positions.back();
        agents[agent_id].prev_positions.pop_back();
        if(agents[agent_id].cur_position.first == agents[agent_id].goal.first && agents[agent_id].cur_position.second == agents[agent_id].goal.second)
            agents[agent_id].reached = true;
        else
            agents[agent_id].reached = false;
    }

    float step(std::vector<int> actions, bool real_actions=false)
    {
        std::vector<std::pair<int, int>> executed_pos;
        for(size_t i = 0; i < agents.size(); i++) {
            if (agents[i].reached && on_target != On_target::nothing)
            {
                executed_pos.push_back(agents[i].cur_position);
                actions[i] = 0;
            }
            else
                executed_pos.emplace_back(agents[i].cur_position.first + moves[actions[i]].first,
                                          agents[i].cur_position.second + moves[actions[i]].second);
        }
        std::map<std::pair<int, int>, bool> used_cells;
        if(collision_system == Collision_system::block_both)
        {
            for (size_t i = 0; i < agents.size(); i++)
                if (!agents[i].reached or on_target == On_target::nothing)
                    used_cells[agents[i].cur_position] = true;
            for (size_t i = 0; i < agents.size(); i++) {
                if (agents[i].reached && on_target == On_target::finish) {
                    continue;
                }
                if (used_cells.count(executed_pos[i]))
                    used_cells[executed_pos[i]] = true;
                else
                    used_cells[executed_pos[i]] = false;
            }
            for (size_t i = 0; i < agents.size(); i++)
                if (used_cells[executed_pos[i]]) {
                    executed_pos[i] = agents[i].cur_position;
                    actions[i] = 0;
                }
            for (size_t i = 0; i < agents.size(); i++)
                if (executed_pos[i].first < 0 || executed_pos[i].first >= static_cast<int>(grid.size()) ||
                    executed_pos[i].second < 0 || executed_pos[i].second >= static_cast<int>(grid[0].size())
                    || grid[executed_pos[i].first][executed_pos[i].second]) {
                    executed_pos[i] = agents[i].cur_position;
                    actions[i] = 0;
                }
        }
        else if(collision_system == Collision_system::priority)
        {
            for (size_t i = 0; i < agents.size(); i++)
            {
                if(agents[i].reached && on_target == On_target::finish)
                    continue;
                if (executed_pos[i].first < 0 || executed_pos[i].first >= static_cast<int>(grid.size()) ||
                    executed_pos[i].second < 0 || executed_pos[i].second >= static_cast<int>(grid[0].size())
                    || grid[executed_pos[i].first][executed_pos[i].second]) {
                    executed_pos[i] = agents[i].cur_position;
                    actions[i] = 0;
                }
                for (size_t j = 0; j < agents.size(); j++)
                {
                    if((agents[i].reached && on_target != On_target::nothing) || i == j)
                        continue;
                    if (executed_pos[i].first == agents[j].cur_position.first &&
                        executed_pos[i].second == agents[j].cur_position.second)
                    {
                        executed_pos[i] = agents[i].cur_position;
                        actions[i] = 0;
                        break;
                    }
                }
                agents[i].cur_position = executed_pos[i];
            }
        }
        else
        {
            cooperate_actions(actions);
            for (size_t i = 0; i < agents.size(); i++)
                executed_pos[i] = std::make_pair(agents[i].cur_position.first + moves[actions[i]].first, agents[i].cur_position.second + moves[actions[i]].second);
        }
        for (size_t i = 0; i < agents.size(); i++)
        {
            agents[i].cur_position = executed_pos[i];
            agents[i].made_actions.push_back(actions[i]);
        }
        float reward(0);
        for(size_t i = 0; i < agents.size(); i++) {
            if (agents[i].reached && on_target == On_target::finish)
                continue;
            int cur_cost2go = static_cast<int>(cost2go[agents[i].goal][executed_pos[i].first][executed_pos[i].second]);
            if (cur_cost2go < agents[i].furthest_reached) {
                reward += 0.1 / agents.size();
                agents[i].furthest_reached = cur_cost2go;
            }
            if (real_actions && agents[i].already_reached > cur_cost2go)
                agents[i].already_reached = cur_cost2go;

            if(executed_pos[i].first == agents[i].goal.first && executed_pos[i].second == agents[i].goal.second)
            {
                agents[i].reached = true;
                set_next_goal(i);
            }
            else
                agents[i].reached = false;
        }
        if(on_target == On_target::nothing && all_done())
            reward = 1;
        return reward;
    }

    void terminate_agents()
    {
        for(size_t i = 0; i < agents.size(); i++)
            if(agents[i].reached && on_target != On_target::nothing)
                agents[i].terminated = true;
    }

    void step_back()
    {
        for(size_t i = 0; i < agents.size(); i++)
        {
            agents[i].cur_position.first = agents[i].cur_position.first - moves[agents[i].made_actions.back()].first;
            agents[i].cur_position.second = agents[i].cur_position.second - moves[agents[i].made_actions.back()].second;
            if(agents[i].cur_position.first != agents[i].goal.first || agents[i].cur_position.second != agents[i].goal.second)
                agents[i].reached = false;
            agents[i].made_actions.pop_back();
        }
    }

    int sample_action(int agent_idx, int num_actions, const bool use_move_limits=false, const bool agents_as_obstacles=false)
    {
        auto action = engine() % num_actions;
        if (use_move_limits)
        {
            while (!check_action(agent_idx, action, agents_as_obstacles))
                action = engine() % num_actions;
        }
        return action;
    }

    std::vector<int> sample_actions(int num_actions, const bool use_move_limits=false, const bool agents_as_obstacles=false)
    {
        std::vector<int> actions;
        for(size_t i = 0; i < agents.size(); i++)
            actions.emplace_back(sample_action(i, num_actions, use_move_limits, agents_as_obstacles));
        return actions;
    }

    bool all_done()
    {
        return static_cast<int>(agents.size()) == get_num_done();
    }

    void render()
    {
        for(size_t i = 0; i < agents.size(); i++) {
            if(agents[i].reached && on_target == On_target::finish)
                continue;
            grid[agents[i].goal.first][agents[i].goal.second] = i + 2 + agents.size();
        }
        for(size_t i = 0; i < agents.size(); i++) {
            if(agents[i].reached && on_target == On_target::finish)
                continue;
            grid[agents[i].cur_position.first][agents[i].cur_position.second] = i + 2;
        }
        for(size_t i = 0; i < grid.size(); i++) {
            for (size_t j = 0; j < grid[0].size(); j++) {
                if (grid[i][j] == 0)
                    std::cout << " . ";
                else if (grid[i][j] == 1)
                    std::cout << " # ";
                else {
                    if (grid[i][j] > static_cast<int>(agents.size()) + 1)
                        std::cout << "|" << grid[i][j] - 2 - agents.size() << "|";
                    else
                        std::cout << " " << grid[i][j] - 2 << " ";
                    grid[i][j] = 0;
                }
            }
            std::cout<<std::endl;
        }
    }

    bool check_action(int agent_idx, int action, bool agents_as_obstacles) const
    {
        std::pair<int, int> future_position = {agents[agent_idx].cur_position.first + moves[action].first, agents[agent_idx].cur_position.second + moves[action].second};
        if (future_position.first < 0 || future_position.second < 0 || future_position.first >= static_cast<int>(grid.size()) || future_position.second >= static_cast<int>(grid[0].size()))
            return false;
        if (grid[future_position.first][future_position.second] == 1)
            return false;
        if (agents_as_obstacles)
        {
            for (size_t i = 0; i < agents.size(); i++)
            {
                if (static_cast<int>(i) != agent_idx)
                {
                    if((agents[i].cur_position.first == future_position.first) && (agents[i].cur_position.second == future_position.second))
                        return false;
                }
            }
        }
        return true;
    }

    std::vector<float> generate_input(int a_id, int input_radius)
    {
        int max_dist(0), min_dist(1e6), mx(0);
        int input_size = input_radius*2+1;
        std::vector<float> input(input_size*input_size*2, 0);
        for(int i = -input_radius; i <= input_radius; i++)
            for(int j = -input_radius; j <= input_radius; j++)
            {
                input[(i + input_radius)*input_size + j + input_radius + input_size*input_size] = static_cast<int>(cost2go[agents[a_id].goal][agents[a_id].cur_position.first + i][agents[a_id].cur_position.second + j]);
                max_dist = std::max(max_dist, static_cast<int>(cost2go[agents[a_id].goal][agents[a_id].cur_position.first + i][agents[a_id].cur_position.second + j]));
            }
        for(size_t a2_id = 0; a2_id < get_num_agents(); a2_id++) {
            if (std::abs(agents[a_id].cur_position.first - agents[a2_id].cur_position.first) <= input_radius &&
                std::abs(agents[a_id].cur_position.second - agents[a2_id].cur_position.second) <= input_radius)
                input[(agents[a2_id].cur_position.first - agents[a_id].cur_position.first + input_radius) * input_size + agents[a2_id].cur_position.second - agents[a_id].cur_position.second + input_radius] = 1;
        }
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
            if(input[i] < 0)
                input[i] += input_radius + max_dist;
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
            min_dist = std::min(min_dist, static_cast<int>(input[i]));
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
            input[i] -= min_dist;
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
            mx = std::max(mx, static_cast<int>(input[i]));
        max_dist = 0;
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
        {
            input[i] = mx - input[i];
            max_dist = std::max(max_dist, static_cast<int>(input[i]));
        }
        for(int i = input_size*input_size; i < input_size*input_size*2; i++)
            input[i] /= max_dist;
        int dist_to_reward = static_cast<int>(cost2go[agents[a_id].goal][agents[a_id].cur_position.first][agents[a_id].cur_position.second]) - agents[a_id].furthest_reached + 1;
        input[input_size*input_size + input_size*input_radius + input_radius] = -std::fmin(1.0, dist_to_reward/64.0);
        return input;
    }

    std::vector<std::vector<int>> get_available_actions()
    {
        std::vector<std::vector<int>> result(agents.size());
        for(size_t agent_id = 0; agent_id < agents.size(); agent_id++)
            for(size_t action_id = 0; action_id < moves.size(); action_id++)
                if(check_action(agent_id, action_id, false))
                    result[agent_id].push_back(action_id);
        return result;
    }
};
