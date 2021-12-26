import random
from api import agent_api
from entities.actor import Actor

"""
Bogo is an agent for the craft bots simulation that only makes (semi)-random moves. 
They are by no means efficient but in most circumstances, Bogo will complete the tasks of 
the simulation.

Bogo's name is a reference to bogosort:
https://en.wikipedia.org/wiki/Bogosort
"""


class Bogo:
    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info
        self.orange_ticks = {}

    def get_next_commands(self):
        self.api: agent_api.AgentAPI

        for actor_id in self.api.actors:
            try:

                actor = self.api.get_by_id(actor_id, entity_type="Actor")

                if actor["state"] == Actor.IDLE:

                    for task_id in self.api.get_field(actor["node"], "tasks", entity_type="Node"):
                        task = self.api.get_by_id(task_id, entity_type="Task")
                        if task["project"] is None:
                            self.api.start_site(actor_id, 5)

                    sites = self.api.get_field(actor["node"], "sites", entity_type="Node")
                    if sites:
                        for site_id in sites:
                            site = self.api.get_by_id(site_id, entity_type="Site")
                            for resource_id in actor["resources"]:
                                resource = self.api.get_by_id(resource_id, entity_type="Resource")
                                if site["deposited_resources"][resource["colour"]] < site["needed_resources"][
                                    resource["colour"]]:
                                    self.api.deposit_resources(actor_id, site["id"], resource_id)
                                    self.api.construct_at(actor_id, site["id"])
                    else:
                        make_building_chance = random.random()
                        if 0.04 < make_building_chance <= 0.05:
                            self.api.start_site(actor_id, 4)
                        elif 0.03 < make_building_chance <= 0.04:
                            self.api.start_site(actor_id, 3)
                        elif 0.02 < make_building_chance <= 0.03:
                            self.api.start_site(actor_id, 2)
                        elif 0.01 < make_building_chance <= 0.02:
                            self.api.start_site(actor_id, 1)
                        elif make_building_chance <= 0.01:
                            self.api.start_site(actor_id, 0)


                    resources = self.api.get_field(actor["node"], "resources", entity_type="Node")
                    if resources:
                        if actor["resources"]:
                            if self.api.get_field(actor["resources"][0], "colour", entity_type="Resource") == 3 or \
                                    self.api.get_field(resources[0], "colour", entity_type="Resource") == 3:
                                self.api.drop_all_resources(actor_id)
                        self.api.pick_up_resource(actor_id, resources[0])
                        self.api.move_rand(actor_id)

                    mines = self.api.get_field(actor["node"], "mines", entity_type="Node")
                    if mines:
                        target_mine = mines[random.randint(0, mines.__len__() - 1)]
                        self.api.dig_at(actor_id, target_mine)
                        self.orange_ticks[actor_id] = self.world_info["tick"] + 1200

                    self.api.move_rand(actor_id)

                elif actor["state"] == Actor.DIGGING:
                    if self.api.get_field(actor["target"], "colour", entity_type="Mine") == 2:
                        if self.world_info["tick"] > self.orange_ticks[actor_id]:
                            self.api.cancel_action(actor_id)
                            self.api.move_rand(actor_id)
            except:
                print("Something went wrong")

        self.thinking = False
