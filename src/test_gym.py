import gym
import random
import argparse
import numpy as np

from deepqnetwork import DeepQNetwork

parser = argparse.ArgumentParser()

envarg = parser.add_argument_group('Environment')
envarg.add_argument("env_id", help="Which atari game to test such as Breakout-v0")
envarg.add_argument("--screen_width", type=int, default=40, help="Screen width after resize.")
envarg.add_argument("--screen_height", type=int, default=52, help="Screen height after resize.")

memarg = parser.add_argument_group('Replay memory')
memarg.add_argument("--replay_size", type=int, default=10000, help="Maximum size of replay memory.")
memarg.add_argument("--history_length", type=int, default=4, help="How many screen frames form a state.")
memarg.add_argument("--min_reward", type=float, default=-1, help="Minimum reward.")
memarg.add_argument("--max_reward", type=float, default=1, help="Maximum reward.")

netarg = parser.add_argument_group('Deep Q-learning network')
netarg.add_argument("--learning_rate", type=float, default=0.00025, help="Learning rate.")
netarg.add_argument("--discount_rate", type=float, default=0.99, help="Discount rate for future rewards.")
netarg.add_argument("--batch_size", type=int, default=32, help="Batch size for neural network.")
netarg.add_argument('--optimizer', choices=['rmsprop', 'adam', 'adadelta'], default='rmsprop', help='Network optimization algorithm.')
netarg.add_argument("--decay_rate", type=float, default=0.95, help="Decay rate for RMSProp and Adadelta algorithms.")
netarg.add_argument("--clip_error", type=float, default=1, help="Clip error term in update between this number and its negative.")
netarg.add_argument("--target_steps", type=int, default=10000, help="Copy main network to target network after this many steps.")

neonarg = parser.add_argument_group('Neon')
neonarg.add_argument('--backend', choices=['cpu', 'gpu'], default='gpu', help='backend type')
neonarg.add_argument('--device_id', type=int, default=0, help='gpu device id (only used with GPU backend)')
neonarg.add_argument('--datatype', choices=['float16', 'float32', 'float64'], default='float32', help='default floating point precision for backend [f64 for cpu only]')
neonarg.add_argument('--stochastic_round', const=True, type=int, nargs='?', default=False, help='use stochastic rounding [will round to BITS number of bits if specified]')

antarg = parser.add_argument_group('Agent')
antarg.add_argument("--exploration_rate_test", type=float, default=0.05, help="Exploration rate used during testing.")
antarg.add_argument("--random_starts", type=int, default=30, help="Perform max this number of dummy actions after game restart, to produce more random game dynamics.")

mainarg = parser.add_argument_group('Main loop')
mainarg.add_argument("--load_weights", help="Load network from file.")
mainarg.add_argument("--save_weights_prefix", help="Save network to given file. Epoch and extension will be appended.")

comarg = parser.add_argument_group('Common')
comarg.add_argument("output_folder", help="Where to write results to.")
comarg.add_argument("--num_episodes", type=int, default=10, help="Number of episodes to test.")
comarg.add_argument("--random_seed", type=int, help="Random seed for repeatable experiments.")
args = parser.parse_args()

if args.random_seed:
  random.seed(args.random_seed)

class GymAgent():
    def __init__(self, env, net, memory, args):
        self.env = env
        self.net = net
        self.memory = memory
        self.history_length = args.history_length
        self.exploration_rate_test = args.exploration_rate_test

    def add(self, observation):
        self.memory[0, :-1] = self.memory[0, 1:]
        self.memory[0, -1] = np.array(observation)

    def get_action(self, t, observation):
        self.add(observation)
        if t < self.history_length or random.random() < self.exploration_rate_test:
            action = env.action_space.sample()
        else:
            qvalues = net.predict(memory)
            action = np.argmax(qvalues[0])
        return action

env = gym.make(args.env_id)
net = DeepQNetwork(env.action_space.n, args)
memory = np.empty((args.batch_size, args.history_length, args.screen_height, args.screen_width))

if args.load_weights:
  print "Loading weights from %s" % args.load_weights
  net.load_weights(args.load_weights)

agent = GymAgent(env, net, memory, args)

env.monitor.start(args.output_folder, force=True)
avg_reward = 0
num_episodes = 100
for i_episode in xrange(num_episodes):
    observation = env.reset()
    i_total_reward = 0
    for t in xrange(10000):
        action = agent.get_action(t, observation)
        observation, reward, done, info = env.step(action)
        i_total_reward += reward
        if done:
            avg_reward += i_total_reward
            print "Episode {} finished after {} timesteps with reward {}".format(i_episode+1, t+1, i_total_reward)
            break
print "Avg reward {}".format(avg_reward / float(num_episodes))
env.monitor.close()