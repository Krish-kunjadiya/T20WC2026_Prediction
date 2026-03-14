import re

with open('frontend/src/pages/Simulator.jsx', 'r') as f:
    text = f.read()

# Helper block for team select
def make_select(label, name, value_var, onchange, options_var):
    return f"""                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <select name="{name}" value={{{value_var}}} onChange={{{onchange}}} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select {label}</option>
                    {{{options_var}.map(t => <option key={{t}} value={{t}}>{{t}}</option>)}}
                  </select>
                </div>"""

# Replace Pre-match Simulator inputs
# They look like: <Input\n                  label="Team A"\n                  name="team_a"\n                  value={form.team_a}\n                  onChange={handleChange}\n                  required\n                />
r_teama = re.compile(r'<Input\s+label="Team A"\s+name="team_a"\s+value=\{form.team_a\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_teama.sub(make_select('Team A', 'team_a', 'form.team_a', 'handleChange', 'teamOptions'), text)

r_teamb = re.compile(r'<Input\s+label="Team B"\s+name="team_b"\s+value=\{form.team_b\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_teamb.sub(make_select('Team B', 'team_b', 'form.team_b', 'handleChange', 'teamOptions'), text)

r_venue = re.compile(r'<Input\s+label="Venue"\s+name="venue"\s+value=\{form.venue\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_venue.sub(make_select('Venue', 'venue', 'form.venue', 'handleChange', 'venueOptions'), text)

r_toss_winner = re.compile(r'<Input\s+label="Toss Winner"\s+name="toss_winner"\s+value=\{form.toss_winner\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_toss_winner.sub(make_select('Toss Winner', 'toss_winner', 'form.toss_winner', 'handleChange', 'teamOptions'), text)


# Add same for Live Form
r_l_bat = re.compile(r'<Input\s+label="Batting Team"\s+name="batting_team"\s+value=\{liveForm.batting_team\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_bat.sub(make_select('Batting Team', 'batting_team', 'liveForm.batting_team', 'handleLiveChange', 'teamOptions'), text)

r_l_bowl = re.compile(r'<Input\s+label="Bowling Team"\s+name="bowling_team"\s+value=\{liveForm.bowling_team\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_bowl.sub(make_select('Bowling Team', 'bowling_team', 'liveForm.bowling_team', 'handleLiveChange', 'teamOptions'), text)

r_l_ven = re.compile(r'<Input\s+label="Venue"\s+name="venue"\s+value=\{liveForm.venue\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_ven.sub(make_select('Venue', 'venue', 'liveForm.venue', 'handleLiveChange', 'venueOptions'), text)


# Add same for Toss Form
r_t_teama = re.compile(r'<Input\s+label="Team"\s+name="team_a"\s+value=\{form.team_a\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_t_teama.sub(make_select('Team', 'team_a', 'form.team_a', 'handleChange', 'teamOptions'), text)

r_t_teamb = re.compile(r'<Input\s+label="Opponent"\s+name="team_b"\s+value=\{form.team_b\}\s+onChange=\{handleChange\}\s+required\s+/>', re.MULTILINE)
text = r_t_teamb.sub(make_select('Opponent', 'team_b', 'form.team_b', 'handleChange', 'teamOptions'), text)

# Toss venue already covered or it's named 'venue' in form? Oh it is named venue, so wait.. the regex for venue is <Input label="Venue" name="venue" value={form.venue} ... It might fail if toss uses form.venue too. Yes, it will replace all occurrences.

with open('frontend/src/pages/Simulator.jsx', 'w') as f:
    f.write(text)

