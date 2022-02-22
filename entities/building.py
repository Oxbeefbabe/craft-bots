import numpy.random as nr
import random as r
import math as m


class Building:

    BUILDING_TASK         = 0
    BUILDING_SPEED        = 1
    BUILDING_MINE         = 2
    BUILDING_CONSTRUCTION = 3
    BUILDING_INVENTORY    = 4
    BUILDING_ACTOR_SPAWN  = 5

    @staticmethod
    def get_building_type_name(building_type):
        for key in Building.__dict__:
            if "BUILDING" in key and Building.__dict__[key]==building_type:
                return key

    def __init__(self, world, node, building_type=0):
        """
        A completed building in the craftbots simulation. It takes a certain amount of work and resources gathered into
        a site by actors to create a building. Different buildings require different amount of resources. Each type of
        building will provide a different positive effect for the actors in the simulation.

        :param world: the world the in which the building exists
        :param node: the node the building is located at
        :param building_type: the colour of the building (this determines the effect it provides)
        """
        self.world = world
        self.node = node
        self.building_type = building_type
        self.id = self.world.get_new_id()

        self.node.append_building(self)

        # If the building is green then create other fields needed to keep track of new actor construction
        if building_type == Building.BUILDING_ACTOR_SPAWN:
            self.deposited_resources = [0, 0, 0, 0, 0]
            self.needed_resources = self.world.modifiers["NEW_ACTOR_RESOURCES"]
            self.progress = 0
            self.fields = {"node": self.node.id, "building_type": self.building_type, "id": self.id,
                           "deposited_resources": self.deposited_resources,
                           "needed_resources": self.needed_resources, "progress": self.progress}
        else:
            self.fields = {"node": self.node.id, "building_type": self.building_type, "id": self.id}

        # Keep track of the bonuses the building provides in the simulation
        max_var_name = 'MAX_' + Building.get_building_type_name(self.building_type)
        if max_var_name in self.world.modifiers:
            if self.world.modifiers[max_var_name] >= 0:
                self.world.building_modifiers[self.building_type] = min(self.world.modifiers[max_var_name], self.world.building_modifiers[self.building_type] + 1)
            else:
                self.world.building_modifiers[self.building_type] += 1

    def __repr__(self):
        return "Building(" + str(self.id) + ", " + Building.get_building_type_name(self.building_type) + ", " + str(self.node) + ")"

    def __str__(self):
        return self.__repr__()

    def deposit_resources(self, resource):
        """
        Deposit a resource into the building if it is green. This consumes the resource.

        :param resource: The resource to be added
        :return: True if the resource was deposited and false if it wasn't
        """
        if self.building_type == Building.BUILDING_ACTOR_SPAWN:
            if resource.location == self.node or resource.location.node == self.node:
                if self.deposited_resources[resource.colour] < self.needed_resources[resource.colour]:
                    resource.set_used(True)
                    self.deposited_resources[resource.colour] += 1
                    self.fields.__setitem__("deposited_resources", self.deposited_resources)
                    resource.location.remove_resource(resource)
                    resource.set_used(True)
                    return True
        return False

    def construct(self, deviation):
        """
        Called to provide progress on the construction of a new bot. This can only be done up to a certain point based
        on how many resources have been deposited so far.
        """

        if self.world.rules["CONSTRUCTION_NON_DETERMINISTIC"] and r.random() < self.world.modifiers["CONSTRUCTION_FAIL_CHANCE"]:
            print("Constructing failed")
            self.world.failures += 1
            self.fail_construction()
            return

        if self.building_type == Building.BUILDING_ACTOR_SPAWN:

            build_speed = self.world.modifiers["BUILD_SPEED"] if not self.world.rules["CONSTRUCTING_TU"] else \
                max(self.world.modifiers["CONSTRUCTING_MIN_SD"],
                    min(self.world.modifiers["CONSTRUCTING_MAX_SD"],
                        nr.normal(deviation, self.world.modifiers["CONSTRUCTING_PT_SD"])))

            building_progress = build_speed * ((1 + self.world.modifiers["ORANGE_BUILDING_MODIFIER_STRENGTH"]) **
                                               self.world.building_modifiers[Building.BUILDING_CONSTRUCTION])
            
            max_progress = self.max_progress()
            self.set_progress(min(self.progress + building_progress, max_progress))

            if self.progress == max_progress:
                for actor in self.node.actors:
                    if actor.target == self:
                        actor.go_idle()
            if self.progress >= self.world.modifiers["BUILD_EFFORT"] * sum(self.needed_resources):
                if self.world.rules["CONSTRUCTION_COMPLETION_NON_DETERMINISTIC"] and r.random() < \
                        self.world.modifiers["CONSTRUCTION_COMPLETION_FAIL_CHANCE"]:
                    print("Construction completion failed")
                    self.world.failures += 1
                    self.fail_construction()
                    return
                self.world.add_actor(self.node)
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
        Gets the currently possible maximum progress based on how many resources have been deposited, if the building is
        green

        :return: The maximum progress, or False if the building is not green
        """
        if self.building_type == Building.BUILDING_ACTOR_SPAWN:
            return sum(self.deposited_resources) / sum(self.needed_resources) * self.world.modifiers["BUILD_EFFORT"]
        return False

    def ignore_me(self):
        """
        Gets all the actors that have targeted the building and sets them to become idle
        """
        if self.building_type == Building.BUILDING_ACTOR_SPAWN:
            for actor in self.node.actors:
                if actor.target == self:
                    actor.go_idle()

    def set_progress(self, progress):
        """
        Sets the progress of the new actor in the building and keeps track of this in the Buildings fields.

        :param progress:
        """
        if self.building_type == Building.BUILDING_ACTOR_SPAWN:
            self.progress = progress
            self.fields.__setitem__("progress", progress)
