import math
import view
import model
import random as r


TICK_HZ = 60

WIDTH = 600
HEIGHT = 600
PADDING = 25
NODE_SIZE = 20


def init_scenario():
    world = model.World(WIDTH, HEIGHT)
    actors = []
    for _ in range(5):
        actors.append(model.Actor(world))
    model.Resource(world, world.actors[0], 0)
    model.Resource(world, world.actors[1], 1)
    model.Resource(world, world.actors[2], 2)
    model.Resource(world, world.actors[3], 3)
    model.Resource(world, world.actors[4], 4)
    return world
       
        
def init_gui(world):
    root = view.tk.Tk()
    root.geometry(str(WIDTH + PADDING * 2) + "x" + str(HEIGHT + PADDING * 2))
    return view.GUI(world, width=WIDTH, height=HEIGHT, padding=PADDING, node_size=NODE_SIZE, master=root)
    

def keep_moving(actors, sim_gui, world):
    for actor in actors:
        if not actor.state:
            if actor.inventory and world.tick > 200:
                actor.drop_everything()
            elif not actor.inventory and world.tick > 200 and actor.node.resources:
                actor.pick_up_resource(actor.node.resources[r.randint(0, actor.node.resources.__len__() - 1)])
            actor.travel_rand()

    def call_keep_moving():
        keep_moving(actors, sim_gui, world)
    sim_gui.after(500, call_keep_moving)


def refresh(world, sim_gui):
    world.run_tick()
    sim_gui.update_model()

    def call_refresh():
        refresh(world, sim_gui)
    sim_gui.after(math.ceil(1000/TICK_HZ), call_refresh)


if __name__ == '__main__':
    new_world = init_scenario()
    gui = init_gui(new_world)
    refresh(new_world, gui)
    keep_moving(new_world.actors, gui, new_world)
    gui.mainloop()
