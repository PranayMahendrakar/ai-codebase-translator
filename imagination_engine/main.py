"""
Artificial Imagination Engine - Main Entry Point
Simulates possible futures before making decisions.
"""

from future_predictor import FuturePredictor


def main():
    print("=" * 60)
    print("  ARTIFICIAL IMAGINATION ENGINE")
    print("  Simulating Possible Futures...")
    print("=" * 60)
    print()

    predictor = FuturePredictor(domain="urban_transport", simulations=10)

    questions = [
        "What happens if a city introduces autonomous buses?",
        "What if we expand cycling lanes?",
        "What happens with a congestion tax?",
    ]

    for question in questions:
        print(f"QUESTION: {question}")
        print("-" * 60)
        prediction = predictor.predict(question)
        explanation = predictor.explain(prediction)
        print(explanation)
        print()


if __name__ == "__main__":
    main()
