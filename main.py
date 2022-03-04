def run_rba():
    import time
    from agents import basic_rba
    from craftbots import craft_bots

    print(craft_bots.start_simulation(agent_class=basic_rba.Basic_RBA,
                                use_gui=True,
                                modifier_file="craftbots/initialisation_files/simple_modifiers",
                                world_modifier_file="craftbots/initialisation_files/simple_world_gen_modifiers",
                                rule_file="craftbots/initialisation_files/simple_rules"
                                ))

def run_evaluation():
    import evaluator
    from agents import basic_rba
    from agents import bogo
    from agents import task_allocator

    agents = [task_allocator.TaskAllocator]
    print(evaluator.run_evaluator(agents, 3,
                                    "craftbots/initialisation_files/eval/simple_small/modifiers",
                                    "craftbots/initialisation_files/eval/simple_small/rules",
                                    "craftbots/initialisation_files/eval/simple_small/world_gen_modifiers",
                                    "simple_small",
                                    agent_names=["TAA"]
                                    ))

def run_demo():
    from agents import basic_rba
    from craftbots import craft_bots

    print(craft_bots.start_simulation(agent_class=basic_rba.Basic_RBA,
                                      use_gui=True,
                                      modifier_file="craftbots/initialisation_files/demo_modifiers",
                                      world_modifier_file="craftbots/initialisation_files/demo_world_gen_modifiers",
                                      rule_file="craftbots/initialisation_files/demo_rules",
                                      refresh_sim_on_end=True
                                      ))

def run_taa():
    from agents import task_allocator
    from craftbots import craft_bots

    print(craft_bots.start_simulation(agent_class=task_allocator.TaskAllocator,
                                      use_gui=True,
                                      modifier_file="craftbots/initialisation_files/eval/simple_small/modifiers",
                                      world_modifier_file="craftbots/initialisation_files/eval/simple_small/world_gen_modifiers",
                                      rule_file="craftbots/initialisation_files/eval/simple_small/rules"
                                      ))


if __name__ == '__main__':
    run_taa()