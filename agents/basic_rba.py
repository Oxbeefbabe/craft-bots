import math
import random

from api import agent_api


class Basic_RBA:
    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info
        self.needed_orange = 0
        self.tasks = []
        self.actors = []

        self.api: agent_api.AgentAPI

        for actor in self.api.actors:
            self.actors.append(Actor_Info(actor, api))

        # Go to orange
        # Mine at orange
        # Pick up required orange
        # Go to / start site
        # Deposit orange to site
        # Pick up red / blue
        # Deposit red / blue to site
        # Pick up / drop off black to site
        # Pick up / drop off green to site
        # Build


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
            for i in range(num):
                tasks.append(list(available_tasks.keys())[i])
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
            if not self.api.get_field(actor.id, "state"):
                if actor.auto_run:
                    actor.pop()
                    if not actor.command_queue:
                        actor.auto_run = False
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

    def __init__(self, actor_id, api, auto_run=False, task=None):
        self.id = actor_id
        self.api = api
        self.command_queue = []
        self.auto_run = auto_run
        self.task = task


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

    def solve_task(self):
        self.api : agent_api.AgentAPI
        self.command_queue = []
        needed_resources = self.api.get_field(self.task, "needed_resources")
        held_resources = [0, 0, 0, 0, 0]
        current_node = self.api.get_field(self.id, "node")
        task_node = self.api.get_field(self.task, "node")


        for resource_type in range(len(needed_resources)):
            resource_amount = needed_resources[resource_type]
            if resource_amount:
                mine, mine_node = self.find_mine(current_node, resource_type)
                self.go_to(mine_node, current_node)
                current_node = mine_node
                for _ in range(resource_amount):
                    self.push(self.api.dig_at, mine)
                for _ in range(resource_amount):
                    self.push(self.pick_up_resource_of, resource_type, include_actor=False)

        self.go_to(task_node, current_node)
        current_node = task_node

        self.push(self.api.start_site, 0 , self.task)
        self.push(self.finish_off_site, include_actor=False)

    def pick_up_resource_of(self, colour):
        for resource in self.api.get_field(self.api.get_field(self.id, "node"), "resources"):
            if self.api.get_field(resource, "colour") == colour:
                self.push(self.api.pick_up_resource, resource, to_front=True)
                return

    def finish_off_site(self):
        #deposits all resources in inventory into a site and starts construction
        if self.api.get_field(self.id, "node") == self.api.get_field(self.task, "node"):
            site = self.api.get_field(self.task, "project")
            # print(self.api.get_by_id(self.task))
            self.push(self.api.construct_at, site)
            resources = self.api.get_field(self.id, "resources")
            for resource in self.api.get_field(self.id, "resources"):
                self.push(self.api.deposit_resources, site, resource, to_front=True)

    def go_to(self, target_node, start_node = None):
        if start_node is None:
            start_node = self.api.get_field(self.id, "node")
        path = self.bfs_pathfinding(start_node, target_node)
        if path:
            for node in path:
                self.push(self.api.move_to, node)

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
                        return (mine, current_path[0][-1])
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
                if current_path[0][-1] == end_node: return current_path[0]
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
