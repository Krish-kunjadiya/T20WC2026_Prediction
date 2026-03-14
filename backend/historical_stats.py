import pandas as pd
import os

def get_historical_stats(team_a, team_b, venue, toss_winner, toss_decision):
    base = os.path.dirname(__file__)
    default_path = os.path.join(base, "..", "10", "matches.csv")
    matches_path = os.getenv("MATCHES_DATA_PATH", default_path)
    
    try:
        df = pd.read_csv(matches_path)
    except Exception as e:
        return {"error": str(e)}

    stats = []

    # Overall head-to-head
    mask_teams = ((df["team1"] == team_a) & (df["team2"] == team_b)) | \
                 ((df["team1"] == team_b) & (df["team2"] == team_a))
    
    h2h_df = df[mask_teams]
    h2h_matches = len(h2h_df)
    
    if h2h_matches > 0:
        h2h_a_wins = len(h2h_df[h2h_df["winner"] == team_a])
        h2h_b_wins = len(h2h_df[h2h_df["winner"] == team_b])
        stats.append(f"Head-to-head: {team_a} won {h2h_a_wins}, {team_b} won {h2h_b_wins} (out of {h2h_matches} matches).")
    else:
        stats.append(f"No previous head-to-head records found between {team_a} and {team_b}.")

    # Head-to-head at this specific venue
    venue_df = h2h_df[h2h_df["venue"] == venue]
    venue_matches = len(venue_df)
    if venue_matches > 0:
        venue_a_wins = len(venue_df[venue_df["winner"] == team_a])
        venue_b_wins = len(venue_df[venue_df["winner"] == team_b])
        stats.append(f"At {venue}, {team_a} won {venue_a_wins} and {team_b} won {venue_b_wins} head-to-head.")
    
    # Specific Toss conditions
    toss_df = h2h_df[(h2h_df["toss_winner"] == toss_winner) & (h2h_df["toss_decision"] == toss_decision)]
    toss_matches = len(toss_df)
    if toss_matches > 0:
        toss_a_wins = len(toss_df[toss_df["winner"] == team_a])
        stats.append(f"Under these exact toss conditions (Toss won by {toss_winner}, decision to {toss_decision}): {team_a} won {toss_a_wins}/{toss_matches} times.")

    # General venue team performance
    team_a_venue = df[((df["team1"] == team_a) | (df["team2"] == team_a)) & (df["venue"] == venue)]
    if len(team_a_venue) > 0:
        a_venue_wins = len(team_a_venue[team_a_venue["winner"] == team_a])
        stats.append(f"Overall at {venue}: {team_a} has won {a_venue_wins} out of {len(team_a_venue)} matches.")

    team_b_venue = df[((df["team1"] == team_b) | (df["team2"] == team_b)) & (df["venue"] == venue)]
    if len(team_b_venue) > 0:
        b_venue_wins = len(team_b_venue[team_b_venue["winner"] == team_b])
        stats.append(f"Overall at {venue}: {team_b} has won {b_venue_wins} out of {len(team_b_venue)} matches.")

    # Venue bat first vs field first bias
    overall_venue_df = df[df["venue"] == venue]
    if len(overall_venue_df) > 0:
        bat_first_wins = len(overall_venue_df[(overall_venue_df["toss_decision"] == "bat") & (overall_venue_df["winner"] == overall_venue_df["toss_winner"])])
        bat_first_wins += len(overall_venue_df[(overall_venue_df["toss_decision"] == "field") & (overall_venue_df["winner"] != overall_venue_df["toss_winner"])])
        stats.append(f"At {venue}, the team batting first has historically won {bat_first_wins} out of {len(overall_venue_df)} matches.")

    return stats
