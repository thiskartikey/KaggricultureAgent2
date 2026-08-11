import environment as env
import policy

e = env.KagricultureEnvironment()
obs, info = e.reset()
done = False
while not done:
    action = policy.agent_fn(obs, info)
    obs, reward, done, trunc, info = e.step(action)

print(f"Final Score: {e.me['score']}")
print(f"Unlocked quadrants: {e.me['unlocked_quadrants']}")
print(f"Total tiles: {len(e.me['tiles'])}")
