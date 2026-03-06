"""
Future Predictor - Predicts and ranks future scenarios.
"""

from simulation_engine import SimulationEngine
from scenario_generator import ScenarioGenerator


class FuturePredictor:
    def __init__(self, domain="urban_transport", simulations=5):
        self.domain = domain
        self.simulations = simulations
        self.engine = SimulationEngine(domain)
        self.generator = ScenarioGenerator(domain)
        self.memory = []

    def predict(self, question):
        scenarios = self.generator.generate_question_scenarios(question)
        all_results = {}
        all_scores = {}

        for name, actions in scenarios.items():
            scores_accum = {}
            for _ in range(self.simulations):
                result = self.engine.run_scenario(actions)
                scores = self.engine.evaluate_scenario(result)
                for k, v in scores.items():
                    scores_accum[k] = scores_accum.get(k, 0) + v
            avg = {k: round(v / self.simulations, 2) for k, v in scores_accum.items()}
            all_results[name] = avg
            all_scores[name] = avg["overall"]

        best = max(all_scores, key=all_scores.get)
        worst = min(all_scores, key=all_scores.get)

        prediction = {
            "question": question,
            "domain": self.domain,
            "scenarios": list(scenarios.keys()),
            "scores": all_results,
            "best_scenario": best,
            "worst_scenario": worst,
            "recommendation": self._recommend(best, all_results[best]),
        }
        self.memory.append(prediction)
        return prediction

    def _recommend(self, best, scores):
        name = best.replace("_", " ").title()
        return (
            f"Recommended: {name}. "
            f"Environment: {scores.get('environment', 0)}, "
            f"Economy: {scores.get('economy', 0)}, "
            f"Satisfaction: {scores.get('satisfaction', 0)}, "
            f"Overall: {scores.get('overall', 0)}"
        )

    def explain(self, prediction):
        lines = [
            f"Question: {prediction['question']}",
            f"Domain: {prediction['domain']}",
            "",
            "Scenario Scores:",
        ]
        for name, scores in prediction["scores"].items():
            lines.append(f"  {name}: overall={scores.get('overall', 0)}")
        lines.append("")
        lines.append(f"Best: {prediction['best_scenario']}")
        lines.append(f"Recommendation: {prediction['recommendation']}")
        return "\n".join(lines)
