"""
World Model - Represents the state of the environment
and tracks how actions affect the world.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class WorldState:
    """Represents the current state of the world."""
    variables: Dict[str, float] = field(default_factory=dict)
    history: List[Dict[str, float]] = field(default_factory=list)
    timestamp: int = 0

    def snapshot(self):
        return dict(self.variables)

    def apply_delta(self, delta):
        self.history.append(self.snapshot())
        for key, value in delta.items():
            self.variables[key] = self.variables.get(key, 0) + value
        self.timestamp += 1


class WorldModel:
    def __init__(self, domain="urban_transport"):
        self.domain = domain
        self.state = WorldState()
        self._initialize_domain()

    def _initialize_domain(self):
        self.state.variables = {
            "traffic_volume": 100.0,
            "pollution_index": 75.0,
            "employment_rate": 85.0,
            "public_satisfaction": 60.0,
            "economic_output": 100.0,
            "road_accidents": 50.0,
            "co2_emissions": 80.0,
        }

    def predict_transition(self, action, intensity=1.0):
        effects = {
            "introduce_autonomous_buses": {
                "traffic_volume": -15.0,
                "pollution_index": -20.0,
                "employment_rate": -5.0,
                "public_satisfaction": 10.0,
                "economic_output": 8.0,
                "road_accidents": -25.0,
                "co2_emissions": -18.0,
            },
            "expand_cycling_lanes": {
                "traffic_volume": -8.0,
                "pollution_index": -10.0,
                "employment_rate": 2.0,
                "public_satisfaction": 15.0,
                "road_accidents": -10.0,
                "co2_emissions": -8.0,
            },
            "implement_congestion_tax": {
                "traffic_volume": -20.0,
                "pollution_index": -12.0,
                "economic_output": -5.0,
                "public_satisfaction": -8.0,
                "co2_emissions": -15.0,
            },
        }
        return {k: v * intensity for k, v in effects.get(action, {}).items()}

    def get_state_summary(self):
        return {
            "domain": self.domain,
            "timestamp": self.state.timestamp,
            "variables": self.state.variables,
        }

    def reset(self):
        self.state = WorldState()
        self._initialize_domain()
