import numpy.random as nr
import random as r

from entities.building import Building


class Mine:
    def __init__(self, world, node, colour=0):
        self.world = world
        self.node = node
        self.colour = colour
        self.progress = 0
        self.id = self.world.get_new_id()

        self.node.append_mine(self)

        self.fields = {"node": self.node.id, "colour": self.colour, "id": self.id, "progress": self.progress}

    def __repr__(self):
        return "Mine(" + str(self.id) + ", " + self.world.get_colour_string(self.colour) + ", " + str(
            self.node) + ")"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Mine) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def provide(self):
        """
        Creates a resource at the node the mine is at, and resets the progress
        """
        self.set_progress(0)
        self.world.add_resource(self.node, self.colour)

    def dig(self, deviation):
        """
        Called when an actor digs at this mine, checking if the requirements (if any) are met before progress is made.

        :return: True if digging can begin and false otherwise.
        """

        if self.world.rules["DIGGING_NON_DETERMINISTIC"] and r.random() < \
                self.world.modifiers["DIGGING_FAIL_CHANCE"]:
            print("Digging failed")
            self.world.failures += 1
            self.set_progress(0)
            self.ignore_me()
            return

        dig_speed = self.world.modifiers["DIG_SPEED"] if not self.world.rules["DIGGING_TU"] else \
            max(self.world.modifiers["DIGGING_MIN_SD"],
                min(self.world.modifiers["DIGGING_MAX_SD"],
                    nr.normal(deviation, self.world.modifiers["DIGGING_PT_SD"])))

        digging_progress = dig_speed * ((1 + self.world.modifiers["BLUE_BUILDING_MODIFIER_STRENGTH"]) **
                                        self.world.building_modifiers[Building.BUILDING_MINE])

        # If mine is red, ensure that it is within red mining intervals
        if self.colour == 0:
            index = 0
            bad_time = True
            while index < self.world.modifiers["RED_COLLECTION_INTERVALS"].__len__():
                if self.world.modifiers["RED_COLLECTION_INTERVALS"][index] <= self.world.tick % \
                        self.world.modifiers["CYCLE_LENGTH"] <= \
                        self.world.modifiers["RED_COLLECTION_INTERVALS"][index + 1]:
                    self.set_progress(self.progress + digging_progress)
                    bad_time = False
                    break
                index += 2
            if bad_time:
                return False

        # If mine is orange, make sure 2+ actors are currently mining
        elif self.colour == 2:
            num_of_miners = 0
            for actor in self.node.actors:
                if actor.target == self:
                    num_of_miners += 1
            if num_of_miners >= self.world.modifiers["ORANGE_ACTORS_TO_MINE"]:
                self.set_progress(self.progress + digging_progress)
            else:
                return False

        # If mine is blue, slow down mining speed
        elif self.colour == 1:
            self.set_progress(self.progress + (digging_progress / self.world.modifiers["BLUE_EXTRA_EFFORT"]))
        else:
            self.set_progress(self.progress + digging_progress)

        # Check if mining yields resources, and stop mining
        if self.progress >= self.world.modifiers["MINE_EFFORT"]:
            if self.world.rules["DIGGING_COMPLETION_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["DIGGING_COMPLETION_FAIL_CHANCE"]:
                print("Digging completion failed")
                self.set_progress(0)
                self.ignore_me()
                return
            self.provide()
            self.ignore_me()

    def ignore_me(self):
        """
        Gets all the actors that have targeted the mine and sets them to become idle
        """
        for actor in self.node.actors:
            if actor.target == self:
                actor.go_idle()

    def set_progress(self, progress):
        """
        Sets the progress of the mine and keeps track of this in the mines fields

        :param progress:
        """
        self.progress = progress
        self.fields.__setitem__("progress", progress)
