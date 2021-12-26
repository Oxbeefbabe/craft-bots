import random as r
import numpy.random as nr

from entities.building import Building


class Actor:
    
    IDLE = 0
    MOVING = 1
    DIGGING = 2
    CONSTRUCTING = 3
    RECOVERING = 4
    LOOKING = 5
    SENDING = 6
    RECEIVING = 7

    def __init__(self, world, node):
        """
        The actor of the world. With this object, your agent will be able to manipulate the world.
        The actor lets the node it should be in know that it exists, so it can be tracked. The actor also has
        several states which indicate what it is currently doing. It initially starts idle (0)
        :param world: The world in which the actor should exist
        :param node: The node in which to spawn the actor. If none is given then the actor spawns at the first node
        created in the world.
        """
        self.world = world
        self.node = node
        self.state = Actor.IDLE
        self.progress = -1
        self.id = self.world.get_new_id()
        self.target = None
        self.resources = []
        self.deviation = 0

        self.node.append_actor(self)

        self.fields = {"node": self.node.id, "state": self.state, "progress": self.progress, "id": self.id,
                       "target": None, "resources": []}

    def __repr__(self):
        return "Actor(" + str(self.id) + ", " + str(self.node) + ")"

    def __str__(self):
        return self.__repr__()

    def travel_to(self, target_node):
        """
        Tells the actor to begin moving to the targeted node. Whenever the actor is updated via update(), it will make
        a certain amount of progress based on the ACTOR_SPEED modifier. Actor must be idle before beginning to travel.
        :param target_node: Node object to send the actor to. Must share an edge with node the actor is currently in
        :return: True if successful and False otherwise
        """
        if self.state != Actor.IDLE:
            # print("Error: Must be idle to begin travelling to another node!")
            return False
        node_index = self.node.shares_edge_with(target_node)
        if node_index != -1:
            self.deviation = nr.normal(self.world.modifiers["ACTOR_MOVE_SPEED"],
                                       self.world.modifiers["TRAVEL_OVERALL_SD"]) \
                if self.world.rules["TRAVEL_TU"] else 0
            self.set_target((self.node.edges[node_index], target_node))
            self.set_state(Actor.MOVING)
            self.set_progress(0)
            return True
        return False

    def travel_rand(self):
        """
        Tells the actor to begin travelling towards a random node that shares an edge with the node it is currently in
        :return: True if successful and False otherwise
        """
        target_edge = self.node.edges[r.randint(0, self.node.edges.__len__() - 1)]
        if target_edge.node_a == self.node:
            return self.travel_to(target_edge.node_b)
        else:
            return self.travel_to(target_edge.node_a)

    def update(self):
        """
        Called to simulate the actor performing actions for 1 tick. Depends on what the actor is currently doing via the
        state.
        """
        if self.state == Actor.MOVING or self.state == Actor.RECOVERING:
            speed_mod = (self.world.building_modifiers[Building.BUILDING_SPEED] * 0.05) + 1
            move_speed = self.world.modifiers["ACTOR_MOVE_SPEED"] if not self.world.rules["TRAVEL_TU"] else \
                max(self.world.modifiers["TRAVEL_MIN_SD"],
                    min(self.world.modifiers["TRAVEL_MAX_SD"],
                        nr.normal(self.deviation, self.world.modifiers["TRAVEL_PT_SD"])))

            if self.state == Actor.MOVING and self.world.rules["TRAVEL_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["TRAVEL_FAIL_CHANCE"]:
                print("Travel failed")
                self.cancel_action()
                self.set_state(Actor.RECOVERING)
                return

            self.set_progress(self.progress + (move_speed * speed_mod))
            if self.target[0].length() <= self.progress:
                self.node.remove_actor(self)
                self.set_node(self.target[1])
                self.node.append_actor(self)
                self.set_state(0)
                self.set_progress(-1)
                self.set_target(None)
                self.deviation = 0
        if self.state == Actor.DIGGING:
            self.target.dig(self.deviation)
        if self.state == Actor.CONSTRUCTING:
            self.target.construct(self.deviation)
        if self.state == Actor.LOOKING:
            self.set_progress(self.progress + 1)
        if self.state == Actor.SENDING:
            for actor in self.node.actors:
                if actor.state == actor.RECEIVING:
                    actor.target.append((self.world.tick, self.target))
                    actor.set_target(actor.target)

    def pick_up_resource(self, resource):
        """
        Has the actor attempt to pick up the resource and place it in its inventory. Resource must be in the same node
        as the actor, and actor must be idle. If the resource is black, the actor must have an empty inventory.
        Otherwise, the actor must not already be holding a black resource. The actor must also have space to carry the
        resource as determined by the initialisation of the world and the amount of black buildings.

        :param resource: Resource object to be picked up
        :return: True if successful and False otherwise
        """
        if self.state == Actor.IDLE and resource.location is self.node:
            if self.resources and (resource.colour == 3 or self.resources[0].colour == 3) and self.world.modifiers["BLACK_HEAVY"]:
                print("Can hold one black and nothing else")
                return False
            if self.resources.__len__() >= self.world.modifiers["INVENTORY_SIZE"] \
                    * self.world.modifiers["BLACK_BUILDING_MODIFIER_STRENGTH"] + \
                    self.world.building_modifiers[Building.BUILDING_INVENTORY]:
                print("Inventory full, cannot pick up other resources until something is dropped")
                return False
            if self.world.rules["PICK_UP_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["PICK_UP_FAIL_CHANCE"]:
                print("Pick up failed")
                return False
            resource.set_location(self)
            self.append_resource(resource)
            self.node.remove_resource(resource)
            return True
        return False

    def drop_resource(self, resource):
        """
        Has the actor drop the resource into the node it is currently in. Actor must be idle to do so, and the resource
        should be inside the actor's inventory.

        :param resource: Resource object to be dropped
        :return: True if successful and False otherwise
        """
        if self.state == Actor.IDLE and self.resources.__contains__(resource):
            if self.world.rules["DROP_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["DROP_FAIL_CHANCE"]:
                print("Drop failed")
                return False
            resource.set_location(self.node)
            self.remove_resource(resource)
            self.node.append_resource(resource)
            return True
        return False

    def drop_everything(self):
        """
        Has the actor drop everything in it's inventory into the actor's current node, leaving it holding nothing.
        Actor must be idle to do this

        :return: True if successful and False otherwise
        """
        if self.state == Actor.IDLE:
            for resource in self.resources:
                self.drop_resource(resource)
            return True
        return False

    def dig_at(self, mine):
        """
        Tells the actor to start digging at the selected mine. Actor must be idle to start digging and the mine should
        be at the same node as the actor. When the actor is updated via update(), the actor makes progress towards
        digging.

        :param mine: The mine object the actor should start digging at.
        :return: True if successful and otherwise False
        """
        if self.state == Actor.IDLE and mine.node == self.node:
            self.set_state(Actor.DIGGING)
            self.set_target(mine)
            return True
        return False

    def start_site(self, colour, target_task=None):
        """
        Has the actor create a new "construction" site to create a building. Site is created in the same node as the
        actor. Actor must be idle to do this.

        :param colour: The colour of the construction site to make
        :return True if successful and False otherwise
        """
        if self.state == Actor.IDLE:
            if self.world.rules["SITE_CREATION_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["SITE_CREATION_FAIL_CHANCE"]:
                print("Site Creation failed")
                return False
            self.world.add_site(self.node, colour, target_task=target_task)
            return True
        return False

    def construct_at(self, site):
        """
        Tells the actor to begin building at the construction site. The site must be in the same node as the actor, and
        the actor must be idle. The actor will automatically stop building when it cannot build anymore due to a lack of
        materials or if the building is complete. When the actor is updated via update(), the actor makes progress
        towards building

        :param site: The site the actor should start building at.
        :return: True if successful and otherwise False
        """
        if self.state == Actor.IDLE and self.node == site.node:

            self.deviation = nr.normal(self.world.modifiers["BUILD_SPEED"],
                                       self.world.modifiers["CONSTRUCTING_OVERALL_SD"]) \
                if self.world.rules["CONSTRUCTING_TU"] else 0

            self.set_state(Actor.CONSTRUCTING)
            self.set_target(site)
            return True
        return False

    def deposit(self, site, resource):
        """
        Tells the actor to deposit a resource object into a construction site. The site must be in the same node as the
        actor, the actor must be idle, the resource should be in the actors inventory or in the same node as the site
        and the actor, and the site should still need that type of resource.

        :param site: The site in which to drop off the resource
        :param resource: The resource to drop off
        :return: True if successful and False otherwise
        """
        if self.resources.__contains__(resource) \
                and (self.node.sites.__contains__(site) or self.node.buildings.__contains__(site)) \
                and self.state == Actor.IDLE:
            if self.world.rules["DEPOSIT_NON_DETERMINISTIC"] and r.random() < \
                    self.world.modifiers["DEPOSIT_FAIL_CHANCE"]:
                print("Deposit failed")
                return False
            return site.deposit_resources(resource)
        return False

    def cancel_action(self):
        """
        A call to cancel any ongoing actions. If the actor is moving along an edge between two nodes, then it turns
        around and must return to the original node before being to make another action. If the actor is digging and
        there are no other actors digging (or not enough to continue digging if the mine is orange) then the progress
        towards getting a resource from the mine is lost. If the actor is constructing a building or actor at a green
        building then it simply stop the progress at the place it was in. If the actor is recovering after failing a
        movement action, it cannot cancel the action, and must return to its starting node. If the actor is looking,
        then it simply becomes idle.

        :return: True if action was successfully cancelled or False if action is not cancelable
        """
        if self.state == Actor.MOVING:
            self.set_progress(self.target[0].length() - self.progress)
            return_node = self.node
            self.node.remove_actor(self)
            self.set_node(self.target[1])
            self.node.append_actor(self)
            self.set_target((self.target[0], return_node))
            return True
        elif self.state == Actor.DIGGING:
            num_of_helpers = -1 * self.world.modifiers["ORANGE_ACTORS_TO_MINE"] if self.target.colour == 2 else -1
            for actor in self.node.actors:
                if actor.target == self.target:
                    num_of_helpers += 1

            if num_of_helpers <= 0:
                self.target.set_progress(0)
            self.go_idle()
            return True
        elif self.state == Actor.CONSTRUCTING or self.state == Actor.LOOKING or self.state == Actor.SENDING or \
                self.state == Actor.RECEIVING:
            self.go_idle()
            return True
        return False

    def go_idle(self):
        """
        Has the actor become Idle and forgot its target
        """
        self.set_target(None)
        self.set_state(0)
        self.deviation = 0
        self.set_progress(-1)

    def look(self):
        """
        Tells the actor to begin "looking". If any part of the simulation is considered partially observable, then
        looking will allow the actor to see past its own node. Every tick, an actor can see more around itself. Actor
        must be idle

        :return: True if actor begins "looking" and False otherwise
        """
        if self.state == Actor.IDLE:
            self.set_state(Actor.LOOKING)
            self.set_progress(0)
            return True
        return False

    def start_sending(self, message):
        if self.state == Actor.IDLE:
            self.set_target(message)
            self.set_state(Actor.SENDING)
            return True
        return False

    def start_receiving(self):
        if self.state == Actor.IDLE:
            self.set_target([])
            self.set_state(Actor.RECEIVING)
            return True
        return False

    def set_node(self, node):
        """
        Sets the node current node the actor is in, and keeps track of it in the actor's fields.

        :param node: the new current node
        """
        self.node = node
        self.fields.__setitem__("node", node.id)
    
    def set_state(self, state):
        """
        Sets the actor's state, and keeps track of it in the actor's fields

        :param state: the new state
        """
        self.state = state
        self.fields.__setitem__("state", state)
    
    def set_progress(self, progress):
        """
        Sets the progress the actor has made and keeps track of it in the actor's fields

        :param progress: the new value of progress
        """
        self.progress = progress
        self.fields.__setitem__("progress", progress)
    
    def set_target(self, target):
        """
        Sets the new target of the actor and keeps track of the id of the target, if it has one.

        :param target: the new target
        """
        self.target = target
        if isinstance(target, tuple):
            self.fields.__setitem__("target", (target[0].id, target[1].id))
        else:
            try:
                self.fields.__setitem__("target", target.id)
            except AttributeError:
                self.fields.__setitem__("target", target)
    
    def append_resource(self, resource):
        """
        Adds a resource to the inventory of the actor and adds the relevant id to the actor's fields

        :param resource: resource to be added to the inventory
        """
        self.resources.append(resource)
        self.fields.get("resources").append(resource.id)
        
    def remove_resource(self, resource):
        """
        Removes the resource from the inventory and removes the relevant id from the actor's fields

        :param resource: resource to be removed from the inventory
        """
        self.resources.remove(resource)
        self.fields.get("resources").remove(resource.id)
