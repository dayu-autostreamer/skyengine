#include "MCTSCost2Go.h"
#include <iomanip>

Node* MCTSCost2Go::safe_insert_node(Node* parent)
{
    all_nodes.emplace_back();
    all_nodes.back().parent = parent;
    return &all_nodes.back();
}

void MCTSCost2Go::print_input(std::vector<float> input, int obs_radius)
{
    int obs_size(obs_radius*2+1);
    for(int i = 0; i < static_cast<int>(input.size()); i++)
    {
        if(i % obs_size == 0 && i > 0)
            std::cout<<"\n";
        if(i % (obs_size*obs_size) == 0 && i > 0)
            std::cout<<"\n";
        std::cout<<std::setprecision(2)<<std::setw(4)<<input[i]<<" ";
    }
    std::cout<<"\n";
}

float MCTSCost2Go::evaluate_node(Node* node, float reward, std::vector<std::vector<int>> available_actions, std::vector<int> sorted_agents)
{
    node->reward = reward;
    std::vector<std::vector<float>> probabilities;
    std::vector<float> values;
    float value(0);
    if(cfg.use_nn_module)
    {
        for (size_t agent_id = 0; agent_id < env.get_num_agents(); agent_id++) {
            auto input = env.generate_input(agent_id, ppo.obs_radius);
            auto result = ppo.get_output({input, {0}});
            probabilities.push_back(result.first);
            values.push_back(result.second);
            value += values.back();
        }
        value /= values.size();

    }
    else {
        for (size_t agent_id = 0; agent_id < env.get_num_agents(); agent_id++)
            probabilities.push_back(std::vector<float>(available_actions[agent_id].size(), 1.0/available_actions[agent_id].size()));
        value = env.run_simulation();
    }
    node->visit_count = 1;
    node->value_sum = value;
    for(size_t agent_id = 0; agent_id < env.get_num_agents(); agent_id++) {
        if (static_cast<int>(agent_id) < cfg.agents_to_plan)
            node->masked_actions.push_back(available_actions[agent_id]);
        else {
            if(cfg.use_nn_module) {
                int max_elem = std::distance(probabilities[agent_id].begin(),
                                             std::max_element(probabilities[agent_id].begin(),
                                                              probabilities[agent_id].end()));
                node->masked_actions.push_back({max_elem});
            }
            else {
                node->masked_actions.push_back({available_actions[agent_id][generator()%available_actions[agent_id].size()]});
            }
        }
    }
    int num_children(1);
    for(auto m:node->masked_actions)
        num_children *= m.size();
    float prob_sum(0);
    for(int c = 0; c < num_children; c++) {
        int child(c);
        std::vector<int> actions;
        float probability(1.0);
        for(size_t agent_id = 0; agent_id < env.get_num_agents(); agent_id++) {
            actions.push_back(node->masked_actions[agent_id][child % node->masked_actions[agent_id].size()]);
            if(node->masked_actions[agent_id].size() > 1)
                probability *= probabilities[agent_id][actions.back()];
            child /= node->masked_actions[agent_id].size();
        }
        node->children.push_back(safe_insert_node(node));
        node->children.back()->prior = probability;
        prob_sum += probability;
    }
    for(Node* child: node->children)
        child->prior /= prob_sum;
    return value;
}

float MCTSCost2Go::ucb_score(Node *parent, Node* child)
{
    float pb_c = cfg.pb_c_init;
    pb_c *= std::sqrt(parent->visit_count)/(child->visit_count + 1);
    float value_score(0);
    if(child->visit_count > 0)
        value_score = minMaxStats.normalize(child->reward + cfg.gamma*child->get_value());
    return pb_c * child->prior + value_score;
}

void MCTSCost2Go::add_exploration_noise(Node *node, float frac)
{
    float noise = 1.0/node->children.size();
    for(Node* c: node->children)
        c->prior = c->prior*(1 - frac) + noise * frac;
}

Node* MCTSCost2Go::lookahead_search(std::vector<int> sorted_agents, bool debug)
{
    all_nodes.clear();
    Node* root = safe_insert_node(nullptr);
    root->value_sum = 0;
    evaluate_node(root, 0, env.get_available_actions(), sorted_agents);
    add_exploration_noise(root, cfg.random_action_chance);
    minMaxStats = MinMaxStats();
    std::vector<Agent> init_state;
    for(int i = 0; i < cfg.num_expansions; i++) {
        init_state = env.agents;
        std::vector<Node*> search_path = {root};
        float reward(0);
        while(!search_path.back()->children.empty()) {
            std::vector<float> ucb_scores;
            for(auto child: search_path.back()->children)
                ucb_scores.push_back(ucb_score(search_path.back(), child));
            int best_child = std::distance(ucb_scores.begin(), std::max_element(ucb_scores.begin(), ucb_scores.end()));
            reward = env.step(search_path.back()->get_actions(best_child));
            search_path.push_back(search_path.back()->children[best_child]);
        }
        float v = evaluate_node(search_path.back(), reward, env.get_available_actions(), sorted_agents);
        float r = search_path.back()->reward;
        search_path.pop_back();
        for(int k = search_path.size() - 1; k >= 0; k--) {
            minMaxStats.update(v);
            search_path[k]->value_sum += r + cfg.gamma * v;
            search_path[k]->visit_count += 1;
            v = search_path[k]->reward + cfg.gamma * v;
        }
        env.agents = init_state;
    }
    if(debug)
    {
        show_children(root);
    }
    return root;
}

void MCTSCost2Go::show_children(Node* node, int show_max_agents)
{
    std::cout<<node->children.size()<<" children size\n";
    for(size_t i = 0; i < node->children.size(); i++){
        std::cout<<"actions: ";
        auto actions = node->get_actions(i);
        for(auto a:actions)
            std::cout<<a<<" ";
        std::cout<<std::setprecision(3)<<" ucb_score:"<<ucb_score(node, node->children[i])<<" cnt:"<< node->children[i]->visit_count<<" prior:"<<node->children[i]->prior<<" reward:"<<node->children[i]->reward<<" value:"<<minMaxStats.normalize(node->children[i]->get_value())<<"\n";
    }
}

int MCTSCost2Go::run(const Environment &env_, std::vector<int> active_agents_, int agent_idx)
{
    active_agents = active_agents_;
    env.add_agents(env_, active_agents_);
    auto root = lookahead_search(active_agents_, cfg.render);

    return root->select_action(true)[0];
}