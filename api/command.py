class Command:

    MOVE_TO = 0
    MOVE_RAND = 1
    PICK_UP_RESOURCE = 2
    DROP_RESOURCE = 3
    DROP_ALL_RESOURCES = 4
    DIG_AT = 5
    START_SITE = 6
    CONSTRUCT_AT = 7
    DEPOSIT_RESOURCES = 8
    CANCEL_ACTION = 9
    START_LOOKING = 10
    START_SENDING = 11
    START_RECEIVING = 12

    PENDING = 0
    ACTIVE = 1
    REJECTED = 2
    COMPLETED = 3

    def __init__(self, world, function_id, save, *args):
        self.world = world
        self.id = self.world.get_new_id()
        self.world.command_queue.append(self)
        self.function_id = function_id
        self.args = args
        self.result = None
        self.state = Command.PENDING
        self.save = save

        self.fields = {"id": self.id, "function_id": self.function_id, "args": self.args, "result": self.result,
                       "state": self.state}

    def __str__(self):
        command_names = {self.MOVE_TO : "move_to",
    self.MOVE_RAND : "move_rand",
    self.PICK_UP_RESOURCE : "pick_up_resource",
    self.DROP_RESOURCE : "drop_resource",
    self.DROP_ALL_RESOURCES : "drop_all_resources",
    self.DIG_AT : "dig_at",
    self.START_SITE : "start_site",
    self.CONSTRUCT_AT : "construct_at",
    self.DEPOSIT_RESOURCES : "deposit_resource",
    self.CANCEL_ACTION : "cancel_action",
    self.START_LOOKING : "start_looking",
    self.START_SENDING : "start_sending",
    self.START_RECEIVING : "start_receiving"}
        return f" Command({command_names[self.function_id]}, {self.args})"
    
    def __repr__(self):
        return self.__str__()
    
    def perform(self):
        if self.function_id == Command.MOVE_TO and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            target_node = self.world.get_by_id(self.args[1], entity_type="Node")
            if actor is not None and target_node is not None:
                self.set_result(actor.travel_to(target_node))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.MOVE_RAND and self.args.__len__() == 1:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.travel_rand())
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.PICK_UP_RESOURCE and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            resource = self.world.get_by_id(self.args[1], entity_type="Resource")
            if actor is not None and resource is not None:
                self.set_result(actor.pick_up_resource(resource))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.DROP_RESOURCE and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            resource = self.world.get_by_id(self.args[1], entity_type="Resource")
            if actor is not None and resource is not None:
                self.set_result(actor.drop_resource(resource))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.DROP_ALL_RESOURCES and self.args.__len__() == 1:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.drop_everything())
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.DIG_AT and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            mine = self.world.get_by_id(self.args[1], entity_type="Mine")
            if actor is not None and mine is not None:
                self.set_result(actor.dig_at(mine))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.START_SITE and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.start_site(self.args[1]))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.START_SITE and self.args.__len__() == 3:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            target_task = self.world.get_by_id(self.args[2], entity_type="Task")
            if actor is not None:
                self.set_result(actor.start_site(self.args[1], target_task))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.CONSTRUCT_AT and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            site = self.world.get_by_id(self.args[1], entity_type="Site")
            if site is None:
                site = self.world.get_by_id(self.args[1], entity_type="Building")
            if actor is not None and site is not None:
                self.set_result(actor.construct_at(site))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.DEPOSIT_RESOURCES and self.args.__len__() == 3:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            site = self.world.get_by_id(self.args[1], entity_type="Site")
            if site is None:
                site = self.world.get_by_id(self.args[1], entity_type="Building")
            resource = self.world.get_by_id(self.args[2], entity_type="Resource")
            if actor is not None and site is not None and resource is not None:
                self.set_result(actor.deposit(site, resource))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.CANCEL_ACTION and self.args.__len__() == 1:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.cancel_action())
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.START_LOOKING and self.args.__len__() == 1:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.look())
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.START_SENDING and self.args.__len__() == 2:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.start_sending(self.args[1]))
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        elif self.function_id == Command.START_RECEIVING and self.args.__len__() == 1:
            self.set_state(Command.ACTIVE)
            actor = self.world.get_by_id(self.args[0], entity_type="Actor")
            if actor is not None:
                self.set_result(actor.start_receiving())
                self.set_state(Command.COMPLETED)
                return self.result
            self.set_state(Command.REJECTED)
            return False
        else:
            self.set_state(Command.REJECTED)
            return False

    def set_result(self, result):
        self.result = result
        self.fields.__setitem__("result", result)
        
    def set_state(self, state):
        self.state = state
        self.fields.__setitem__("state", state)
