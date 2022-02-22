import time

from craftbots import craft_bots

def get_seed(world_gen_path):
    return craft_bots.get_world_gen_modifiers(world_gen_path)["RANDOM_SEED"]

def set_seed(world_gen_path, seed=None):
    if seed is None: seed = int(time.time())

    # Get world gen file as a list of strings
    with open(world_gen_path, 'r') as world_gen_file:
        world_gen_lines = world_gen_file.readlines()
        world_gen_file.close()

    # Find and replace the seed
    for index, line in enumerate(world_gen_lines):
        if line.split(' ')[0] == "RANDOM_SEED":
            world_gen_lines[index] = f"RANDOM_SEED = {seed}\n"
            break

    # Rewrite world gen file
    with open(f"{world_gen_path}", 'w') as world_gen_file:
        world_gen_file.writelines(world_gen_lines)
        world_gen_file.close()


def copy_world_gen_file(world_gen_path):
    with open(world_gen_path, 'r') as world_gen_file:
        world_gen_lines = world_gen_file.readlines()
        world_gen_file.close()

    with open(f"{world_gen_path}_set_seed", 'w') as world_gen_file:
        world_gen_file.writelines(world_gen_lines)
        world_gen_file.close()

    return f"{world_gen_path}_set_seed"


"""
TODO:  
 - implement testing multiple different rule sets
 - implement some parallel simulation 
"""
def run_evaluator(agents, epochs, modifiers_path, rules_path, world_gen_path, rule_set_name, share_seeds=True, agent_names=None):

    # Set agent names to default if none are given, not given in list, or list of agent names is a different length to agent list
    if agent_names is None or (isinstance(agent_names, list) and len(agents) != len(agent_names)):
        agent_names = [ i for i in range(len(agents))]

    # Seed is set therefore seed does not need to be synchronised between agents
    if get_seed(world_gen_path): share_seeds = False
    if share_seeds: world_gen_path = copy_world_gen_file(world_gen_path)

    results = {}

    for name in agent_names: results[name] = []

    for _ in range(epochs):

        if share_seeds: set_seed(world_gen_path)

        for index, agent in enumerate(agents):
            results[agent_names[index]].append(craft_bots.start_simulation(agent_class=agent,
                                    use_gui=False, # Set to False to allow for simulation to be run in the background
                                    modifier_file=modifiers_path,
                                    world_modifier_file=world_gen_path,
                                    rule_file=rules_path))
    write_results(results, rule_set_name)
    return results


def write_results(results, rule_set_name):
    for agent in results.keys():
        with open(f"{rule_set_name}_{agent}_results.csv", "a") as file:
            for result in results[agent]:
                actor_idle_string = ""
                for actor in result["actor_idle_time"].keys():
                    actor_idle_string += f"{actor}:{result['actor_idle_time'][actor]};"
                file.write(f"{result['score']},"
                           f"{result['commands_sent']},"
                           f"{result['ticks']},"
                           f"{result['seed']},"
                           f"{result['tasks_completed']},"
                           f"{result['remaining_sites']},"
                           f"{result['remaining_resources']},"
                           f"{actor_idle_string},"
                           f"{result['failures']},"
                           f"{result['time_to_run']}\n")
            file.close()
