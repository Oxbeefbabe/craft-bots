class PlanningAgent:

    MOVE_TO = 0
    PICK_UP_RESOURCE = 2
    DROP_RESOURCE = 3
    DROP_ALL_RESOURCES = 4
    DIG_AT = 5
    START_SITE = 6
    CONSTRUCT_AT = 7
    DEPOSIT_RESOURCES = 8

    def __init__(self, api, world_info):
        self.api = api
        self.thinking = False
        self.world_info = world_info

    def get_next_commands(self):
        print(self.get_available_commands(self.world_info))
        self.thinking = False

    def get_available_commands(self, info):
        available_commands = []
        for actor in info["actors"].values():
            if not actor["state"]:
                current_node = info["nodes"][actor["node"]]

                # Move along any edge that is connected to the actors current node
                for edge in current_node["edges"]:
                    available_commands.append(
                        (actor["id"], self.MOVE_TO,
                         info["edges"][edge]["get_other_node"](current_node["id"])))

                # Pick up any resources that are on the same node as the actor
                for resource in current_node["resources"]:
                    available_commands.append((actor["id"], self.PICK_UP_RESOURCE, resource))

                # Drop any resources that the actor is currently holding onto the node it is at
                for resource in actor["resources"]:
                    available_commands.append((actor["id"], self.DROP_RESOURCE, resource))

                # Drop all the resources the actor is currently holding onto the node it is at
                if actor["resources"]:
                    available_commands.append((actor["id"], self.DROP_ALL_RESOURCES))

                # Dig at any mines the actor is currently at
                for mine in current_node["mines"]:
                    available_commands.append((actor["id"], self.DIG_AT, mine))

                # Start the site of any tasks at the current node if they don't already have a project
                for task in current_node["tasks"]:
                    if info["tasks"][task]["project"] is None:
                        available_commands.append((actor["id"], self.START_SITE, task))

                # Construct at any sites at the node the actor is currently at

                # Deposit any resources in the actors inventory into the site if the site is at the same node and still
                # needs that type of resource
                for site in current_node["sites"]:
                    available_commands.append((actor["id"], self.CONSTRUCT_AT, site))

                    remaining_requests = self.api.get_field(site, "needed_resources")
                    deposited_resources = self.api.get_field(site, "remaining_resources")
                    for i, r in enumerate(remaining_requests):
                        remaining_requests[i] = r - deposited_resources[i]

                    for resource in actor["resources"]:
                        if remaining_requests[self.api.get_field(resource, "colour")]:
                            available_commands.append((actor.id, self.DEPOSIT_RESOURCES, site, resource))

        return available_commands

    def predict_outcome(self, info, command):
        pass