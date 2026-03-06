"""
Simulation Engine - Runs future scenario simulations
using the world model to predict outcomes.
"""

import random
import copy
from typing import List, Dict, Any
from world_model import WorldModel


class SimulationEngine:
    """
    Runs multiple simulation steps to predict
    future states of the world given a sequence of actions.
    """

    def __init__(self, domain: str = "urban_transport", steps: int = 10):
        self.domain = domain
        self.steps = steps
        self.world = WorldModel(domain)

    def run_scenario(self, actions: List[str]) -> Dict[str, Any]:
        """
        Simulate a scenario given a list of actions.
        Returns final state and trajectory.
        """
        self.world.reset()
        trajectory = []
        trajectory.append(copy.deepcopy(self.world.state.variables))

        for step in range(self.steps):
            action = actions[step % len(actions)] if actions else "none"
            delta = self.world.predict_transition(action)
            if delta:
                self.world.state.apply_delta(delta)
            noise = {k: random.gauss(0, 0.5) for k in self.world.state.variables}
            self.world.state.apply_delta(noise)
            trajectory.append(copy.deepcopy(self.world.state.variables))

        return {
            "domain": self.domain,
            "actions": actions,
            "steps": self.steps,
            "final_state": self.world.state.variables,
            "trajectory": trajectory,
        }

    def compare_scenarios(self, scenarios: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Run multiple scenarios and compare their outcomes.
        """
        results = {}
        for name, actions in scenarios.items():
            results[name] = self.run_scenario(actions)
        return results

    def evaluate_scenario(self, result: Dict[str, Any]) -> Dict[str, float]:
        """
        Score a scenario result based on key metrics.
        Higher is better.
        """
        state = result["final_state"]
        score = {
            "environment": max(0, 100 - state.get("pollution_index", 100)),
            "economy": state.get("economic_output", 0),
            "safety": max(0, 100 - state.get("road_accidents", 100)),
            "satisfaction": state.get("public_satisfaction", 0),
            "employment": state.get("employment_rate", 0),
        }
        score["overall"] = sum(score.values()) / len(score)
        return score

    def best_scenario(self, scenarios: Dict[str, List[str]]) -> str:
        """
        Return the name of the best scenario by overall score.
        """
        results = self.compare_scenarios(scenarios)
        scores = {name: self.evaluate_scenario(res)["overall"]
                  for name, res in results.items()}
        return max(scores, key=scores.get)
