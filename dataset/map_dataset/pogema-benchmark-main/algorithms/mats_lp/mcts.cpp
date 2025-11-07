//cppimport
#include "mcts.hpp"

std::mutex insert_mutex;
namespace py = pybind11;

void Decentralized_MCTS::set_env(Environment env_, int merging_range_)
{
    env = std::move(env_);
    merging_range = merging_range_;
    agents.clear();
    for(size_t i = 0; i < env.get_num_agents(); i++)
        agents.push_back(MCTSCost2Go(env, cfg));
    generator = std::mt19937(0);
}

void Decentralized_MCTS::set_config(const Config& config)
{
    cfg = config;
    actor = NN_module(cfg.path_to_weights);
}

std::vector<int> Decentralized_MCTS::find_and_sort_agents(int agent_idx)
{
    std::vector<int> result = {agent_idx};
    std::queue<std::pair<int, int>> fringe;
    fringe.push(env.agents[agent_idx].cur_position);
    auto visited = env.grid;
    std::set<std::pair<int, int>> other_agents_positions;
    for(size_t k = 0; k < env.get_num_agents(); k++)
    {
        if(k == static_cast<size_t>(agent_idx))
            continue;
        if(abs(env.agents[agent_idx].cur_position.first - env.agents[k].cur_position.first) <= cfg.obs_radius &&
            abs(env.agents[agent_idx].cur_position.second - env.agents[k].cur_position.second) <= cfg.obs_radius)
            other_agents_positions.insert(env.agents[k].cur_position);
    }
    while(!fringe.empty())
    {
        auto pos = fringe.front();
        fringe.pop();
        for(const auto& move: env.moves)
        {
            std::pair<int, int> new_pos = {pos.first + move.first, pos.second + move.second};
            if(visited[new_pos.first][new_pos.second] != 0)
                continue;
            visited[new_pos.first][new_pos.second] = visited[pos.first][pos.second] - 1;
            fringe.push(new_pos);
            if(visited[new_pos.first][new_pos.second] < -merging_range)
                break;
            if(other_agents_positions.count(new_pos) > 0)
                for(size_t k = 0; k < env.get_num_agents(); k++)
                    if(new_pos.first == env.agents[k].cur_position.first && new_pos.second == env.agents[k].cur_position.second)
                    {
                        result.push_back(k);
                        break;
                    }
        }
    }
    return result;
}

bool comparator(const std::vector<int>& a, const std::vector<int>& b)
{
    return a.size() > b.size();
}

std::map<int, int> Decentralized_MCTS::get_actions(std::vector<std::vector<int>> active_agents)
{
    std::map<int, int> result;
    for(size_t i = 0; i < active_agents.size(); i++)
        result[active_agents[i][0]] = agents[active_agents[i][0]].run(env, active_agents[i], active_agents[i][0]);
    return result;
}

std::vector<int> Decentralized_MCTS::act()
{
    cur_step++;
    if(cfg.ppo_only) {
        std::vector<int> actions;
        for (size_t agent_id = 0; agent_id < env.get_num_agents(); agent_id++) {
            auto input = env.generate_input(agent_id, actor.obs_radius);
            auto result = actor.get_output({input, {0}});
            std::vector<int> score;
            for (auto v: result.first)
                score.push_back(v * 1e6);
            std::discrete_distribution<int> d(score.begin(), score.end());
            actions.push_back(d(generator));
        }
        env.step(actions, true);
        if (cfg.render)
            env.render();
        return actions;
    }
    else {
        BS::thread_pool pool(cfg.num_threads);
        std::vector<int> actions(env.get_num_agents(), 0);
        if(env.on_target == On_target::restart)
            for(size_t i = 0; i < env.get_num_agents(); i++)
                if(env.reached_goal(i))
                    env.set_next_goal(i);
        std::vector<std::vector<int>> active_agents(env.get_num_agents());
        std::vector<std::future<std::vector<int>>> active_agents_futures;
        for(size_t i = 0; i < env.get_num_agents(); i++)
            active_agents_futures.push_back(pool.submit(&Decentralized_MCTS::find_and_sort_agents, this, i));
        for(size_t i = 0; i < env.get_num_agents(); i++)
            active_agents[i] = active_agents_futures[i].get();
        std::sort(active_agents.begin(), active_agents.end(), comparator);
        std::vector<std::vector<std::vector<int>>> batched_tasks(cfg.num_threads);
        for(size_t i = 0; i < env.get_num_agents(); i++)
            batched_tasks[i%cfg.num_threads].push_back(active_agents[i]);

        std::vector<std::future<std::map<int, int>>> futures;
        for(size_t i = 0; i < cfg.num_threads; i++)
            futures.push_back(pool.submit(&Decentralized_MCTS::get_actions, this, batched_tasks[i]));
        for(size_t i = 0; i < cfg.num_threads; i++)
        {
            std::map<int, int> some_actions = futures[i].get();
            for(auto it = some_actions.begin(); it != some_actions.end(); it++)
                actions[it->first] = it->second;
        }
        env.step(actions, true);
        env.terminate_agents();
        if(cfg.render)
            env.render();
        return actions;
    }
}


PYBIND11_MODULE(mcts, m) {
    py::class_<Decentralized_MCTS>(m, "Decentralized_MCTS")
            .def(py::init<>())
            .def("act", &Decentralized_MCTS::act)
            .def("set_config", &Decentralized_MCTS::set_config)
            .def("set_env", &Decentralized_MCTS::set_env)
            ;
}

<%
cfg['libraries'] = ['onnxruntime']
cfg['sources'] = ['MCTSCost2Go.cpp']
cfg['extra_compile_args'] = ['-std=c++17']
setup_pybind11(cfg)
%>