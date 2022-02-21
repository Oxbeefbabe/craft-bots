import numpy.random as nr
import random as r
import math as m

from entities.building import Building


class Site:

    def __init__(self, world, node, building_type, target_task=None):
        """
        A site in the craftbots simulation. It allows actors to deposit resources and construct at it to create
        buildings. These buildings provide bonuses to the actors

        :param world: the world in which the site exists
        :param node: the node the site is located at
        :param building_type: the colour of the site (this will produce a building of that type)
        :param target_task: the task entity that is chosen if the site is purple. If it is None then one at the sites node is chosen at random (if a free task is available)
        """
        self.world = world
        self.node = node
        self.building_type = building_type
        self.deposited_resources = [0, 0, 0, 0, 0]
        self.progress = 0
        self.id = self.world.get_new_id()
        self.needed_resources = []
        self.task = None
        if self.building_type == Building.BUILDING_TASK:
            if target_task is None:
                for task in self.world.tasks:
                    if task.node == self.node and task.project is None:
                        task.set_project(self)
                        self.task = task
                        self.needed_resources = task.needed_resources
                        break
            else:
                if target_task.project is None and target_task.node == self.node:
                    target_task.set_project(self)
                    self.task = target_task
                    self.needed_resources = target_task.needed_resources
        else:
            required_resources_key = "REQUIRED_RESOURCES_" + Building.get_building_type_name(building_type)
            if self.world.modifiers[required_resources_key]:
                self.needed_resources = self.world.modifiers[required_resources_key]

        # If needed resources cannot be found, then do not inform anything that this Site exists
        if self.needed_resources:
            self.node.append_site(self)
            self.fields = {"node": self.node.id, "building_type": self.building_type, "deposited_resources": self.deposited_resources,
                           "needed_resources": self.needed_resources, "progress": self.progress, "id": self.id, "task": self.task.id}

    def __repr__(self):
        return "Site(" + str(self.id) + ", " + str(self.node) + ")"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, Site):
            return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def deposit_resources(self, resource):
        """
        Deposit a resource into the site. This consumes the resource.
        :param resource: The resource to be added
        :return: True if the resource was deposited and false if it wasn't
        """
        if resource.location.node == self.node:
            if self.deposited_resources[resource.colour] < self.needed_resources[resource.colour]:
                resource.set_used(True)
                self.deposited_resources[resource.colour] += 1
                self.fields.__setitem__("deposited_resources", self.deposited_resources)
                resource.location.remove_resource(resource)
                self.world.resources.remove(resource)
                resource.set_used(True)
                return True
        return False

    def construct(self, deviation):
        """
        Called to provide progress on the construction of a building. This can only be done up to a certain point based
        on how many resources have been deposited so far.
        """

        if self.world.rules["CONSTRUCTION_NON_DETERMINISTIC"] and r.random() < \
                self.world.modifiers["CONSTRUCTION_FAIL_CHANCE"]:
            print("Constructing failed")
            self.fail_construction()
            return

        build_speed = self.world.modifiers["BUILD_SPEED"] if not self.world.rules["CONSTRUCTING_TU"] else \
            max(self.world.modifiers["CONSTRUCTING_MIN_SD"],
                min(self.world.modifiers["CONSTRUCTING_MAX_SD"],
                    nr.normal(deviation, self.world.modifiers["CONSTRUCTING_PT_SD"])))

        building_progress = build_speed * ((1 + self.world.modifiers["ORANGE_BUILDING_MODIFIER_STRENGTH"]) **
                                           self.world.building_modifiers[Building.BUILDING_CONSTRUCTION])

        max_progress = self.max_progress()
        self.set_progress(min(self.progress + building_progress, max_progress))

        if self.progress >= self.world.modifiers["BUILD_EFFORT"] * sum(self.needed_resources):
            if self.world.rules["CONSTRUCTION_COMPLETION_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["CONSTRUCTION_COMPLETION_FAIL_CHANCE"]:
                print("Construction completion failed")
                self.fail_construction()
                return
            new_building = self.world.add_building(self.node, self.building_type)
            self.node.remove_site(self)
            self.ignore_me()
            if self.building_type == Building.BUILDING_TASK:
                self.task.set_project(new_building)
                self.task.complete_task()
        elif self.progress == max_progress:
            self.ignore_me()

    def fail_construction(self):
        self.ignore_me()
        penalty = r.uniform(self.world.modifiers["CONSTRUCTION_FAIL_MIN_PENALTY"],
                            self.world.modifiers["CONSTRUCTION_FAIL_MAX_PENALTY"])
        for _ in range(min(self.world.modifiers["MAX_RESOURCE_PENALTY"], m.ceil(sum(self.needed_resources) * penalty))):
            self.deposited_resources[self.deposited_resources.index(max(self.deposited_resources))] -= 1
        for index in range(self.needed_resources.__len__()):
            self.needed_resources[index] = max(0, self.needed_resources[index])
        self.set_progress(min(self.progress - (sum(self.needed_resources) * self.world.modifiers["BUILD_EFFORT"]
                                               * penalty), self.max_progress()))

    def max_progress(self):
        """
        Gets the currently possible maximum progress based on how many resources have been deposited

        :return: The maximum progress
        """
        return self.world.modifiers["BUILD_EFFORT"] * sum(self.needed_resources) * sum(self.deposited_resources) / sum(self.needed_resources)

    def ignore_me(self):
        """
        Gets all the actors that have targeted the building and sets them to become idle
        """
        for actor in self.node.actors:
            if actor.target == self:
                actor.go_idle()

    def set_progress(self, progress):
        """
        Sets the progress of the site and keeps track of this in the sites fields.
        :param progress:
        """
        self.progress = progress
        self.fields.__setitem__("progress", progress)
