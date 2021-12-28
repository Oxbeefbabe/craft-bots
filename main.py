def run_once():
    import time
    from agents import basic_rba
    from craftbots import craft_bots

    start = time.perf_counter()
    craft_bots.start_simulation(agent_class=basic_rba.Basic_RBA,
                                use_gui=True,
                                modifier_file="craftbots/initialisation_files/simple_modifiers",
                                world_modifier_file="craftbots/initialisation_files/simple_world_gen_modifiers",
                                rule_file="craftbots/initialisation_files/simple_rules"
                                )
    print(f"\n{time.perf_counter() - start}")

def run_evaluation():
    import evaluator
    from agents import basic_rba
    from agents import bogo

    agents = [basic_rba.Basic_RBA, bogo.Bogo]
    print(evaluator.run_evaluator(agents, 2,
                                  "craftbots/initialisation_files/simple_modifiers",
                                  "craftbots/initialisation_files/simple_rules",
                                  "craftbots/initialisation_files/simple_world_gen_modifiers",
                                  agent_names=["RBA", "Bogo"]
                                  ))

if __name__ == '__main__':
    run_evaluation()