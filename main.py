from agents import basic_rba
from craftbots import craft_bots

if __name__ == '__main__':
    craft_bots.start_simulation(agent_class=basic_rba.Basic_RBA,
                                use_gui=True,
                                modifier_file="craftbots/initialisation_files/simple_modifiers",
                                world_modifier_file="craftbots/initialisation_files/simple_world_gen_modifiers",
                                rule_file="craftbots/initialisation_files/simple_rules"
                                )
