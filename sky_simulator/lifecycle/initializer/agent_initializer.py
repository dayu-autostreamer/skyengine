from sky_simulator.registry.factory import create_component_by_id

def initialize_agent(config):
    agent_config = config.get(config.get("env_type")).get("agent")
    agent = create_component_by_id(agent_config.get("agent_name"), agent_config.get("name"), agent_config.get("id"))
    return agent
