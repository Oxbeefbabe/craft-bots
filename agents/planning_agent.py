import math
import random
from copy import deepcopy

import api.agent_api


class PlanningAgent:

    MOVE_TO = 0
    PICK_UP_RESOURCE = 2
    DROP_RESOURCE = 3
    DROP_ALL_RESOURCES = 4
    DIG_AT = 5
    START_SITE = 6
    CONSTRUCT_AT = 7
    DEPOSIT_RESOURCES = 8

    IDLE = 0
    MOVING = 1
    DIGGING = 2
    CONSTRUCTING = 3

    ACTOR_MOVE_SPEED = 1
    DIG_SPEED = 3
    BUILD_SPEED = 3
    INVENTORY_SIZE = 3

    MINE_EFFORT = 100
    BUILD_EFFORT = 100

    TASK_SCORE_A = 2
    TASK_SCORE_B = 1
    TASK_SCORE_C = 1.5

    SIM_LENGTH = 240
    TICK_HZ = 60

    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info
        self.current_task = world_info["tasks"][list(world_info["tasks"].keys())[0]]["id"]

        self.plan = self.bfs(world_info)
        print(self.plan)

    def get_next_commands(self):
        self.api : api.agent_api.AgentAPI
        current_tick = self.world_info["tick"]
        if self.plan:
            if current_tick == self.plan[0][-1]:
                current_command = self.plan.pop(0)
                if current_command[1] == self.MOVE_TO:
                    self.api.move_to(current_command[0], current_command[2])
                elif current_command[1] == self.PICK_UP_RESOURCE:
                    self.api.pick_up_resource(current_command[0], current_command[2])
                elif current_command[1] == self.DROP_RESOURCE:
                    self.api.drop_resource(current_command[0], current_command[2])
                elif current_command[1] == self.DROP_ALL_RESOURCES:
                    self.api.drop_all_resources(current_command[0])
                elif current_command[1] == self.DIG_AT:
                    self.api.dig_at(current_command[0], current_command[2])
                elif current_command[1] == self.START_SITE:
                    self.api.start_site(current_command[0], 0, current_command[2])
                elif current_command[1] == self.CONSTRUCT_AT:
                    self.api.construct_at(current_command[0], current_command[2])
                elif current_command[1] == self.DEPOSIT_RESOURCES:
                    self.api.deposit_resources(current_command[0], current_command[2], current_command[3])
        self.thinking = False

    def get_available_commands(self, state):
        info = state.info
        call_tick = info["tick"]
        available_commands = []
        for actor in info["actors"].values():
            if not actor["state"]:
                current_node = info["nodes"][actor["node"]]

                # Move along any edge that is connected to the actors current node
                for edge in current_node["edges"]:
                    available_commands.append(
                        (actor["id"], self.MOVE_TO,
                        info["edges"][edge]["get_other_node"](current_node["id"]), call_tick))

                # Pick up any resources that are on the same node as the actor
                for resource in current_node["resources"]:
                    available_commands.append((actor["id"], self.PICK_UP_RESOURCE, resource, call_tick))

                # Drop any resources that the actor is currently holding onto the node it is at
                for resource in actor["resources"]:
                    available_commands.append((actor["id"], self.DROP_RESOURCE, resource, call_tick))

                # Drop all the resources the actor is currently holding onto the node it is at
                if actor["resources"]:
                    available_commands.append((actor["id"], self.DROP_ALL_RESOURCES, call_tick))

                # Dig at any mines the actor is currently at
                for mine in current_node["mines"]:
                    available_commands.append((actor["id"], self.DIG_AT, mine, call_tick))

                # Start the site of any tasks at the current node if they don't already have a project
                if current_node["id"] == info["tasks"][self.current_task]["node"]:
                    if info["tasks"][self.current_task]["project"] is None:
                        available_commands.append((actor["id"], self.START_SITE, self.current_task, call_tick))

                # Construct at any sites at the node the actor is currently at

                # Deposit any resources in the actors inventory into the site if the site is at the same node and still
                # needs that type of resource
                for site in current_node["sites"]:
                    #print(info["sites"][site]["needed_resources"], info["sites"][site]["deposited_resources"])
                    available_commands.append((actor["id"], self.CONSTRUCT_AT, site, call_tick))

                    remaining_requests = info["sites"][site]["needed_resources"][:]
                    deposited_resources = info["sites"][site]["deposited_resources"][:]
                    for i, r in enumerate(remaining_requests):
                        remaining_requests[i] = r - deposited_resources[i]

                    for resource in actor["resources"]:
                        if remaining_requests[info["resources"][resource]["colour"]]:
                            available_commands.append((actor["id"], self.DEPOSIT_RESOURCES, site, resource, call_tick))

        return available_commands

    def predict_outcome(self, info, command=None):
        new_info = deepcopy(info)
        new_info["tick"] = new_info["tick"] + 1

        for actor_id in new_info["actors"]:
            current_node = new_info["actors"][actor_id]["node"]

            if new_info["actors"][actor_id]["state"] == self.MOVING:
                new_info["actors"][actor_id]["progress"] += self.ACTOR_MOVE_SPEED
                target = new_info["actors"][actor_id]["target"]

                if new_info["actors"][actor_id]["progress"] >= new_info["edges"][target[0]]["length"]:
                    new_info["nodes"][current_node]["actors"].remove(actor_id)
                    new_info["nodes"][target[1]]["actors"].append(actor_id)
                    new_info["actors"][actor_id]["node"] = target[1]
                    new_info["actors"][actor_id]["state"] = self.IDLE

            elif new_info["actors"][actor_id]["state"] == self.DIGGING:
                target = new_info["actors"][actor_id]["target"]
                new_info["mines"][target]["progress"] += self.DIG_SPEED

                if new_info["mines"][target]["progress"] >= self.MINE_EFFORT:
                    new_info["mines"][target]["progress"] = 0
                    new_resource_id = self.get_next_id(new_info)
                    new_info["resources"][new_resource_id] = \
                        {"id": new_resource_id,
                         "location": current_node,
                         "tick_created": new_info["tick"],
                         "used": False,
                         "colour": new_info["mines"][target]["colour"]}
                    new_info["nodes"][current_node]["resources"].append(new_resource_id)

                    for digging_actor in new_info["actors"]:
                        if new_info["actors"][digging_actor]["target"] == target:
                            new_info["actors"][digging_actor]["target"] = None
                            new_info["actors"][digging_actor]["state"] = self.IDLE

            elif new_info["actors"][actor_id]["state"] == self.CONSTRUCTING:
                target = new_info["actors"][actor_id]["target"]
                max_progress = self.BUILD_EFFORT * sum(new_info["sites"][target]["deposited_resources"])
                new_info["sites"][target]["progress"] = max(self.BUILD_SPEED + new_info["sites"][target]["progress"], max_progress)

                if new_info["sites"][target]["progress"] >= self.BUILD_EFFORT * sum(new_info["sites"][target]["needed_resources"]):
                    new_building_id = self.get_next_id(new_info)
                    new_info["buildings"][new_building_id] = \
                        {"node": current_node,
                         "building_type": 0,
                         "id": new_building_id}
                    new_info["nodes"][current_node]["buildings"] = new_building_id

                    for building_actor in new_info["actors"]:
                        if new_info["actors"][building_actor]["target"] == target:
                            new_info["actors"][building_actor]["target"] = None
                            new_info["actors"][building_actor]["state"] = self.IDLE

                    new_info["tasks"][new_info["sites"][target]["task"]]["project"] = new_building_id
                    new_info["nodes"][current_node]["sites"].remove(target)
                    new_info["sites"].pop(target)

        if command is not None:
            current_node = new_info["actors"][command[0]]["node"]
            if command[1] == self.MOVE_TO:
                target_edge = None
                for edge in new_info["nodes"][current_node]["edges"]:
                    if new_info["edges"][edge]["get_other_node"](command[2]) == current_node:
                        target_edge = edge
                new_info["actors"][command[0]]["target"] = (target_edge, command[2])
                new_info["actors"][command[0]]["state"] = self.MOVING
                new_info["actors"][command[0]]["progress"] = 0

            elif command[1] == self.PICK_UP_RESOURCE:
                new_info["nodes"][current_node]["resources"].remove(command[2])
                new_info["actors"][command[0]]["resources"].append(command[2])
                new_info["resources"][command[2]]["location"] = command[0]

            elif command[1] == self.DROP_RESOURCE:
                new_info["nodes"][current_node]["resources"].append(command[2])
                new_info["actors"][command[0]]["resources"].remove(command[2])
                new_info["resources"][command[2]]["location"] = current_node

            elif command[1] == self.DROP_ALL_RESOURCES:
                for resource in new_info["actors"][command[0]]["resources"]:
                    new_info["nodes"][current_node]["resources"].append(resource)
                    new_info["actors"][command[0]]["resources"].remove(resource)
                    new_info["resources"][resource]["location"] = current_node

            elif command[1] == self.DIG_AT:
                new_info["actors"][command[0]]["state"] = self.DIGGING
                new_info["actors"][command[0]]["target"] = command[2]

            elif command[1] == self.START_SITE:
                new_site_id = self.get_next_id(new_info)
                new_info["sites"][new_site_id] = \
                    {"node": current_node,
                     "building_type": 0,
                     "deposited_resources": [0, 0, 0, 0, 0],
                     "needed_resources": new_info["tasks"][command[2]]["needed_resources"][:],
                     "progress": 0,
                     "id": new_site_id,
                     "task": command[2]}
                new_info["nodes"][current_node]["sites"].append(new_site_id)
                new_info["tasks"][command[2]]["project"] = new_site_id

            elif command[1] == self.CONSTRUCT_AT:
                new_info["actors"][command[0]]["state"] = self.CONSTRUCTING
                new_info["actors"][command[0]]["target"] = command[2]

            elif command[1] == self.DEPOSIT_RESOURCES:
                resource_colour = new_info["resources"][command[3]]["colour"]
                new_info["actors"][command[0]]["resources"].remove(command[3])
                new_info["sites"][command[2]]["deposited_resources"][resource_colour] += 1
                new_info["resources"].pop(command[3])

        all_busy = True
        for actor in new_info["actors"]:
            if new_info["actors"][actor]["state"] == self.IDLE:
                all_busy = False

        if all_busy and new_info["tick"] < self.TICK_HZ * self.SIM_LENGTH:
            return self.predict_outcome(new_info)

        return new_info

    def get_next_id(self, info):
        """
        Given a dictionary of world_info, returns what the id a new entity would be given
        :param info: (dict) of CraftBots world info
        :return: (int) the id of a new entity
        """
        max_id = -1
        for key in info:
            if isinstance(info[key], dict):
                for int_key in info[key]:
                    max_id = max(int_key, max_id)
        return max_id + 1
    
    def bfs(self, info):
        c = 0
        current_state = State(info, task = self.current_task)
        queue = [current_state]
        while queue:
            c += 1
            current_state = queue.pop()
            if c % 1 == 0 and c > 1:
                print(f"States checked: {c}, Current heuristic: {current_state.score}, Last command : {current_state.path[-1]} ,Tick: {current_state.info['tick']}, True Score: {current_state.true_score()}, Queue length: {len(queue)}")
            if current_state.finished():
                print(f"Checked {c} different states to get plan")
                return current_state.path

            commands = self.get_available_commands(current_state)
            for command in commands:
                new_state = State(self.predict_outcome(current_state.info, command), current_state, command, task=self.current_task)
                queue.insert(self.bin_insert_pos(queue, new_state, 0, len(queue) - 1), new_state)
        print("Ran out of states to expand")
        return current_state.path

    def bin_insert_pos(self, queue, state, start, stop):
        if start == stop:
            if queue[start] > state:
                return start
            return start + 1
        if start > stop:
            return start

        mid = (start + stop) // 2
        if queue[mid] < state:
            return self.bin_insert_pos(queue, state, mid + 1, stop)
        elif queue[mid] > state:
            return self.bin_insert_pos(queue, state, start, mid - 1)
        return mid

    def MCTS(self, info):
        def UCB(v, n, C = 2):
            if n == 0:
                return math.inf
            return v + C * math.sqrt(math.log(N, math.e)/n)

        def rollout(r_info):
            print("Rolling out current state")
            r = 0
            current_info = r_info
            while not self.finished(current_info):
                r += 1
                current_info = self.predict_outcome(current_info, random.choice(self.get_available_commands(current_info)))
                print(f"Ran {r} commands. On tick {current_info['tick']}")
            return self.true_score(info)

        def back_prop(state, v):
            state.v += v
            state.n += 1
            if state is not parent_state:
                back_prop(state.parent, v)

        parent_state = State(info)
        N = 0
        while N < 1000:
            current_state = parent_state
            print(N)
            while current_state.children:
                ucb_values = list(map(lambda s: UCB(s.v, s.n), current_state.children))
                current_state = current_state.children[ucb_values.index(max(ucb_values))]

            if current_state.n:
                commands = self.get_available_commands(current_state.info)
                for command in commands:
                    State(self.predict_outcome(current_state.info, command), current_state, command)
                current_state = current_state.children[0]

            back_prop(current_state, current_state.score)
            N += 1

        current_state = parent_state

        while not current_state.children:
            ucb_values = list(map(lambda s: UCB(s.v, s.n), current_state.children))
            current_state = current_state.children[ucb_values.index(max(ucb_values))]

        return current_state.path

    def true_score(self, info):
        score = 0
        for task_id in info["tasks"]:
            if info["tasks"][task_id]["completed"]():
                needed_resources = sum(info["tasks"][task_id]["needed_resources"])
                score += (self.TASK_SCORE_A * needed_resources) + (
                        self.TASK_SCORE_B * needed_resources) ** self.TASK_SCORE_C
        return score

    def finished(self, info):
        if info["tasks"][self.current_task]["project"] not in info["buildings"]:
            return info["tick"] >= self.TICK_HZ * self.SIM_LENGTH
        return True

class State:
    
    TASK_SCORE_A = 2
    TASK_SCORE_B = 1
    TASK_SCORE_C = 1.5

    SIM_LENGTH = 240
    TICK_HZ = 60
    
    def __init__(self, info, parent = None, last_command = None, task = None):
        self.info = info
        self.task = task


        """
        if info["tasks"][self.task]["project"] in info["sites"]:
            print(info["sites"][self.info["tasks"][self.task]["project"]]["needed_resources"], info["sites"][self.info["tasks"][self.task]["project"]]["deposited_resources"])
        """
        self.score = self.info_score()
        self.parent = parent
        self.path = []
        if self.parent is not None:
            self.parent.children.append(self)
            self.path = parent.path[:]
        if last_command is not None:
            self.path.append(last_command)
        self.children = []


        # For MCTS/UCB
        self.v = 0
        self.n = 0

    def __lt__(self, other):
        if isinstance(other, State):
            return self.score < other.score
        return None

    def __eq__(self, other):
        if isinstance(other, State):
            return self.score == other.score
        return None
    """
    def info_score(self):
        score = 0
        total_requests = [0 for _ in range(5)]
        for task_id in self.info["tasks"]:
            project = self.info["tasks"][task_id]["project"]
            if project in self.info["buildings"]:
                needed_resources = sum(self.info["tasks"][task_id]["needed_resources"])
                score += (self.TASK_SCORE_A * needed_resources) + (self.TASK_SCORE_B * needed_resources) ** self.TASK_SCORE_C

            else:
                task_requests = self.info["tasks"][task_id]["needed_resources"]
                if self.info["tasks"][task_id]["project"] is not None:
                    score += 1
                    if self.info["tasks"][task_id]["project"] == 97:
                        print("hello")
                    deposited_resources = self.info["sites"][self.info["tasks"][task_id]["project"]]["deposited_resources"]
                    for i, r in enumerate(task_requests):
                        score += 2
                        task_requests[i] = r - deposited_resources[i]
                for colour, request in enumerate(task_requests):
                    total_requests[colour] += request

        available_resources = [
            len(list(filter(lambda r: self.info["resources"][r]["colour"] == colour, self.info["resources"]))) for
            colour in range(5)]
        for colour, amount in enumerate(total_requests):
            if amount:
                if available_resources[colour] > 0:
                    score += min(available_resources[colour], amount)
                if available_resources[colour] < amount:
                    actor_closeness_scores = []
                    num_of_nodes = len(self.info["nodes"])
                    for actor in self.info["actors"]:
                        path = self.find_closest_mine_to_actor(colour, actor)
                        actor_closeness_scores.append((num_of_nodes - len(path)) / num_of_nodes)
                    score += max(actor_closeness_scores)
        return score
    """

    def info_score(self):
        score = 0
        total_requests = [0 for _ in range(5)]
        project = self.info["tasks"][self.task]["project"]
        num_of_nodes = len(self.info["nodes"])

        if project in self.info["buildings"]:
           needed_resources = sum(self.info["tasks"][self.task]["needed_resources"])
           score += needed_resources * 20

        else:
            task_requests = self.info["tasks"][self.task]["needed_resources"][:]
            if project is not None:
                score += 1
                deposited_resources = self.info["sites"][project]["deposited_resources"][:]
                score += sum(deposited_resources) * 10
                for i, d in enumerate(deposited_resources):
                    task_requests[i] = task_requests[i] - d
            for colour, request in enumerate(task_requests):
                total_requests[colour] += request

            available_resources = [
               len(list(filter(lambda r: self.info["resources"][r]["colour"] == colour, self.info["resources"]))) for
               colour in range(5)]
            for colour, amount in enumerate(total_requests):
                if amount:
                    if available_resources[colour] > 0:
                        existing_resources = list(
                            filter(lambda r: self.info["resources"][r]["colour"] == colour, self.info["resources"]))
                        resource_closeness_scores = list(map(lambda r: self.resource_path_to_task(r), existing_resources))
                        for resource_count in range(min(available_resources[colour], amount)):
                            max_score = max(resource_closeness_scores)
                            max_index = resource_closeness_scores.index(max_score)
                            score += max_score + 1
                            resource_closeness_scores.pop(max_index)
                    if available_resources[colour] < amount:
                        actor_closeness_scores = []
                        for actor in self.info["actors"]:
                            path = self.find_closest_mine_to_actor(colour, actor)
                            actor_closeness_scores.append((num_of_nodes - len(path[0])) / num_of_nodes)
                        score += max(actor_closeness_scores) * 0.5
                    if available_resources[colour] > amount:
                        score -= available_resources[colour] - amount
                else:
                    # Don't get resources you dont need
                    score -= available_resources[colour]
        return score

    def true_score(self):
        score = 0
        for task_id in self.info["tasks"]:
            if self.info["tasks"][task_id]["completed"]():
                needed_resources = sum(self.info["tasks"][task_id]["needed_resources"])
                score += (self.TASK_SCORE_A * needed_resources) + (
                            self.TASK_SCORE_B * needed_resources) ** self.TASK_SCORE_C
        return score

    def finished(self):
        if not self.info["tasks"][self.task]["project"] in self.info["buildings"]:
            return self.info["tick"] >= self.TICK_HZ * self.SIM_LENGTH
        return True

    def find_closest_mine_to_actor(self, colour, actor):
        # finds the closest mine of the given colour to the specific node
        def check_mines(node_id):
            for mine in self.info["nodes"][node_id]["mines"]:
                if self.info["mines"][mine]["colour"] == colour:
                    return True
            return False

        return self.find_path_to(self.info["actors"][actor]["node"], check_mines)

    def resource_path_to_task(self, resource):
        location = self.info["resources"][resource]["location"]
        actor_bonus = 0
        if location in self.info["actors"]:
            location = self.info["actors"][location]["node"]
            actor_bonus = 1

        path = self.find_path_to(location, lambda n : self.info["tasks"][self.task]["node"] == n)

        num_of_nodes = len(self.info["nodes"])

        return ((num_of_nodes - len(path[0])) / num_of_nodes) + actor_bonus

    def find_path_to(self, start, goal):
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
        current_path = ([start], 0)
        frontier = {start: current_path}
        explored = {}
        while True:
            if frontier:
                current_path = frontier.pop(smallest_key(frontier))
                if goal(current_path[0][-1]):
                    return current_path
                explored[current_path[0][-1]] = current_path
                for edge in self.info["nodes"][current_path[0][-1]]["edges"]:
                    # edge is id of an edge connected to current_path[0][-1]
                    length = self.info["edges"][edge]["length"]
                    next_node = self.info["edges"][edge]["get_other_node"](current_path[0][-1])
                    path = current_path[0][:]
                    path.append(next_node)
                    new_path = (path, current_path[1] + length)
                    if explored.__contains__(next_node) and explored[next_node][1] > new_path[1]:
                        explored[next_node] = new_path
                    elif not frontier.__contains__(next_node) or frontier[next_node][1] > new_path[1]:
                        frontier[next_node] = new_path
            else:
                return None