import sys

from craftbots.world import World
from api.agent_api import AgentAPI
from agents.blank_agent import BlankAgent
import craftbots.view as view
import threading
import random as r
import math
import time

from entities.building import Building

PADDING = 25
NODE_SIZE = 20

simulation_stop = None
sim_stopped = False
gui_updating = False
root = None
world = World()
start_time = None
ticks_run_this_second = 0
refresh = False
results = []
gui_initialised = False
gui = None
kill_switch = False


def default_scenario(modifiers, world_gen_modifiers):
    global world
    for _ in range(modifiers["NUM_OF_ACTORS"]):
        actor = world.add_actor(world.nodes[r.randint(0, world.nodes.__len__() - 1)])
        for _ in range(world_gen_modifiers["ACTOR_NUM_OF_RED_RESOURCES"]):
            world.add_resource(actor, 0)
        for _ in range(world_gen_modifiers["ACTOR_NUM_OF_BLUE_RESOURCES"]):
            world.add_resource(actor, 1)
        for _ in range(world_gen_modifiers["ACTOR_NUM_OF_ORANGE_RESOURCES"]):
            world.add_resource(actor, 2)
        for _ in range(world_gen_modifiers["ACTOR_NUM_OF_BLACK_RESOURCES"]):
            world.add_resource(actor, 3)
        for _ in range(world_gen_modifiers["ACTOR_NUM_OF_GREEN_RESOURCES"]):
            world.add_resource(actor, 4)
        
    for _ in range(world_gen_modifiers["NUM_OF_RED_RESOURCES"]):
        world.add_resource(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 0)
    for _ in range(world_gen_modifiers["NUM_OF_RED_MINES"]):
        world.add_mine(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 0)

    for _ in range(world_gen_modifiers["NUM_OF_BLUE_RESOURCES"]):
        world.add_resource(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 1)
    for _ in range(world_gen_modifiers["NUM_OF_BLUE_MINES"]):
        world.add_mine(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 1)
        
    for _ in range(world_gen_modifiers["NUM_OF_ORANGE_RESOURCES"]):
        world.add_resource(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 2)
    for _ in range(world_gen_modifiers["NUM_OF_ORANGE_MINES"]):
        world.add_mine(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 2)

    for _ in range(world_gen_modifiers["NUM_OF_BLACK_RESOURCES"]):
        world.add_resource(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 3)
    for _ in range(world_gen_modifiers["NUM_OF_BLACK_MINES"]):
        world.add_mine(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 3)

    for _ in range(world_gen_modifiers["NUM_OF_GREEN_RESOURCES"]):
        world.add_resource(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 4)
    for _ in range(world_gen_modifiers["NUM_OF_GREEN_MINES"]):
        world.add_mine(world.nodes[r.randint(0, world.nodes.__len__() - 1)], 4)

    for key in world_gen_modifiers:

        # initial buildings
        if key.startswith("NUM_BUILDING"):
            for _ in range(world_gen_modifiers[key]):
                building_type_name = key[4:] # removes "NUM_"
                building_type = Building.__dict__[building_type_name]
                world.add_building(world.nodes[r.randint(0, world.nodes.__len__() - 1)], building_type)

        # initial sites
        if key.startswith("NUM_SITE"):
            for _ in range(world_gen_modifiers[key]):
                building_type_name = "BUILDING" + key[9:] # removes "NUM_SITE_"
                building_type = Building.__dict__[building_type_name]
                world.add_site(world.nodes[r.randint(0, world.nodes.__len__() - 1)], building_type)


def start_simulation(agent_class=BlankAgent, use_gui=True, scenario=default_scenario,modifier_file=None,world_modifier_file=None,rule_file=None, refresh_sim_on_end=False, seed = None):
    """
        The command used to start the CraftBots simulation. The simulation will run on a separate thread and the current
        thread will wait for the simulation to finish and return the score achieved.

        :param agent_class: (optional) the class constructor for the Agent to be used. Default: BlankAgent (from agents folder)
        :param use_gui: (optional) if the GUI should be displayed. Default: True
        :param scenario: (optional) the scenario that should be created in the world, regarding actors, mine, resources, sites, and buildings. Documentation to create a scenario still WIP. Default: default_scenario (using modifiers and world_gen_modifiers)
        :param modifier_file: (optional) path to the text file that is used to initialise the modifiers for the simulation. Default: None (the default parameters are used)
        :param world_modifier_file: (optional) path to the text file that is used to initialise the world parameters for the simulation. Default: None (the default parameters are used)
        :param rule_file: (optional) path to the text file that is used to set the rules for the simulation.  Default: None (the default parameters are used)
        :return:
        """
    global ticks_run_this_second, sim_stopped, refresh, root, start_time
    if refresh_sim_on_end:
        while not kill_switch:
            sim_thread = threading.Thread(target=prep_simulation, args=(
                agent_class, use_gui, scenario, modifier_file, world_modifier_file, rule_file, seed), daemon=True)
            sim_thread.start()
            sim_stopped = False
            refresh = True
            while not sim_stopped:
                time.sleep(1) # Wait for the simulation to stop
                root.wm_attributes("-topmost", 1)
                root.focus_force()
            print(f"Current results: {results}")
        return results
    else:
        start_time = time.perf_counter()
        sim_thread = threading.Thread(target=prep_simulation, args=(agent_class, use_gui, scenario, modifier_file, world_modifier_file, rule_file, seed), daemon=True)
        sim_thread.start()
        sim_stopped = False
        while not sim_stopped:
            time.sleep(1)

            # sys.stdout.write(f"\rTick rate: {ticks_run_this_second}")
            # sys.stdout.flush()
            ticks_run_this_second = 0
        return get_results()


def prep_simulation(agent_class, use_gui, scenario, modifier_file, world_modifier_file, rule_file, seed):
    global world, view, gui, gui_initialised
    world_gen_modifiers = get_world_gen_modifiers(world_modifier_file)
    modifiers = get_modifiers(modifier_file)
    rules = get_rules(rule_file)
    if seed is not None:
        world_gen_modifiers["RANDOM_SEED"] = seed
    world = World(modifiers, world_gen_modifiers, rules)
    scenario(modifiers, world_gen_modifiers)

    if rules["LIMITED_COMMUNICATIONS"]:
        agents = []
        for actor in world.actors:
            api = AgentAPI(world, [actor.id])
            new_agent = agent_class(api, api.get_world_info())
            agents.append(new_agent)
    else:
        actor_ids = []
        for actor in world.actors:
            actor_ids.append(actor.id)
        api = AgentAPI(world, actor_ids)
        agents = [agent_class(api, api.get_world_info())]

    if rules["RT_OR_LOCK_STEP"] == 0:
        global simulation_stop
        simulation_stop = call_repeatedly(1 / rules["TICK_HZ"], refresh_world, agents)

        if use_gui:
            gui = init_gui()
            refresh_gui(gui, rules["TICK_HZ"])
            gui.mainloop()

    else:
        if use_gui:
            if not gui_initialised: gui = init_gui()
            else: gui.world = world
            gui.draw_world()
            sim_thread = threading.Thread(target=lock_step_sim, args=(agents, gui.update_model))
            sim_thread.start()
            if not gui_initialised:
                gui_initialised = True
                gui.mainloop()

        else:
            sim_thread = threading.Thread(target=lock_step_sim, args=(agents, None))
            sim_thread.start()


def lock_step_sim(agents, update_model):
    global world, ticks_run_this_second
    while not sim_stopped:
        for agent in agents:
            agent.world_info = agent.api.get_world_info()
            agent.get_next_commands()


        #time.sleep(1 / world.rules["LOCK_STEP_RATE"])
        world.run_tick()
        ticks_run_this_second += 1

        for agent in agents:
            agent.api.num_of_current_commands = 0


        if world.world_gen_modifiers["REFRESH_TASKS"] == 0 and world.modifiers["NEW_TASK_CHANCE"] == 0 and world.tasks_complete():
            return on_close()

        if world.rules["TIME_LENGTH_TYPE"] == 0:
            if time.time() - world.rules["SIM_LENGTH"] >= start_time:
                return on_close()
        else:
            if world.tick >= world.rules["SIM_LENGTH"] * world.rules["TICK_HZ"]:
                return on_close()

        if update_model is not None:
            update_model()


def refresh_gui(gui, tick_hz):

    def refresh_gui_wrapper():
        if not sim_stopped:
            global gui_updating
            gui_updating = True
            gui.update_model()
            gui_updating = False
            refresh_gui(gui, tick_hz)

    gui.after(math.ceil(1000 / tick_hz), refresh_gui_wrapper)


def refresh_world(agents):
    global world, ticks_run_this_second
    for agent in agents:
        if not agent.thinking:
            agent.thinking = True
            agent.world_info = agent.api.get_world_info()
            agent_thread = threading.Thread(target=agent.get_next_commands)
            agent_thread.start()
    world.run_tick()
    ticks_run_this_second += 1
    for agent in agents:
        agent.api.num_of_current_commands = 0
    if world.rules["TIME_LENGTH_TYPE"] == 0:
        if time.time() - world.rules["SIM_LENGTH"] >= start_time:
            return on_close()
    else:
        if world.tick >= world.rules["SIM_LENGTH"] * world.rules["TICK_HZ"]:
            return on_close()


def call_repeatedly(interval, func, *args):
    stopped = threading.Event()

    def loop():
        while not stopped.wait(interval):  # the first call is in `interval` secs
            func(*args)
    threading.Thread(target=loop, daemon=True).start()
    return stopped.set


def get_results():
    global start_time
    total_time = time.perf_counter() - start_time
    return {"seed": world.seed,
            "score": world.total_score,
            "potential_score": sum(list(map(lambda task: task.get_score(), world.tasks))),
            "commands_sent": world.total_commands,
            "failures": world.failures,
            "tasks_completed": len(list(filter(lambda task: task.completed(), world.tasks))),
            "remaining_sites": len(world.sites),
            "remaining_resources": len(world.resources),
            "actor_idle_time": world.actor_idle_time,
            "ticks": world.tick,
            "time_to_run": total_time,

            }


def init_gui():
    global root, world, gui
    if gui_initialised: return gui
    root = view.tk.Tk()

    width = world.world_gen_modifiers["WIDTH"]
    height = world.world_gen_modifiers["HEIGHT"]
    root.title("CraftBots")
    root.protocol("WM_DELETE_WINDOW", kill_gui)
    root.geometry(str(width + PADDING * 2) + "x" + str(height + PADDING * 2))
    return view.GUI(world, width=width, height=height, padding=PADDING, node_size=NODE_SIZE, master=root)


def on_close():
    global world
    print("\nSimulation time up")
    global sim_stopped, simulation_stop, refresh, results
    if simulation_stop is not None:
        simulation_stop()
    sim_stopped = True
    if refresh:
        results.append(get_results())
        return
    if root is not None:
        try:
            root.destroy()
        except:
            return on_close()
    return world.total_score


def kill_gui():
    global kill_switch
    kill_switch = True
    on_close()
    root.destroy()


def get_world_gen_modifiers(modifier_file):
    return read_ini_file(modifier_file, "craftbots/initialisation_files/default_world_gen_modifiers")


def get_modifiers(modifier_file):
    return read_ini_file(modifier_file, "craftbots/initialisation_files/default_modifiers")
    

def get_rules(rule_file):
    return read_ini_file(rule_file, "craftbots/initialisation_files/default_rules")


def read_ini_file(path, default_path):
    default_file = open(default_path, "r")
    parameters = {}
    for line in default_file:
        data = line.strip("\n").split(" ")
        if data[0] != '' and data[0][0] != "#":
            try:
                parameters[data[0]] = int(data[2])
                continue
            except ValueError:
                try:
                    parameters[data[0]] = float(data[2])
                    continue
                except ValueError:
                    temp = []
                    for value in data[2].split(","):
                        temp.append(int(value))
                    parameters[data[0]] = temp
    default_file.close()

    if path is None: return parameters
    try:
        file = open(path, "r")
        for line in file:
            data = line.strip("\n").split(" ")
            if data[0] != '' and data[0][0] != "#":
                try:
                    parameters[data[0]] = int(data[2])
                    continue
                except ValueError:
                    try:
                        parameters[data[0]] = float(data[2])
                        continue
                    except ValueError:
                        temp = []
                        for value in data[2].split(","):
                            temp.append(int(value))
                        parameters[data[0]] = temp
        file.close()
    except FileNotFoundError:
        pass
    return parameters
