import random as r
import math as m

from api.command import Command
from entities.node import Node
from entities.edge import Edge
from entities.actor import Actor
from entities.resource import Resource
from entities.site import Site
from entities.building import Building
from entities.mine import Mine
from entities.task import Task


class World:

    def __init__(self, modifiers=None, world_gen_modifiers=None, rules=None):
        if modifiers is None or world_gen_modifiers is None or rules is None:
            pass
        else:
            self.modifiers = modifiers
            self.world_gen_modifiers = world_gen_modifiers
            self.rules = rules
            """
            0 - Actor Speed
            1 - Actor Mining Speed
            2 - Actor Building Speed
            3 - Actor Inventory Size
            """
            self.building_modifiers = {0: 0, 1: 0, 2: 0, 3: 0}

            self.nodes = []
            self.tick = 0
            self.last_id = -1
            self.command_queue = []
            self.command_results = []
            self.all_commands = []
            self.total_score = 0

            self.create_nodes_prm()
            self.tasks = self.generate_tasks()

    def create_nodes_prm(self):
        self.nodes = [Node(self, self.world_gen_modifiers["WIDTH"]/2, self.world_gen_modifiers["HEIGHT"]/2)]
        attempts = 0
        curr_x = self.nodes[0].x
        curr_y = self.nodes[0].y
        for i in range(self.world_gen_modifiers["MAX_NODES"] - 1):
            ok = False
            while not ok:
                ok = True
                rand_angle = r.randint(0, 360)
                rand_deviation = r.randint(-1 * self.world_gen_modifiers["RANDOM_DEVIATION"],
                                           self.world_gen_modifiers["RANDOM_DEVIATION"])
                new_x = m.floor(curr_x + rand_deviation + self.world_gen_modifiers["CAST_DISTANCE"] * m.cos(rand_angle))
                new_y = m.floor(curr_y + rand_deviation + self.world_gen_modifiers["CAST_DISTANCE"] * m.sin(rand_angle))
                for node in self.nodes:
                    if m.dist((new_x, new_y), (node.x, node.y)) <= self.world_gen_modifiers["MIN_DISTANCE"] or\
                            new_x < 0 or new_x > self.world_gen_modifiers["WIDTH"] or new_y < 0 \
                            or new_y > self.world_gen_modifiers["HEIGHT"]:
                        ok = False
                        break
                no_new_edges = True
                if ok:
                    new_node = Node(self, new_x, new_y)
                    new_edges = []
                    for node in self.nodes:
                        if m.dist((new_x, new_y), (node.x, node.y)) <= self.world_gen_modifiers["CONNECT_DISTANCE"]:
                            new_edges.append(Edge(self, new_node, node))
                            no_new_edges = False
                    if not no_new_edges:
                        self.nodes.append(new_node)
                        curr_x = new_x
                        curr_y = new_y
                attempts += 1
                if attempts >= self.world_gen_modifiers["MAX_ATTEMPTS"]:
                    break

    def get_world_info(self):
        edges = self.get_edges_info()
        resources = self.get_resources_info()
        mines = self.get_mines_info()
        sites = self.get_sites_info()
        buildings = self.get_buildings_info()
        tasks = self.get_tasks_info()

        actors = {}
        for actor in self.get_all_actors():
            actors.__setitem__(actor.id, actor.fields)

        nodes = {}
        if self.rules["NODE_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    if nodes.__contains__(actor.node.id):
                        nodes.get(actor.node.id)["observers"].append(actor.id)
                    else:
                        nodes.__setitem__(actor.node.id, actor.node.fields)
                        nodes.get(actor.node.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node_id in node_stack:
                        if nodes.__contains__(node_id):
                            nodes.get(node_id)["observers"].append(actor.id)
                        else:
                            nodes.__setitem__(node_id, node_stack[node_id].fields)
                            nodes.get(node_id).__setitem__("observers", [actor.id])
        else:
            for node in self.nodes:
                nodes.__setitem__(node.id, node.fields)
                if self.rules["EDGE_PO"]:
                    nodes[node.id].__setitem__("edges", [])
                    for edge_id in edges:
                        if edges[edge_id]["node_a"] == node.id or edges[edge_id]["node_b"] == node.id:
                            nodes.get(node.id)["edges"].append(edge_id)
                if self.rules["RESOURCE_PO"]:
                    nodes[node.id].__setitem__("resources", [])
                    for resource_id in resources:
                        if resources[resource_id]["location"] == node.id:
                            nodes.get(node.id)["resources"].append(resource_id)
                if self.rules["MINE_PO"]:
                    nodes[node.id].__setitem__("mines", [])
                    for mine_id in mines:
                        if mines[mine_id]["node"] == node.id:
                            nodes.get(node.id)["mines"].append(mine_id)
                if self.rules["SITE_PO"]:
                    nodes[node.id].__setitem__("sites", [])
                    for site_id in sites:
                        if sites[site_id]["node"] == node.id:
                            nodes.get(node.id)["sites"].append(site_id)
                if self.rules["BUILDING_PO"]:
                    nodes[node.id].__setitem__("buildings", [])
                    for building_id in buildings:
                        if buildings[building_id]["node"] == node.id:
                            nodes.get(node.id)["buildings"].append(building_id)
                if self.rules["TASK_PO"]:
                    nodes[node.id].__setitem__("tasks", [])
                    for task_id in tasks:
                        if tasks[task_id]["node"] == node.id:
                            nodes.get(node.id)["tasks"].append(task_id)

        commands = {}
        for command in self.all_commands:
            commands.__setitem__(command.id, command.fields)

        return {"tick": self.tick, "actors": actors, "nodes": nodes, "edges": edges, "resources": resources,
                "mines": mines, "sites": sites, "buildings": buildings, "tasks": tasks, "commands": commands}

    def get_tasks_info(self):
        tasks = {}
        if self.rules["TASK_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for task in actor.node.tasks:
                        if tasks.__contains__(task.id):
                            tasks.get(task.id)["observers"].append(actor.id)
                        else:
                            tasks.__setitem__(task.id, task.fields)
                            tasks.get(task.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for task in node_stack[node].tasks:
                            if tasks.__contains__(task.id):
                                tasks.get(task.id)["observers"].append(actor.id)
                            else:
                                tasks.__setitem__(task.id, task.fields)
                                tasks.get(task.id).__setitem__("observers", [actor.id])
        else:
            for task in self.tasks:
                tasks.__setitem__(task.id, task.fields)
        return tasks

    def get_buildings_info(self):
        buildings = {}
        if self.rules["BUILDING_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for building in actor.node.buildings:
                        if buildings.__contains__(building.id):
                            buildings.get(building.id)["observers"].append(actor.id)
                        else:
                            buildings.__setitem__(building.id, building.fields)
                            buildings.get(building.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for building in node_stack[node].buildings:
                            if buildings.__contains__(building.id):
                                buildings.get(building.id)["observers"].append(actor.id)
                            else:
                                buildings.__setitem__(building.id, building.fields)
                                buildings.get(building.id).__setitem__("observers", [actor.id])
        else:
            for building in self.get_all_buildings():
                buildings.__setitem__(building.id, building.fields)
        return buildings

    def get_sites_info(self):
        sites = {}
        if self.rules["SITE_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for site in actor.node.sites:
                        if sites.__contains__(site.id):
                            sites.get(site.id)["observers"].append(actor.id)
                        else:
                            sites.__setitem__(site.id, site.fields)
                            sites.get(site.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for site in node_stack[node].sites:
                            if sites.__contains__(site.id):
                                sites.get(site.id)["observers"].append(actor.id)
                            else:
                                sites.__setitem__(site.id, site.fields)
                                sites.get(site.id).__setitem__("observers", [actor.id])
        else:
            for site in self.get_all_sites():
                sites.__setitem__(site.id, site.fields)
        return sites

    def get_mines_info(self):
        mines = {}
        if self.rules["MINE_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for mine in actor.node.mines:
                        if mines.__contains__(mine.id):
                            mines.get(mine.id)["observers"].append(actor.id)
                        else:
                            mines.__setitem__(mine.id, mine.fields)
                            mines.get(mine.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for mine in node_stack[node].mines:
                            if mines.__contains__(mine.id):
                                mines.get(mine.id)["observers"].append(actor.id)
                            else:
                                mines.__setitem__(mine.id, mine.fields)
                                mines.get(mine.id).__setitem__("observers", [actor.id])
        else:
            for mine in self.get_all_mines():
                mines.__setitem__(mine.id, mine.fields)
        return mines

    def get_resources_info(self):
        resources = {}
        if self.rules["RESOURCE_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for resource in actor.node.resources:
                        if resources.__contains__(resource.id):
                            resources.get(resource.id)["observers"].append(actor.id)
                        else:
                            resources.__setitem__(resource.id, resource.fields)
                            resources.get(resource.id).__setitem__("observers", [actor.id])
                    for node_actor in actor.node.actors:
                        for resource in node_actor.resources:
                            if resources.__contains__(resource.id):
                                resources.get(resource.id)["observers"].append(actor.id)
                            else:
                                resources.__setitem__(resource.id, resource.fields)
                                resources.get(resource.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for resource in node_stack[node].resources:
                            if resources.__contains__(resource.id):
                                resources.get(resource.id)["observers"].append(actor.id)
                            else:
                                resources.__setitem__(resource.id, resource.fields)
                                resources.get(resource.id).__setitem__("observers", [actor.id])
                        for node_actor in node_stack[node].actors:
                            for resource in node_actor.resources:
                                if resources.__contains__(resource.id):
                                    resources.get(resource.id)["observers"].append(actor.id)
                                else:
                                    resources.__setitem__(resource.id, resource.fields)
                                    resources.get(resource.id).__setitem__("observers", [actor.id])
        else:
            for resource in self.get_all_resources():
                resources.__setitem__(resource.id, resource.fields)
        return resources

    def get_edges_info(self):
        edges = {}
        if self.rules["EDGE_PO"]:
            for actor in self.get_all_actors():
                if actor.state != actor.LOOKING and actor.state != actor.MOVING and actor.state != actor.RECOVERING:
                    for edge in actor.node.edges:
                        if edges.__contains__(edge.id):
                            if not edges.get(edge.id)["observers"].__contains__(actor.id):
                                edges.get(edge.id)["observers"].append(actor.id)
                        else:
                            edges.__setitem__(edge.id, edge.fields)
                            edges.get(edge.id).__setitem__("observers", [actor.id])
                elif actor.state == actor.LOOKING:
                    node_stack = {actor.node.id: actor.node}
                    got_new_nodes = True
                    layer = 0
                    new_nodes = []
                    while got_new_nodes and layer < actor.progress / self.modifiers["LOOK_EFFORT"]:
                        got_new_nodes = False
                        layer += 1
                        for node_id in node_stack:
                            for edge in node_stack[node_id].edges:
                                new_node = edge.get_other_node(node_stack[node_id])
                                if not node_stack.__contains__(new_node.id):
                                    new_nodes.append(new_node)
                                    got_new_nodes = True
                        if got_new_nodes:
                            for new_node in new_nodes:
                                node_stack.__setitem__(new_node.id, new_node)
                    for node in node_stack:
                        for edge in node_stack[node].edges:
                            if edges.__contains__(edge.id):
                                if not edges.get(edge.id)["observers"].__contains__(actor.id):
                                    edges.get(edge.id)["observers"].append(actor.id)
                            else:
                                edges.__setitem__(edge.id, edge.fields)
                                edges.get(edge.id).__setitem__("observers", [actor.id])
        else:
            for edge in self.get_all_edges():
                edges.__setitem__(edge.id, edge.fields)
        return edges

    def run_tick(self):
        self.update_all_actors()
        self.update_all_resources()
        self.run_agent_commands()
        if self.tasks_complete():
            self.tasks.extend(self.generate_tasks())
        else:
            if r.random() < self.modifiers["NEW_TASK_CHANCE"]:
                self.tasks.append(Task(self))
        self.tick += 1

    def run_agent_commands(self):
        if self.command_queue:
            self.all_commands.extend(self.command_queue)
            self.command_results = []
            for command in self.command_queue:
                self.command_results.append((command.id, command.perform()))
            self.command_queue = []

    def update_all_actors(self):
        for actor in self.get_all_actors():
            actor.update()
            
    def update_all_resources(self):
        for resource in self.get_all_resources():
            resource.update()

    def tasks_complete(self):
        for task in self.tasks:
            if not task.completed():
                return False
        return True

    def generate_tasks(self):
        tasks = []
        for index in range(3):
            tasks.append(Task(self))
        return tasks

    def add_actor(self, node):
        return Actor(self, node)

    def add_resource(self, location, colour):
        return Resource(self, location, colour)

    def add_mine(self, node, colour):
        return Mine(self, node, colour)

    def add_site(self, node, colour):
        return Site(self, node, colour)

    def add_building(self, node, colour):
        return Building(self, node, colour)

    def get_colour_string(self, colour):
        if colour == 0:
            return "red"
        elif colour == 1:
            return "blue"
        elif colour == 2:
            return "orange"
        elif colour == 3:
            return "black"
        elif colour == 4:
            return "green"
        elif colour == 5:
            return "purple"

    def get_all_mines(self):
        mines = []
        for node in self.nodes:
            mines.extend(node.mines)
        return mines
    
    def get_all_actors(self):
        actors = []
        for node in self.nodes:
            actors.extend(node.actors)
        return actors

    def get_all_actor_ids(self):
        actor_ids = []
        for node in self.nodes:
            for actor in node.actors:
                actor_ids.append(actor.id)
        return actor_ids
    
    def get_all_resources(self):
        resources = []
        for node in self.nodes:
            resources.extend(node.resources)
        for actor in self.get_all_actors():
            resources.extend(actor.resources)
        return resources
    
    def get_all_sites(self):
        sites = []
        for node in self.nodes:
            sites.extend(node.sites)
        return sites
    
    def get_all_buildings(self):
        buildings = []
        for node in self.nodes:
            buildings.extend(node.buildings)
        return buildings

    def get_all_edges(self):
        edges = []
        for node in self.nodes:
            for edge in node.edges:
                if not edges.__contains__(edge):
                    edges.append(edge)
        return edges

    def get_new_id(self):
        self.last_id += 1
        return self.last_id

    def get_by_id(self, entity_id, entity_type=None, target_node=None):
        if target_node is None:
            target_node = self.nodes
        else:
            target_node = [target_node]
        if entity_type == "Task" or entity_type is None:
            for task in self.tasks:
                if task.id == entity_id:
                    return task
        for node in target_node:
            if node.id == entity_id and (entity_type == "Node" or entity_type is None):
                return node
            for actor in node.actors:
                if actor.id == entity_id and (entity_type == "Actor" or entity_type is None):
                    return actor
                for resource in actor.resources:
                    if resource.id == entity_id and (entity_type == "Resource" or entity_type is None):
                        return resource
            for resource in node.resources:
                if resource.id == entity_id and (entity_type == "Resource" or entity_type is None):
                    return resource
            for mine in node.mines:
                if mine.id == entity_id and (entity_type == "Mine" or entity_type is None):
                    return mine
            for site in node.sites:
                if site.id == entity_id and (entity_type == "Site" or entity_type is None):
                    return site
            for building in node.buildings:
                if building.id == entity_id and (entity_type == "Building" or entity_type is None):
                    return building
            for edge in node.edges:
                if edge.id == entity_id and (entity_type == "Edge" or entity_type is None):
                    return edge
        return None

    def get_field(self, entity_id, field, entity_type=None, target_node=None):
        entity = self.get_by_id(entity_id, entity_type=entity_type, target_node=target_node)
        return None if entity is None else entity.fields.get(field)
