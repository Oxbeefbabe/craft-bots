import math

import api.agent_api

DEBUG = 5
INVENTORY_SPACE = 3
GREEN_DECAY_TIME = 200
ACTOR_MOVE_SPEED = 1
BLACK_HEAVY = True


class TaskAllocator:
    PARALLEL_TASKS = 3

    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info
        self.goal_id = 0

        self.finished_tasks = {}
        self.current_tasks = {}

        self.active_mines = []
        self.reserved_resources = {}
        self.actors = []
        self.idle_actors = {}
        for actor in self.api.actors:
            self.actors.append(ActorController(actor, api, self, True))

    def get_next_commands(self):
        for actor in self.actors:
            actor: ActorController

            if not actor.goal_queue:
                print(f"Actor {actor.id} has no remaining goals in its queue, decomposing some tasks and distributing.")
                self.distribute_goals(self.decompose_tasks(self.get_valid_tasks()))

            if actor.current_goal is None and not actor.command_queue:
                print(f"Actor {actor.id} has no current goal, popping a new one from its queue.")
                actor.pop_goal()

            if actor.auto_run:
                actor.update()
                if not self.api.get_field(actor.id, "state"):
                    if actor.command_queue:
                        actor.pop()
                        if actor.id in self.idle_actors: self.idle_actors.pop(actor.id)
                    elif actor.current_goal is not None:
                        if not self.idle_actors.__contains__(actor.id):
                            self.idle_actors[actor.id] = self.world_info["tick"]
                        elif self.idle_actors[actor.id] + 500 < self.world_info["tick"]:
                            actor.say("I've not finished my goal but I have no more commands.")
                            actor.say("Something has probably gone wrong, I'm going to try again.")
                            actor.solve_goal()

    def get_goal_id(self):
        self.goal_id += 1
        return self.goal_id - 1

    def decompose_tasks(self, tasks):
        goals = []

        for task in tasks.values():
            for i, n in enumerate(task["needed_resources"]):
                if n:
                    if i == 2:
                        goals.append(Goal(self.get_goal_id(), Goal.DIG, [n - n//2, i], task["id"]))
                        goals.append(Goal(self.get_goal_id(), Goal.DIG, [n//2, i], task["id"]))
                    else:
                        goals.append(Goal(self.get_goal_id(), Goal.DIG, [n, i], task["id"]))

            for i, n in enumerate(task["needed_resources"]):
                if n:
                    goals.append(Goal(self.get_goal_id(), Goal.DELIVER, [n, i, task["node"]], task["id"]))

            # goals.append(Goal(self.get_goal_id(), Goal.CREATE_SITE, [task["node"]], task["id"]))
            goals.append(Goal(self.get_goal_id(), Goal.FINISH_SITE, [task["node"]], task["id"]))

        return goals

    def distribute_goals(self, goals):
        i = len(self.actors)
        a = 0
        while goals:
            self.actors[a].goal_queue.append(goals.pop(0))
            a = (a + 1) % i

    def get_valid_tasks(self):
        tasks = {}

        # Skip completed tasks, tasks that have been decomposed already, and tasks where the deadline has passed
        # Otherwise add them to new dict until len(dict) is equal to PARALLEL_TASKS or no tasks remain
        for task_id in self.world_info["tasks"].keys():
            if not (self.world_info["tasks"][task_id]["completed"]() or self.finished_tasks.keys().__contains__(
                    task_id) or self.current_tasks.keys().__contains__(task_id)):
                tasks.__setitem__(task_id, self.world_info["tasks"][task_id])
                self.current_tasks.__setitem__(task_id, self.world_info["tasks"][task_id])

            if len(tasks) >= self.PARALLEL_TASKS:
                break
        return tasks


class Goal:
    DIG = 0
    DELIVER = 1
    FINISH_SITE = 2

    """
    Dig parameters: [number, type]
    Deliver parameters: [number, type, node]
    Finish Site parameters: [node]
    """

    def __str__(self):

        if self.type == 0:
            type = "Dig"
        elif self.type == 1:
            type = "Deliver"
        else:
            type = "Finish Site"

        return (f"Goal({self.id}, {type}, {self.parameters}, {self.actor}, {self.task})")

    def __repr__(self):
        return self.__str__()

    def __init__(self, id, type, parameters, task, actor=None):
        self.id = id
        self.type = type
        self.parameters = parameters
        self.actor = actor
        self.task = task
        self.completed = False


class ActorController:
    resource_colour = ["Red", "Blue", "Orange", "Black", "Green"]

    def __init__(self, actor_id, api, master, auto_run=False):
        self.id = actor_id
        self.api = api
        self.command_queue = []
        self.goal_queue = []
        self.current_goal = None
        self.auto_run = auto_run
        self.master = master
        self.target = None

    def update(self):
        self.api: api.agent_api.AgentAPI

        if self.api.get_field(self.id, "state") == 2:  # Digging

            current_node = self.api.get_field(self.id, "node")
            target_colour = self.api.get_field(self.api.get_field(self.id, "target"), "colour")
            viable_resources = list(
                filter(lambda resource_id: self.api.get_field(resource_id,
                                                              "colour") == target_colour and (( resource_id not in self.master.reserved_resources) or self.master.reserved_resources[resource_id][0] == self.current_goal.task),
                       self.api.get_field(current_node, "resources")))

            mine_tracker = list(filter(lambda mine: mine["actors"].__contains__(self.id), self.master.active_mines))
            if mine_tracker:
                mine_tracker = mine_tracker[0]
            else:
                return
            if len(viable_resources) >= mine_tracker["target_amount"]:
                resource_amount = self.current_goal.parameters[0]
                self.say(
                    f"{len(viable_resources)} {self.resource_colour[target_colour]} resources collected, of which I need {resource_amount}. Marking for collection.",
                    True)
                self.api.cancel_action(self.id)
                mine_tracker["actors"].remove(self.id)
                if not mine_tracker["actors"]:
                    self.master.active_mines.remove(mine_tracker)

                for resource in self.api.get_field(current_node, "resources"):
                    if resource_amount <= 0: return self.finish_goal()
                    if self.api.get_field(resource,
                                          "colour") == target_colour and not resource in self.master.reserved_resources:
                        self.master.reserved_resources[resource] = (self.current_goal.task, Goal.DELIVER)
                        resource_amount -= 1
                self.finish_goal()
            else:

                if not self.command_queue or not self.command_queue[0][0].__name__ == "dig_at":
                    self.push(self.api.dig_at, self.api.get_field(self.id, "target"), to_front=True)

        elif self.current_goal is None:  # TODO: Figure out why current goal is sometimes None here in the middle of the simulation
            return
        elif self.current_goal.type == Goal.FINISH_SITE and self.api.get_field(self.id,
                                                                               "state") == 0 and self.api.get_field(
                self.id, "node") == self.current_goal.parameters[0]:

            current_node = self.current_goal.parameters[0]

            site = None
            for s in self.api.get_field(current_node, "sites"):
                if self.api.get_field(s, "task") == self.current_goal.task: site = s

            if site is None: return

            needed_resources = self.api.get_field(site, "needed_resources")
            deposited_resources = self.api.get_field(site, "deposited_resources")
            remaining_resources = []

            for i, a in enumerate(needed_resources):
                remaining_resources.append(a - deposited_resources[i])

            if sum(remaining_resources) == 0:
                self.push(self.api.construct_at, site)
                self.push(self.finish_goal, include_actor=False)

            # Deposit Resources from inventory
            for resource in self.api.get_field(self.id, "resources"):
                if remaining_resources[self.api.get_field(resource, "colour")] > 0:
                    remaining_resources[self.api.get_field(resource, "colour")] -= 1
                    self.api.deposit_resources(self.id, site, resource)

            # Pick Up needed resources
            viable_resources = list(
                filter(lambda resource_id: (resource_id in self.master.reserved_resources) and
                                           (self.master.reserved_resources[resource_id] == (
                                               self.current_goal.task, Goal.FINISH_SITE) or
                                            self.master.reserved_resources[resource_id] == (
                                                self.current_goal.task, Goal.DELIVER)),
                       self.api.get_field(current_node, "resources")))

            if viable_resources:
                for resource in viable_resources:
                    if remaining_resources[self.api.get_field(resource, "colour")] > 0:
                        remaining_resources[self.api.get_field(resource, "colour")] -= 1
                        self.master.reserved_resources[resource] = (self.current_goal.task, self.current_goal.type)
                        self.push(self.pick_up_resource, resource, include_actor=False)

        elif isinstance(self.target, tuple) and list(map(lambda actor: actor.id, self.master.actors)).__contains__(
                self.target[0]) and self.api.get_field(self.id, "state") == 0:
            if self.target[1].completed:
                self.solve_goal()
                return

            target_actor = None
            for actor in self.master.actors:
                if actor.id == self.target[0]:
                    target_actor = actor

            if target_actor is None: return

            if target_actor.target is None:
                target_node = self.api.get_field(target_actor.id, "node")
            else:
                if isinstance(target_actor.target, tuple):
                    target_node = self.api.get_field(target_actor.id, "node")
                else:
                    target_node = target_actor.target

            if target_node is None: return

            path, _ = self.bfs_pathfinding(self.api.get_field(self.id, "node"), target_node)
            # if len(path) > 1: self.push(self.api.move_to, path[1], to_front=True)

    def execute_command(self, command):
        command[0](*command[1])

    def pop(self):
        lengthy_commands = ['move_to', 'dig_at', 'construct_at']
        if self.command_queue:
            command = self.command_queue[0]
            self.command_queue = self.command_queue[1:]
            self.execute_command(command)
            if command[0].__name__ not in lengthy_commands: self.pop()

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
            self.command_queue.insert(0, (command, args))
        else:
            self.command_queue.append((command, args))

        # print(self.command_queue)

    def say(self, message, now=False):
        # TODO: Use global DEBUG var to create levels of print messages to adjust how much information is being sent to console.
        # TODO: Add messages with DEBUG levels to everything in the agent.
        self.push(print, f"[{self.id}] {message}", to_front=now, include_actor=False)

    def finish_goal(self):
        self.current_goal = None

    def pop_goal(self):
        # TODO: quick fix, if self.goal_queue should be handled elsewhere
        if self.goal_queue:

            self.current_goal = self.goal_queue.pop(0)
            self.current_goal.actor = self.id

            self.solve_goal()

        else:
            print("No queue to get goal from, likely finished")

    def solve_goal(self):

        if self.master.idle_actors.__contains__(self.id):
            self.master.idle_actors.pop(self.id)

        if self.current_goal.type == Goal.DIG:
            n, colour = self.current_goal.parameters
            self.dig_for_resource(colour, n)
        elif self.current_goal.type == Goal.DELIVER:
            n, colour, node = self.current_goal.parameters
            self.deliver_resources(n, colour, node)
        elif self.current_goal.type == Goal.FINISH_SITE:
            node, = self.current_goal.parameters
            self.finish_off_site(node)

    def pick_up_x_resources(self, colour, amount=1):
        current_node = self.api.get_field(self.id, "node")
        viable_resources = list(
            filter(lambda resource_id: self.api.get_field(resource_id, "colour") == colour,
                   self.api.get_field(current_node, "resources")))

        viable_resources = list(
            filter(
                lambda resource_id: (resource_id in self.master.reserved_resources) and self.master.reserved_resources[
                    resource_id] == (self.current_goal.task, Goal.DELIVER), viable_resources))

        if viable_resources:
            for i in range(amount):
                self.push(self.pick_up_resource, viable_resources[i], to_front=True, include_actor=False)
                self.master.reserved_resources[viable_resources[i]] = (self.current_goal.task, self.id)

    def pick_up_resource(self, id):
        self.api.pick_up_resource(self.id, id)
        # self.master.reserved_resources.pop(id, None)

    def drop_resources(self, amount, colour, receiver):
        resources_to_drop = list(filter(lambda resource: self.api.get_field(resource, "colour") == colour,
                                        self.api.get_field(self.id, "resources")))[:amount]
        for resource in resources_to_drop:
            if receiver is not None:
                self.master.reserved_resources[resource] = receiver
            self.push(self.api.drop_resource, resource)

    def go_to(self, target_node, start_node=None, now=False):
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
        current_path = ([node], 0)
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
            else:
                return None

    def find_resources(self, node, colour, amount):
        # finds the closest mine of the given colour to the specific node
        # TODO: this causes an infinite loop when there is no resource to find. Also, doesnt check if the resource is reserved in any way
        # TODO: if some resources are found but its not enough then more needs to be found later
        def smallest_key(frontier):
            shortest_path = math.inf
            shortest_key = None
            for path in frontier.keys():
                if frontier[path][1] < shortest_path:
                    shortest_path = frontier[path][1]
                    shortest_key = path
            return shortest_key

        # nodes are referenced as their ID's
        current_path = ([node], 0)
        frontier = {node: current_path}
        explored = {}
        while True:
            if frontier:
                current_path = frontier.pop(smallest_key(frontier))
                resources = self.api.get_field(current_path[0][-1], "resources")
                if len(list(filter(lambda resource: self.api.get_field(resource, "colour") == colour
                                                    and resource in self.master.reserved_resources
                                                    and self.master.reserved_resources[resource] ==
                                                    (self.current_goal.task, Goal.DELIVER), resources))) >= amount:
                    return current_path[0][-1]
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
                    elif not (explored.__contains__(next_node) or frontier.__contains__(next_node)) or (
                            frontier.__contains__(next_node) and frontier[next_node][1] > new_path[1]):
                        frontier[next_node] = new_path
            else:
                return None

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
        current_path = ([start_node], 0)
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
            else:
                return []

    def move_goal_to_front(self, goal, send_to_back=False):
        if send_to_back:
            self.goal_queue.append(self.current_goal)
        else:
            self.goal_queue.insert(0, self.current_goal)
        if goal in self.goal_queue:
            self.goal_queue.remove(goal)
        self.goal_queue.insert(0, goal)
        self.finish_goal()
        return

    def set_target(self, target, to_front=False):
        def set(t):
            self.target = t

        self.push(set, target, include_actor=False, to_front=to_front)

    def confirm_resources(self, needed_resources):
        pending_resources = [0, 0, 0, 0, 0]
        for type, amount in enumerate(needed_resources):
            for actor in self.master.actors:

                if actor.current_goal.task == self.current_goal.task:

                    if actor.current_goal.type == Goal.DELIVER or actor.current_goal.type == Goal.DIG:
                        if actor.current_goal.parameters[:2] == [amount, type]:
                            pending_resources[type] += amount

                    for goal in actor.goal_queue:
                        if goal.type == Goal.DELIVER or goal.type == Goal.DIG:
                            if goal.parameters[:2] == [amount, type]:
                                pending_resources[type] += amount

                    for resource in self.master.reserved_resources:
                        if self.master.reserved_resources[resource][0] == self.current_goal.task:
                            resource_type = self.api.get_field(resource, "colour")
                            if resource_type is None: continue
                            pending_resources[resource_type] += 1

            if amount - pending_resources[type] > 0:
                dig_goal = Goal(self.master.get_goal_id, Goal.DIG, [amount - pending_resources[type], type],
                                self.current_goal.task)
                deliver_goal = Goal(self.master.get_goal_id, Goal.DELIVER, [amount - pending_resources[type], type,
                                                                            self.api.get_field(self.current_goal.task,
                                                                                               "node")],
                                    self.current_goal.task)

                receiving_actor = self.master.actors[0]
                for actor in self.master.actors:
                    if len(actor.goal_queue) < len(receiving_actor.goal_queue):
                        receiving_actor = actor

                receiving_actor.goal_queue.insert(0, deliver_goal)
                receiving_actor.goal_queue.insert(0, dig_goal)

    def forget_task(self):
        pass

    def dig_for_resource(self, colour, amount, target_mine=None):
        # Save the current node id for future reference
        current_node = self.api.get_field(self.id, "node")

        if colour == 2:  # orange
            # Deal with orange resource
            active_orange_mines = list(filter(lambda active_mine: active_mine["colour"] == 2, self.master.active_mines))
            if active_orange_mines:
                orange_mine_distances = list(
                    map(lambda mine: (self.bfs_pathfinding(current_node, mine["mine_node"]))[1], active_orange_mines))
                closest_mine = active_orange_mines[orange_mine_distances.index(min(orange_mine_distances))]
                self.set_target(closest_mine["mine_node"])
                self.go_to(closest_mine["mine_node"], current_node)
                self.set_target(None)
                self.push(self.api.dig_at, closest_mine["mine_id"])
                closest_mine["actors"].append(self.id)
                closest_mine["target_amount"] += amount
                return
            else:
                mine, mine_node, _ = self.find_mine(self.api.get_field(self.id, "node"), colour)
                self.set_target(mine_node)
                self.go_to(mine_node, current_node)
                self.set_target(None)
                self.push(self.api.dig_at, mine)
                self.master.active_mines.append(
                    {"mine_id": mine, "mine_node": mine_node, "target_amount": amount, "colour": colour,
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
                mine, mine_node, path_length = self.find_mine(self.api.get_field(self.id, "node"), colour)
                self.set_target(mine_node)
                self.go_to(mine_node, current_node)
                self.set_target(None)
                self.push(self.dig_for_resource, colour, amount, mine, include_actor=False)
                return

        # Check if any actors are already digging at my target mine
        for active_mine in self.master.active_mines:
            if active_mine["mine_id"] == target_mine:
                # Squeeze in
                active_mine["actors"].append(self.id)
                active_mine["target_amount"] += amount
                self.api.dig_at(self.id, target_mine)
                return

        # Otherwise let other actors know you are here
        self.master.active_mines.append(
            {"mine_id": target_mine, "mine_node": current_node, "target_amount": amount, "colour": colour,
             "actors": [self.id]})
        self.api.dig_at(self.id, target_mine)

    def deliver_resources(self, amount, colour, node):
        current_node = self.api.get_field(self.id, "node")

        current_inventory = self.api.get_field(self.id, "resources")

        # If actor does not have enough space in its inventory to get the resources, pick up what you can and come back for more
        # TODO: when more multitasking is implemented, this code always assumes the actors inventory is empty, which will cause issues
        if colour == 3 and amount > 1 and BLACK_HEAVY:
            self.say(f"I can only move 1 black resource at a time.")
            self.goal_queue.insert(0, Goal(self.master.get_goal_id(), Goal.DELIVER, [amount - 1, colour, node],
                                           self.current_goal.task))
            amount = 1
        elif INVENTORY_SPACE < amount:
            new_amount = INVENTORY_SPACE
            self.goal_queue.insert(0, Goal(self.master.get_goal_id(), Goal.DELIVER, [amount - new_amount, colour, node],
                                           self.current_goal.task))
            self.say(
                f"I don't have enough space to pick up {amount} resources. Picking up {new_amount} resources instead.")
            amount = new_amount
        self.current_goal.parameters[0] = amount

        self.say("Looking for resources to collect")
        destination = self.find_resources(current_node, colour, amount)
        if destination is None:
            self.say("Could not find existing resources, determining who is making them")
            for actor in self.master.actors:
                for goal in actor.goal_queue:
                    if goal.type == Goal.DIG and goal.task == self.current_goal.task and goal.parameters:
                        if actor.id == self.id:
                            self.say(f"I was supposed to dig those resources up. Doing that now.")
                            return self.move_goal_to_front(goal)
                        else:
                            return self.set_target((actor.id, goal), True)
            self.say(f"No one is making {amount} {self.resource_colour[colour]} resources. I'll do it instead.")
            self.move_goal_to_front(Goal(self.master.get_goal_id(), Goal.DIG, [amount, colour], self.current_goal.task))

        else:
            self.say(f"Resources found at node {destination}.")
            self.say(f"Going to node {destination}")
            self.set_target(destination)
            self.go_to(destination)
            self.set_target(None)
            self.say(f"Arrived at node {destination}, collecting resources")
            self.push(self.pick_up_x_resources, colour, amount, include_actor=False)
            self.say(f"Resources collected, going to node {node}")
            self.set_target(node)
            self.go_to(node, destination)
            self.set_target(None)
            self.say(f"Arrived at node {node}, dropping resources off")
            self.push(self.drop_resources, amount, colour, (self.current_goal.task, Goal.FINISH_SITE),
                      include_actor=False)
            self.push(self.finish_goal, include_actor=False)
            self.say(f"Finished delivering resource")

    def finish_off_site(self, node):
        def site_exists():
            for site in self.api.get_field(node, "sites"):
                if self.api.get_field(site, "task") == self.current_goal.task: return
            self.push(self.api.start_site, 0, self.current_goal.task, to_front=True)

        self.set_target(node)
        self.go_to(node)
        self.set_target(None)
        self.push(site_exists, include_actor=False)
