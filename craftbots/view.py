import tkinter as tk
from entities.node import Node
from entities.actor import Actor


class GUI(tk.Frame):
    def __init__(self, world, width=350, height=350, padding=7, master=None, node_size=7):
        self.node_size = node_size
        self.padding = max(self.node_size, padding)
        self.width = width
        self.height = height
        super().__init__(master)
        self.master = master
        self.world = world
        self.graph = tk.Canvas(self, bg="black", height=self.height + self.padding * 2, width=self.width + self.padding * 2)
        self.graph.create_rectangle(self.padding - self.node_size, self.padding - self.node_size, self.width + self.padding + self.node_size,
                                    self.height + self.padding + self.node_size, fill="grey", width=0)
        self.background = self.graph.create_rectangle(self.padding, self.padding, self.width + self.padding,
                                    self.height + self.padding, fill="white", width=0)
        avg_node_x = 0
        avg_node_y = 0
        min_x = self.width + 1
        max_x = 0
        min_y = self.height + 1
        max_y = 0
        for node in self.world.nodes:
            avg_node_x += node.x
            avg_node_y += node.y
            min_x = min(node.x, min_x)
            min_y = min(node.y, min_y)
            max_x = max(node.x, max_x)
            max_y = max(node.y, max_y)
        avg_node_x /= self.world.nodes.__len__()
        avg_node_y /= self.world.nodes.__len__()
        self.centre_offset_x = avg_node_x - (self.width / 2)
        self.centre_offset_y = avg_node_y - (self.height / 2)

        if min_x - self.centre_offset_x < 0:
            self.centre_offset_x = min_x
        if max_x - self.centre_offset_x > self.width:
            self.centre_offset_x = max_x - self.width
        if min_y - self.centre_offset_y < 0:
            self.centre_offset_y = min_y
        if max_y - self.centre_offset_y > self.height:
            self.centre_offset_y = max_y - self.height

        self.update_graph()
        self.actors = []
        for actor in self.world.actors:
            self.draw_actor(actor.node.x, actor.node.y)
            self.actors.append((actor, self.graph.find_all()[-1:][0], False))
        self.resources = []
        for resource in self.world.resources:
            if isinstance(resource.location, Node):
                node_x = resource.location.x + self.padding - self.centre_offset_x
                node_y = resource.location.y + self.padding - self.centre_offset_y
                self.draw_res_on_node(resource.location, resource,
                                      self.draw_resource_sprite(node_x, node_y,
                                                                self.world.get_colour_string(resource.colour)))
            if isinstance(resource.location, Actor):
                actor_id = self.get_sprite_id_of(resource.location)
                actor_x = self.graph.coords(actor_id)[0] + self.padding - self.centre_offset_x
                actor_y = self.graph.coords(actor_id)[1] + self.padding - self.centre_offset_y
                self.draw_res_on_actor(resource.location,
                                       self.draw_resource_sprite(actor_x, actor_y,
                                                                 self.world.get_colour_string(resource.colour)))
            self.resources.append((resource, self.graph.find_all()[-1:][0]))
        self.mines = []
        for mine in self.world.mines:
            self.mines.append((mine, self.draw_mine(mine.node.x, mine.node.y, world.get_colour_string(mine.colour))))
        self.sites = []
        for site in self.world.sites:
            self.sites.append((site, self.draw_site(site.node.x, site.node.y, "purple")))
        self.buildings = []
        for building in self.world.buildings:
            self.buildings.append((building, self.draw_building(building.node.x, building.node.y, "purple")))
        self.update_actors()
        self.graph.pack()
        self.pack()

    def update_graph(self):
        for edge in self.world.edges:
            x1 = edge.node_a.x + self.padding - self.centre_offset_x
            y1 = edge.node_a.y + self.padding - self.centre_offset_y
            x2 = edge.node_b.x + self.padding - self.centre_offset_x
            y2 = edge.node_b.y + self.padding - self.centre_offset_y
            self.graph.create_line(x1, y1, x2, y2, fill="blue")
        for node in self.world.nodes:
            x = node.x + self.padding - self.centre_offset_x
            y = node.y + self.padding - self.centre_offset_y
            self.graph.create_oval(x - self.node_size, y - self.node_size, x + self.node_size, y + self.node_size, fill="white")

    def update_actors(self):
        for actor in self.world.actors:
            accounted = False
            for index, actor_pair in enumerate(self.actors):
                if actor_pair[0] == actor:
                    accounted = True
                    self.actors[index] = (actor_pair[0], actor_pair[1], False)
            if not accounted:
                self.draw_actor(actor.node.x, actor.node.y)
                self.actors.append((actor, self.graph.find_all()[-1:][0], False))

        for actor_pair in self.actors:
            if actor_pair[0].state == 0:
                dx = actor_pair[0].node.x + self.padding - self.centre_offset_x - 3 - self.graph.coords(actor_pair[1])[0]
                dy = actor_pair[0].node.y + self.padding - self.centre_offset_y - 3 - self.graph.coords(actor_pair[1])[1]
                self.graph.move(actor_pair[1], dx, dy)
            if actor_pair[0].state == 1 or actor_pair[0].state == 4:
                new_x = (actor_pair[0].target[1].x - actor_pair[0].node.x) \
                        * (actor_pair[0].progress / actor_pair[0].target[0].length()) + actor_pair[0].node.x
                new_y = (actor_pair[0].target[1].y - actor_pair[0].node.y) \
                    * (actor_pair[0].progress / actor_pair[0].target[0].length()) + actor_pair[0].node.y
                dx = new_x + self.padding - self.centre_offset_x - 3 - self.graph.coords(actor_pair[1])[0]
                dy = new_y + self.padding - self.centre_offset_y - 3 - self.graph.coords(actor_pair[1])[1]
                self.graph.move(actor_pair[1], dx, dy)

    def update_resources(self):
        for resource in self.world.resources:
            accounted = False
            for resource_pair in self.resources:
                if resource_pair[0] == resource:
                    accounted = True
            if not accounted:
                if isinstance(resource.location, Actor):

                    node_x = resource.location.node.x + self.padding - self.centre_offset_x
                    node_y = resource.location.node.y + self.padding - self.centre_offset_y
                    self.draw_res_on_actor(self.get_actor_pair_index(resource),
                                           self.draw_resource_sprite(node_x, node_y,
                                                                     self.world.get_colour_string(resource.colour)))
                else:
                    node_x = resource.location.x + self.padding - self.centre_offset_x
                    node_y = resource.location.y + self.padding - self.centre_offset_y
                    self.draw_res_on_node(resource.location, resource,
                                          self.draw_resource_sprite(node_x, node_y,
                                                                    self.world.get_colour_string(resource.colour)))
                self.resources.append((resource, self.graph.find_all()[-1:][0]))
        for resource_pair in self.resources:
            if isinstance(resource_pair[0].location, Node):
                self.draw_res_on_node(resource_pair[0].location, resource_pair[0], resource_pair[1])
            if isinstance(resource_pair[0].location, Actor):
                self.draw_res_on_actor(self.get_actor_pair_index(resource_pair[0]), resource_pair[1])

    def update_model(self):
        self.update_actors()
        self.update_resources()
        self.update_sites()
        self.update_buildings()
        if self.world.rules["RT_OR_LOCK_STEP"] == 0:
            if self.world.tick % self.world.modifiers["CYCLE_LENGTH"] > self.world.modifiers["CYCLE_LENGTH"] / 2:
                self.graph.itemconfig(self.background, fill="dark grey")
            else:
                self.graph.itemconfig(self.background, fill="white")
        
    def update_sites(self):
        for site_pair in self.sites:
            if site_pair[0].progress == 100:
                self.graph.delete(site_pair[1])
                self.sites.remove(site_pair)
        for site in self.world.sites:
            accounted = False
            for site_pair in self.sites:
                if site_pair[0] == site:
                    accounted = True
            if not accounted:
                node_x = site.node.x
                node_y = site.node.y
                self.draw_site(node_x, node_y, "purple")
                self.sites.append((site, self.graph.find_all()[-1:][0]))
    
    def update_buildings(self):
        for building in self.world.buildings:
            accounted = False
            for building_pair in self.buildings:
                if building_pair[0] == building:
                    accounted = True
            if not accounted:
                node_x = building.node.x
                node_y = building.node.y
                self.draw_building(node_x, node_y, "purple")
                self.buildings.append((building, self.graph.find_all()[-1:][0]))

    def get_actor_pair_index(self, resource):
        for index, actor_pair in enumerate(self.actors):
            if resource.location == actor_pair[0]:
                return index
        return -1

    def draw_resource_sprite(self, x, y, colour):
        return self.graph.create_polygon(x, y, x, y-1, x+1, y-1, x+1, y-2, x+2, y-2, x+2, y-4, x+2, y-2, x+3, y-2, x+3,
                                         y-1, x+4, y-1, x+4, y, x, y, fill=colour, outline=colour, width=1)

    def draw_res_on_node(self, node, resource, sprite_id):
        node_x = node.x
        node_y = node.y
        if resource.colour == 0:
            node_x -= 3
            node_y -= 14
        elif resource.colour == 1:
            node_x += 0
            node_y -= 8
        elif resource.colour == 2:
            node_x += 4
            node_y -= 12
        elif resource.colour == 3:
            node_x += 6
            node_y -= 6
        elif resource.colour == 4:
            node_x += 12
            node_y -= 4
        self.move_sprite_to(sprite_id, node_x + self.padding - self.centre_offset_x, node_y + self.padding - self.centre_offset_y)

    def draw_res_on_actor(self, actor_index, sprite_id):
        actor_pair = self.actors[actor_index]
        if actor_pair[2]:
            self.graph.itemconfigure(sprite_id, state='hidden')
        else:
            coord = self.get_coord_of(actor_pair[0])
            self.move_sprite_to(sprite_id, coord[0], coord[1])
            self.graph.itemconfigure(sprite_id, state='normal')
            self.actors[actor_index] = (actor_pair[0],actor_pair[1], True)

    def move_sprite_to(self, sprite_id, x, y):
        self.graph.move(sprite_id, x - self.graph.coords(sprite_id)[0], y - self.graph.coords(sprite_id)[1])

    def get_sprite_id_of(self, item):
        if isinstance(item, Actor):
            for actor_pair in self.actors:
                if actor_pair[0] is item:
                    return actor_pair[1]
            return -1

    def get_coord_of(self, item):
        return self.graph.coords(self.get_sprite_id_of(item))

    def draw_mine(self, node_x, node_y, colour):
        x = node_x + self.padding - self.centre_offset_x
        y = node_y + self.padding - self.centre_offset_y
        if colour == "red":
            x += 14
            y += 2
        elif colour == "blue":
            x += 12
            y += 10
        elif colour == "orange":
            x += 8
            y += 4
        elif colour == "black":
            x += 6
            y += 10
        elif colour == "green":
            x += 2
            y += 14
        return self.graph.create_oval(x - 2, y - 2, x + 2, y + 2, fill=colour, outline=colour, width=1)
    
    def draw_site(self, node_x, node_y, colour):
        x = node_x + self.padding - self.centre_offset_x
        y = node_y + self.padding - self.centre_offset_y
        if colour == "red":
            x -= 10
            y -= 8
        elif colour == "blue":
            x -= 16
            y -= 2
        elif colour == "orange":
            x -= 10
            y += 4
        elif colour == "black":
            x -= 16
            y += 8
        elif colour == "green":
            x -= 10
            y += 14
        elif colour == "purple":
            x -= 4
            y += 10
        return self.graph.create_polygon(x, y, x, y - 4, x + 1, y - 4, x + 1, y - 1, x + 3, y - 1, x + 3, y - 2,
                                         x + 4, y - 2, x + 4, y, x, y, fill=colour, outline=colour, width=1)
    
    def draw_building(self, node_x, node_y, colour):
        x = node_x + self.padding - self.centre_offset_x
        y = node_y + self.padding - self.centre_offset_y
        if colour == "red":
            x -= 8
            y -= 10
        elif colour == "blue":
            x -= 14
            y -= 4
        elif colour == "orange":
            x -= 8
            y += 2
        elif colour == "black":
            x -= 14
            y += 6
        elif colour == "green":
            x -= 8
            y += 12
        elif colour == "purple":
            x -= 2
            y += 8
        return self.graph.create_rectangle(x - 2, y - 2, x + 2, y + 2, fill=colour, outline=colour, width=1)
    
    def draw_actor(self, node_x, node_y):
        self.graph.create_oval(node_x + self.padding - self.centre_offset_x - 3,
                               node_y + self.padding - self.centre_offset_y - 3,
                               node_x + self.padding - self.centre_offset_x + 3,
                               node_y + self.padding - self.centre_offset_y + 3, fill="grey")
