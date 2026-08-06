from kaggle_environments import make
import sys
env = make('kaggriculture', debug=True, configuration={'boardSize': 22})
env.run(['main.py', 'starter'])
for day in range(24, 30):
    day_start = day * 24
    for step_i in range(day_start, min(day_start+24, len(env.steps))):
        s = env.steps[step_i]
        obs = s[0].observation
        money = obs['farms'][0]['money']
        hour = obs['hour']
        a = s[0].action or {}
        market = [m for m in (a.get('market') or []) if m]
        if market:
            print(f'Day {day:02d} Hour {hour:02d} | money={money:.0f} | market={market}')
