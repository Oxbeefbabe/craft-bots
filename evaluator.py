import random
import time
import sys

from craftbots import craft_bots
from os.path import exists

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


def run_evaluator(agents, epochs, modifiers_path, rules_path, world_gen_path, rule_set_name, share_seeds=True, agent_names=None, gui=False):

    # Set agent names to default if none are given, not given in list, or list of agent names is a different length to agent list
    if agent_names is None or (isinstance(agent_names, list) and len(agents) != len(agent_names)):
        agent_names = [ i for i in range(len(agents))]

    # Seed is set therefore seed does not need to be synchronised between agents
    if get_seed(world_gen_path): share_seeds = False
    if share_seeds: world_gen_path = copy_world_gen_file(world_gen_path)

    results = {}

    for name in agent_names: results[name] = []

    for _ in range(epochs):

        seed = int(time.time())

        for index, agent in enumerate(agents):
            results[agent_names[index]].append(craft_bots.start_simulation(agent_class=agent,
                                    use_gui=gui, # Set to False to allow for simulation to be run in the background
                                    modifier_file=modifiers_path,
                                    world_modifier_file=world_gen_path,
                                    rule_file=rules_path,
                                    seed = seed))
            write_results(results[agent_names[index]][-1], rule_set_name, agent_names[index])
    return results


def write_results(result, rule_set_name, agent):
    path = f"{rule_set_name}_{agent}_results.csv"
    if not exists(path):
        with open(path,"a") as file:
            file.write("Seed,"
                       "Score,"
                       "Potential_Score,"
                       "Commands_Sent,"
                       "Failures,"
                       "Tasks_Completed,"
                       "Remaining_Sites,"
                       "Remaining_Resources,"
                       "Actor_Idle_Time,"
                       "Ticks,"
                       "Time_to_Run\n")
            file.close()
    try:
        with open(path, "a") as file:
            actor_idle_string = ""
            for actor in result["actor_idle_time"].keys():
                actor_idle_string += f"{actor}:{result['actor_idle_time'][actor]};"
            file.write(f"{result['seed']},"
                       f"{result['score']},"
                       f"{result['potential_score']},"
                       f"{result['commands_sent']},"
                       f"{result['failures']},"
                       f"{result['tasks_completed']},"
                       f"{result['remaining_sites']},"
                       f"{result['remaining_resources']},"
                       f"{actor_idle_string},"
                       f"{result['ticks']},"
                       f"{result['time_to_run']}\n")
            file.close()
    except:
        sleep_time = random.uniform(0.1, 0.5)
        print(f"Encountered an error writing: waiting for a {int(sleep_time * 1000)}ms")
        time.sleep(sleep_time)
        write_results(result, rule_set_name, agent)
        return


def get_parameters():
    from agents import basic_rba
    from agents import bogo
    from agents import task_allocator

    agents = []
    agent_names = []

    if "RBA" in sys.argv:
        agents.append(basic_rba.Basic_RBA)
        agent_names.append("RBA")

    if "TAA" in sys.argv:
        agents.append(task_allocator.TaskAllocator)
        agent_names.append("TAA")

    rule_set_name = ""

    if "simple" in sys.argv:
        rule_set_name += "simple" + "_"
        if "small" in sys.argv:
            rule_set_name += "small"
        elif "large" in sys.argv:
            rule_set_name += "large"
    elif "complex" in sys.argv:
        rule_set_name += "complex" + "_"
        if "small" in sys.argv:
            rule_set_name += "small"
        elif "large" in sys.argv:
            rule_set_name += "large"

    gui = False
    if "GUI" in sys.argv:
        gui = True

    try:
        if agents and agent_names and rule_set_name:
            return int(sys.argv[1]), agents, agent_names, rule_set_name, gui
        else: return None
    except ValueError:
        return None



if __name__ == '__main__':
    parameters = get_parameters()
    if parameters is not None:

        epochs, agents, agent_names, rule_set_name, gui = parameters

        run_evaluator(agents, epochs,
                                      f"craftbots/initialisation_files/eval/{rule_set_name}/modifiers",
                                      f"craftbots/initialisation_files/eval/{rule_set_name}/rules",
                                      f"craftbots/initialisation_files/eval/{rule_set_name}/world_gen_modifiers",
                                      rule_set_name,
                                      agent_names=agent_names,
                                      gui=gui
                                      )
    else:
        print("Invalid parameters")