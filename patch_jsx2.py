import re

with open('C:/Windows/Temp/Simulator.jsx', 'r') as f:
    text = f.read()

# Helper block for team select
def make_select(label, name, value_var, onchange, options_var):
    return f"""                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <select name="{name}" value={{{value_var}}} onChange={{{onchange}}} className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:ring-primary-500" required>
                    <option value="">Select {label}</option>
                    {{{options_var}?.map(t => <option key={{t}} value={{t}}>{{t}}</option>)}}
                  </select>
                </div>"""

# Live Form uses lower case tags:
r_l_bat = re.compile(r'<Input\s+label="Batting team"\s+name="batting_team"\s+value=\{liveForm.batting_team\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_bat.sub(make_select('Batting team', 'batting_team', 'liveForm.batting_team', 'handleLiveChange', 'teamOptions'), text)

r_l_bowl = re.compile(r'<Input\s+label="Bowling team"\s+name="bowling_team"\s+value=\{liveForm.bowling_team\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_bowl.sub(make_select('Bowling team', 'bowling_team', 'liveForm.bowling_team', 'handleLiveChange', 'teamOptions'), text)

r_l_ven = re.compile(r'<Input\s+label="Venue"\s+name="venue"\s+value=\{liveForm.venue\}\s+onChange=\{handleLiveChange\}\s+required\s+/>', re.MULTILINE)
text = r_l_ven.sub(make_select('Venue', 'venue', 'liveForm.venue', 'handleLiveChange', 'venueOptions'), text)

with open('frontend/src/pages/Simulator.jsx', 'w') as f:
    f.write(text)
