# basic-genetic-neuro-agent
creating 100 neural agents in a maze that must reach the finish line

The program is based on a simple neural network, where an agent operates with 6 input neurons: 5 sensors determine the distance to the wall, and 1 acts as a “compass”, indicating the direction to the finish line.

A genetic method was used. In each generation, the most adapted individuals (those closest to the goal) are selected, their parameters (the weights of neural connections) mutate, and are passed on to the next generation.
