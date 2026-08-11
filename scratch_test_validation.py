from kaggle_environments import make

env = make("kaggriculture", debug=True)

def agent1(obs, conf):
    return {'farmer': ['PASS'], 'hands': [], 'market': [['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['HIRE'], ['BUY_LAND']]}
    return {'farmer': ['PASS'], 'hands': [], 'market': []}

def agent2(obs, conf):
    return {'farmer': ['PASS'], 'hands': [], 'market': []}

out = env.run([agent1, agent2])
print("Agent 1 action at step 1:", out[1][0].action)
