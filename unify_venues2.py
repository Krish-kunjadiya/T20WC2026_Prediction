import pandas as pd
import json
import glob
import os
import difflib

def get_city_from_venue(venue):
    city_map = {
        'Melbourne Cricket Ground': 'Melbourne',
        'Adelaide Oval': 'Adelaide',
        'Harare Sports Club': 'Harare',
        'Dubai International Cricket Stadium': 'Dubai',
        'Sydney Cricket Ground': 'Sydney',
        'Sharjah Cricket Stadium': 'Sharjah',
        'Carrara Oval': 'Queensland',
        'Colombo Cricket Club Ground': 'Colombo',
        'Sydney Showground Stadium': 'Sydney',
        'Perth Stadium': 'Perth',
        'Rawalpindi Cricket Stadium': 'Rawalpindi',
        'Multan Cricket Stadium': 'Multan',
        'Rangiri Dambulla International Stadium': 'Dambulla',
        'AMI Stadium': 'Christchurch',
        'Amini Park': 'Port Moresby',
        'Arun Jaitley Stadium': 'Delhi',
        'Barabati Stadium': 'Cuttack',
        'Barsapara Cricket Stadium': 'Guwahati',
        'Basin Reserve': 'Wellington',
        'Bay Oval': 'Mount Maunganui',
        'Bellerive Oval': 'Hobart',
        'Brabourne Stadium': 'Cuttack',
        'Buffalo Park': 'East London',
        'Cartama Oval': 'Cartama',
        'Chilaw Marians Cricket Club Ground': 'Colombo',
        'Colts Cricket Club Ground': 'Colombo',
        'Desert Springs Cricket Ground': 'Almeria',
        'Edgbaston': 'Birmingham',
        'Godinger Fitness CC': 'Moorslede',
        'W.A.C.A. Ground': 'Perth',
        'WACA Ground': 'Perth',
        'SuperSport Park': 'East London',
        'Shere Bangla National Stadium': 'Mirpur',
        'R Premadasa Stadium': 'Dambulla',
        'Pukekura Park': 'New Plymouth',
    }
    for key, city in city_map.items():
        if venue.startswith(key):
            return city
    return None

def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def process_venues():
    df_t20 = pd.read_csv('t20s_csv2/matches.csv')
    
    # Fill in missing cities dynamically using other rows that have the same venue
    venue_city_map = df_t20.dropna(subset=['city']).groupby('venue')['city'].first().to_dict()
    unique_venues = df_t20['venue'].dropna().unique().tolist()
    
    # Bring in venues from Data/ venues.csv to ensure we cover frontend ones too
    df_data = pd.read_csv('Data/venues.csv')
    for v in df_data['venue_name']:
        if v not in unique_venues:
            unique_venues.append(v)
            
    mapping = {}
    for venue in unique_venues:
        new_v = venue
        # Fix known duplicates / minor spellings
        new_v = new_v.replace('M.Chinnaswamy', 'M Chinnaswamy')
        new_v = new_v.replace('W.A.C.A.', 'WACA')
        
        if ',' not in new_v:
            city = venue_city_map.get(venue)
            if not city or pd.isna(city):
                city = get_city_from_venue(new_v)
            if city and city not in new_v:
                new_v = f"{new_v}, {city}"
        mapping[venue] = new_v

    # Fuzz / grouping
    final_mapping = {}
    mapped_vals = list(mapping.values())
    
    for old_v, new_v in mapping.items():
        best_match = new_v
        for cand in mapped_vals:
            # Check similarity
            if similar(new_v.lower(), cand.lower()) > 0.92:
                if ',' in cand and ',' not in best_match:
                    best_match = cand
                elif len(cand) > len(best_match) and (',' in cand) == (',' in best_match):
                    best_match = cand
        final_mapping[old_v] = best_match

    with open('venue_updates.json', 'w') as f:
        json.dump(final_mapping, f, indent=4)
        
    print(f"Generated {len(final_mapping)} mappings in venue_updates.json")

if __name__ == '__main__':
    process_venues()
