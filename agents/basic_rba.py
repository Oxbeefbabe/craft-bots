import math
import random

from api import agent_api

INVENTORY_SIZE = 3

class Basic_RBA:
    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info
        self.needed_orange = 0
        self.tasks = []
        self.actors = []
        self.active_mines = []
        self.reserved_resources = []

        self.api: agent_api.AgentAPI

        for actor in self.api.actors:
            self.actors.append(Actor_Info(actor, api, self))


    def get_tasks(self, num):
        tasks = []
        available_tasks = self.world_info["tasks"]
        assigned_tasks = []
        for actor in self.actors:
            if actor.task is not None: assigned_tasks.append(actor.task)

        for task_id in list(available_tasks.keys())[:]:
            if available_tasks[task_id]["completed"]() or assigned_tasks.__contains__(task_id):
                available_tasks.pop(task_id)
        try:
            available_tasks = list(available_tasks.keys())
            if len(available_tasks) < num : available_tasks.extend(assigned_tasks)
            for i in range(num):
                tasks.append(available_tasks.pop())
        except IndexError:
            pass

        return tasks

    def get_next_commands(self):
        self.api: agent_api.AgentAPI

        for actor in self.actors:
            if actor.task is not None:
                if self.api.get_field(actor.task, "completed")():
                    actor.task = None
                    actor.auto_run = False
                elif actor.auto_run:
                    actor.update()
                    if not self.api.get_field(actor.id, "state"):
                        actor.pop()
                        if not actor.command_queue:
                            actor.auto_run = False
                elif not actor.command_queue and not self.api.get_field(actor.id, "state"):
                    actor.solve_task()
                    actor.auto_run = True

            else:
                self.assign_tasks([actor])
                if actor.task is not None:
                    actor.solve_task()
                    actor.auto_run = True


        self.thinking = False

    def assign_tasks(self, actors):
        tasks = self.get_tasks(len(actors))
        if tasks:
            for actor in actors:
                actor.task = tasks.pop()
        else:
            print("No tasks remaining")


class Actor_Info:
    """
    A class used to hold some information about a specific actor and provide a bit of automation for execution of a
    series of commands. Commands are stored in a queue and this class can be used to automatically execute those
    commands in order. Commands in the queue consist of a couple with a command ID and a list of arguments.

    """

    resource_colour = ["Red","Blue","Orange","Black","Green"]

    def __init__(self, actor_id, api, master, auto_run=False, task=None):
        self.id = actor_id
        self.api = api
        self.command_queue = []
        self.auto_run = auto_run
        self.task = task
        self.master = master

    def update(self):
        if self.api.get_field(self.id, "state") == 2: # Digging

            current_node = self.api.get_field(self.id, "node")
            target_colour = self.api.get_field(self.api.get_field(self.id, "target"), "colour")
            viable_resources = list(
                filter(lambda resource_id: self.api.get_field(resource_id, "colour") == target_colour,
                       self.api.get_field(current_node, "resources")))

            mine_tracker = list(filter(lambda mine: mine["actors"].__contains__(self.id), self.master.active_mines))[0]
            if len(viable_resources) >= sum(list(map(lambda amount_tracker: amount_tracker[1] ,mine_tracker["target_amount"]))):
                resource_amount = list(filter(lambda amount_tracker: amount_tracker[0] == self.id ,mine_tracker["target_amount"]))[0][1]
                self.say(
                    f"{len(viable_resources)} {self.resource_colour[target_colour]} resources collected, of which I need {resource_amount}. Picking up now.", True)
                self.api.cancel_action(self.id)
                self.pick_up_x_resources(target_colour, resource_amount)
                mine_tracker["actors"].remove(self.id)
                if not mine_tracker["actors"]:
                    self.master.active_mines.remove(mine_tracker)
            else:

                if not self.command_queue[0][0].__name__ == "dig_at":
                    self.push(self.api.dig_at, self.api.get_field(self.id, "target"), to_front=True)

    def execute_command(self, command):
        command[0](*command[1])

    def pop(self):
        if self.command_queue:
            command =self.command_queue[0]
            self.command_queue = self.command_queue[1:]
            self.execute_command(command)

    def push(self, command, *args, to_front=False, include_actor=True):
        """
        Function to push commands to the command queue of the actor.
        * Note: When giving args to command do not include actor ID
        :param command: api call for command
        :param *args: args not including actor ID
        """

        if include_actor:
            args = (self.id,) + args
        if to_front:
            self.command_queue.insert(0,(command,args))
        else:
            self.command_queue.append((command, args))

        #print(self.command_queue)

    def say(self, message, now=False):
        self.push(print, f"[{self.id}] {message}", to_front=now, include_actor=False)

    def solve_task(self):
        self.api : agent_api.AgentAPI

        self.command_queue = []
        needed_resources = self.api.get_field(self.task, "needed_resources")
        # held_resources = [0, 0, 0, 0, 0]
        # current_node = self.api.get_field(self.id, "node")
        task_node = self.api.get_field(self.task, "node")


        for resource_type in range(len(needed_resources)):
            resource_amount = needed_resources[resource_type]
            if resource_amount:
                self.say(f"Starting to gather {resource_amount} {self.resource_colour[resource_type]} resource(s)")
                self.push(self.dig_for_resource, resource_type, resource_amount, include_actor=False)

        self.say(f"Going to finish task {self.task} in node {task_node}")
        self.push(self.go_to, task_node, None, True, include_actor=False)

        self.say(f"Arrived at node {task_node}. Beginning construction")
        self.push(self.api.start_site, 0 , self.task)
        self.push(self.read_assigned_site, include_actor=False)
        self.push(self.finish_off_site, include_actor=False)
        self.say(f"I've been assigned task {self.task} and I am solving it", True)

    def read_assigned_site(self):
        self.say(f"Site {self.api.get_field(self.task, 'project')} created, finishing it off")

    def pick_up_x_resources (self, colour, amount = 1):
        current_node = self.api.get_field(self.id, "node")
        viable_resources = list(
            filter(lambda resource_id: self.api.get_field(resource_id, "colour") == colour,
                   self.api.get_field(current_node, "resources")))

        viable_resources = list(filter(lambda resource_id : not self.master.reserved_resources.__contains__(resource_id), viable_resources))

        for i in range(amount):
            self.push(self.pick_up_resource, viable_resources[i], to_front=True, include_actor=False)
            self.master.reserved_resources.append(viable_resources[i])

    def pick_up_resource(self, id):
        self.api.pick_up_resource(self.id, id)
        self.master.reserved_resources.remove(id)

    def finish_off_site(self):
        #deposits all resources in inventory into a site and starts construction
        if self.api.get_field(self.id, "node") == self.api.get_field(self.task, "node"):
            site = self.api.get_field(self.task, "project")
            # print(self.api.get_by_id(self.task))
            self.say(f"Building at site {site}")
            self.push(self.api.construct_at, site)

            needed_resources = self.api.get_field(self.task, "needed_resources")[:]
            for resource in self.api.get_field(self.id, "resources"):
                needed_resources[self.api.get_field(resource,"colour")] -= 1

            for resource in self.api.get_field(self.api.get_field(self.id, "node"), "resources"):
                if needed_resources[self.api.get_field(resource,"colour")] > 0:
                    self.push(self.api.deposit_resources, site, resource, to_front=True)
                    self.push(self.api.pick_up_resource, resource, to_front=True)
                    needed_resources[self.api.get_field(resource, "colour")] -= 1

            for resource in self.api.get_field(self.id, "resources"):
                self.say(f"Depositing resource {resource} into site {site}", True)
                self.push(self.api.deposit_resources, site, resource, to_front=True)

    def go_to(self, target_node, start_node = None, now = False):
        if start_node is None:
            start_node = self.api.get_field(self.id, "node")
        path, _ = self.bfs_pathfinding(start_node, target_node)
        if path:
            for node in path[::(-1 if now else 1)]:
                self.push(self.api.move_to, node, to_front=now)

    def find_mine(self, node, colour):
        # finds the closest mine of the given colour to the specific node

        def smallest_key(frontier):
            shortest_path = math.inf
            shortest_key = None
            for path in frontier.keys():
                if frontier[path][1] < shortest_path:
                    shortest_path = frontier[path][1]
                    shortest_key = path
            return shortest_key

        # nodes are referenced as their ID's
        current_path = ([node],0)
        frontier = {node: current_path}
        explored = {}
        while True:
            if frontier:
                current_path = frontier.pop(smallest_key(frontier))
                mines = self.api.get_field(current_path[0][-1], "mines")
                for mine in mines:
                    if self.api.get_field(mine, "colour") == colour:
                        return (mine, current_path[0][-1], current_path[1])
                explored[current_path[0][-1]] = current_path
                for edge in self.api.get_field(current_path[0][-1], "edges"):
                    # edge is id of an edge connected to current_path[0][-1]
                    length = self.api.get_field(edge, "length")
                    next_node = self.api.get_field(edge, "get_other_node")(current_path[0][-1])
                    path = current_path[0][:]
                    path.append(next_node)
                    new_path = (path, current_path[1] + length)
                    if explored.__contains__(next_node) and explored[next_node][1] > new_path[1]:
                        explored[next_node] = new_path
                    elif not frontier.__contains__(next_node) or frontier[next_node][1] > new_path[1]:
                        frontier[next_node] = new_path
            else: return None

    def bfs_pathfinding(self, start_node, end_node):

        def smallest_key(frontier):
            shortest_path = math.inf
            shortest_key = None
            for path in frontier.keys():
                if frontier[path][1] < shortest_path:
                    shortest_path = frontier[path][1]
                    shortest_key = path
            return shortest_key

        # nodes are referenced as their ID's
        current_path = ([start_node],0)
        frontier = {start_node: current_path}
        explored = {}
        while True:
            if frontier:
                current_path = frontier.pop(smallest_key(frontier))
                if current_path[0][-1] == end_node: return current_path[0], current_path[1]
                explored[current_path[0][-1]] = current_path
                for edge in self.api.get_field(current_path[0][-1], "edges"):
                    # edge is id of an edge connected to current_path[0][-1]
                    length = self.api.get_field(edge, "length")
                    next_node = self.api.get_field(edge, "get_other_node")(current_path[0][-1])
                    path = current_path[0][:]
                    path.append(next_node)
                    new_path = (path, current_path[1] + length)
                    if explored.__contains__(next_node) and explored[next_node][1] > new_path[1]:
                        explored[next_node] = new_path
                    elif not frontier.__contains__(next_node) or frontier[next_node][1] > new_path[1]:
                        frontier[next_node] = new_path
            else: return []

    def dig_for_resource(self, colour, amount, target_mine = None):
        # Save the current node id for future reference
        current_node = self.api.get_field(self.id, "node")
        inventory = self.api.get_field(self.id, "resources")

        #If I'm currently holding a black resource
        if 3 in list(map(lambda resource: self.api.get_field(resource, "colour"), self.api.get_field(self.id, "resources"))):
            self.push(self.dig_for_resource, colour, amount, include_actor=False, to_front=True)
            self.push(self.api.drop_all_resources, to_front=True)
            self.go_to(self.api.get_field(self.task, "node"), now=True)
            return

        #If I do not have the space for the resources I need
        current_amount = amount
        if len(inventory) + current_amount > INVENTORY_SIZE or colour == 3:
            current_amount = (INVENTORY_SIZE - len(inventory)) if not colour == 3 else 1 if not len(inventory) else 0
            later_amount = max(amount - current_amount,0)
            if current_amount <= 0:
                self.push(self.dig_for_resource, colour, amount, include_actor=False, to_front=True)
                self.push(self.api.drop_all_resources, to_front=True)
                self.go_to(self.api.get_field(self.task, "node"), now=True)
                self.say(
                    f"My inventory is full. I'll drop off what I have and get {amount} later",
                    now=True)
            else:
                if later_amount:
                    self.push(self.dig_for_resource, colour, later_amount, include_actor=False, to_front=True)
                self.push(self.api.drop_all_resources, to_front=True)
                self.go_to(self.api.get_field(self.task, "node"), now=True)
                self.say(f"I don't have enough space for the {amount} resources I need. I'll get {current_amount} later", now=True)


        if colour == 2:
            # Deal with orange resource
            active_orange_mines = list(filter(lambda active_mine : active_mine["colour"] == 2, self.master.active_mines))
            if active_orange_mines:
                orange_mine_distances = list(map(lambda mine : (self.bfs_pathfinding(current_node, mine["mine_node"]))[1], active_orange_mines))
                closest_mine = active_orange_mines[orange_mine_distances.index(min(orange_mine_distances))]
                self.push(self.api.dig_at, closest_mine["mine_id"], to_front=True)
                self.go_to(closest_mine["mine_node"], current_node, now=True)
                closest_mine["actors"].append(self.id)
                closest_mine["target_amount"].append((self.id, current_amount))
                return
            else:
                mine, mine_node, _ = self.find_mine(self.api.get_field(self.id, "node"), colour)
                self.push(self.api.dig_at, mine, to_front=True)
                self.go_to(mine_node, current_node, now=True)
                self.master.active_mines.append(
                    {"mine_id": target_mine, "mine_node": mine_node, "target_amount": [(self.id, current_amount)], "colour": colour,
                     "actors": [self.id]})
                return
        else:
            # Check if a mine of the right colour exists at this node, if the mine is not given
            if target_mine is None:
                for mine_id in self.api.get_field(current_node, "mines"):
                    if self.api.get_field(mine_id, "colour") == colour:
                        target_mine = mine_id
                        break

            # If the mine needed does not exist, go to closest mine and then do this
            if target_mine is None:
                mine, mine_node, _ = self.find_mine(self.api.get_field(self.id, "node"), colour)
                self.push(self.dig_for_resource, colour, current_amount, mine, to_front=True, include_actor=False)
                self.go_to(mine_node, current_node, now=True)
                return

        # Check if any actors are already digging at my target mine
        for active_mine in self.master.active_mines:
            if active_mine["mine_id"] == target_mine:
                # Squeeze in
                active_mine["actors"].append(self.id)
                active_mine["target_amount"].append((self.id, current_amount))
                self.api.dig_at(self.id, target_mine)
                return

        # Otherwise let other actors know you are here
        self.master.active_mines.append({"mine_id": target_mine, "mine_node": current_node, "target_amount": [(self.id, current_amount)], "colour": colour, "actors":[self.id]})
        self.api.dig_at(self.id, target_mine)