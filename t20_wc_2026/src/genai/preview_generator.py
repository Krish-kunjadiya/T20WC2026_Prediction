"""
AI Match Preview Generator - standalone script for testing.
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))
from rag_engine import generate_match_preview


if __name__ == "__main__":
    print("MATCH PREVIEW GENERATOR\n")
    print("=" * 55)

    previews = [
        ("India", "Australia", "MCG, Melbourne"),
        ("Pakistan", "England", "Lord's, London"),
        ("South Africa", "New Zealand", "Newlands, Cape Town"),
    ]

    for team_a, team_b, venue in previews:
        print(f"\n{team_a} vs {team_b} @ {venue}")
        print("-" * 55)
        preview = generate_match_preview(team_a, team_b, venue)
        print(preview)
        print("=" * 55)
