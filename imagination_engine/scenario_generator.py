"""
Scenario Generator - Creates diverse future scenarios
for the AI imagination engine to simulate.
"""

from typing import List, Dict, Any
import itertools


class ScenarioGenerator:
    """
    Generates plausible future scenarios based on
    available actions and domain context.
    """

    URBAN_TRANSPORT_ACTIONS = [
        "introduce_autonomous_buses",
        "expand_cycling_lanes",
        "implement_congestion_tax",
    ]

    def __init__(self, domain: str = "urban_transport"):
        self.domain = domain
        self.actions = self._load_actions()

    def _load_actions(self) -> List[str]:
        action_map = {
            "urban_transport": self.URBAN_TRANSPORT_ACTIONS,
        }
        return action_map.get(self.domain, self.URBAN_TRANSPORT_ACTIONS)

    def generate_single_action_scenarios(self) -> Dict[str, List[str]]:
        """One scenario per action."""
        return {action: [action] for action in self.actions}

    def generate_combined_scenarios(self) -> Dict[str, List[str]]:
        """Scenarios combining pairs of actions."""
        scenarios = {}
        for a, b in itertools.combinations(self.actions, 2):
            name = a + "_AND_" + b
            scenarios[name] = [a, b]
        return scenarios

    def generate_all_scenarios(self) -> Dict[str, List[str]]:
        """All single and combined scenarios."""
        scenarios = {}
        scenarios.update(self.generate_single_action_scenarios())
        scenarios.update(self.generate_combined_scenarios())
        scenarios["do_nothing"] = []
        return scenarios

    def describe_scenario(self, name: str, actions: List[str]) -> str:
        """Human-readable description of a scenario."""
        if not actions:
            return f"Scenario: {name} - No interventions, baseline trajectory."
        action_str = ", ".join(a.replace("_", " ") for a in actions)
        return f"Scenario: {name} - Actions: {action_str}"

    def generate_question_scenarios(self, question: str) -> Dict[str, List[str]]:
        """
        Parse a natural language question and return relevant scenarios.
        Example: What happens if a city introduces autonomous buses?
        """
        question_lower = question.lower()
        matched = []
        for action in self.actions:
            keywords = action.replace("_", " ").split()
            if any(kw in question_lower for kw in keywords):
                matched.append(action)
        if not matched:
            return self.generate_all_scenarios()
        scenarios = {"baseline": []}
        scenarios[matched[0]] = [matched[0]]
        return scenarios
