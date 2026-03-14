import os
import glob
import csv

input_dir = 't20s_csv2'
output_file = os.path.join(input_dir, 'matches.csv')

out_rows = []
for file in glob.glob(os.path.join(input_dir, '*_info.csv')):
    with open(file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        match_data = {
            'team1': None,
            'team2': None,
            'toss_winner': None,
            'toss_decision': None,
            'winner': None,
            'venue': None,
            'city': None,
            'date': None,
            'match_no': os.path.basename(file).split('_')[0],
            'margin': '',
            'result': ''
        }
        teams = []
        for row in reader:
            if len(row) < 3: continue
            if row[0] == 'info':
                key = row[1]
                val = row[2]
                
                if key == 'team':
                    if not match_data['team1']:
                        match_data['team1'] = val
                    else:
                        match_data['team2'] = val
                elif key == 'toss_winner':
                    match_data['toss_winner'] = val
                elif key == 'toss_decision':
                    match_data['toss_decision'] = val
                elif key == 'winner':
                    if len(row) > 2:
                        match_data['winner'] = val
                elif key == 'venue':
                    match_data['venue'] = val
                elif key == 'city':
                    match_data['city'] = val
                elif key == 'date':
                    match_data['date'] = val
                elif key == 'winner_runs':
                    match_data['margin'] = f"{val} runs"
                elif key == 'winner_wickets':
                    match_data['margin'] = f"{val} wkts"
                elif key == 'outcome':
                    if val == 'tie':
                        match_data['winner'] = 'Tie'
                        match_data['result'] = 'Tie'
                    elif val == 'no result':
                        match_data['winner'] = 'No Result'
                        match_data['result'] = 'No Result'
        
        if match_data['team1'] and match_data['team2']:
            out_rows.append(match_data)

out_rows.sort(key=lambda x: x['match_no'])

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'match_no', 'stage', 'group', 'date', 'venue', 'city', 
        'team1', 'team2', 'toss_winner', 'toss_decision', 'winner', 'result', 'margin'
    ])
    writer.writeheader()
    for r in out_rows:
        r['stage'] = ''
        r['group'] = ''
        r['result'] = 'Done' if r['winner'] not in ['Tie', 'No Result'] else r['result']
        writer.writerow(r)

print(f"Generated {output_file} with {len(out_rows)} matches.")
