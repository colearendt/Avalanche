import cvxpy as cvx
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from random import shuffle


def binarize_probabilities(mat):
    num_probs = mat.shape[0] * mat.shape[1]
    probs = np.random.uniform(size=num_probs).reshape(mat.shape)

    bin_mat = np.zeros_like(mat)
    for i in xrange(mat.shape[0]):
        for j in xrange(mat.shape[1]):
            bin_mat[i, j] = 1 if probs[i, j] < mat[i, j] else 0
    return bin_mat


def distribute_liabilities(adj_matrix, total_liabilities):
    size = adj_matrix.shape[0]
    liability_mat = np.zeros_like(adj_matrix)
    for i, liability in enumerate(total_liabilities):
        conns = adj_matrix[i, :].sum()
        if conns == 0:
            continue
        avg_liability = liability / conns
        for j in xrange(size):
            liability_mat[i, j] = adj_matrix[i, j] * avg_liability
    return liability_mat


def make_connections(connectivity_vector, randomize=False, probabilities=True):
    size = connectivity_vector.shape[0]
    connections = cvx.Variable(size, size)
    objective = cvx.Minimize(cvx.sum_entries(connections))

    constraints = [connections[i, i] == 1 for i in range(size)]
    for i, connection in enumerate(connectivity_vector):
        connection_constraint = cvx.sum_entries(connections[i, :]) + cvx.sum_entries(connections[:, i]) >= connection
        constraints.append(connection_constraint)

    for i in range(size):
        for j in range(size):
            lt_one_constraint = connections[i, j] <= 1
            constraints.append(lt_one_constraint)

    problem = cvx.Problem(objective, constraints)
    problem.solve()

    real_connections = connections.value
    if probabilities:
        return real_connections
    
    adj_mat = np.zeros((size, size))
    inds = range(size)
    if randomize:
        shuffle(inds)
    for i in inds:
        connection = connectivity_vector[i]
        connection = max(0, int(connection - adj_mat[i, :].sum()))
        max_connection_inds = real_connections[i].argsort()[::-1]
        max_connection_inds = max_connection_inds[0, :connection]
        for j in max_connection_inds:
            adj_mat[i, j] = 1
    return adj_mat


class ContagionNetwork:
    def __init__(self, exposure_matrix, capital_ratios, defaults=[]):
        self.exposure_matrix = exposure_matrix
        self.capital_ratios = capital_ratios
        self.defaults = defaults

    def step(self):
        next_defaults = []
        for institution, exposures in enumerate(self.exposure_matrix):
            assets = exposures.sum()
            for default in self.defaults:
                capital = self.capital_ratios[institution] * assets
                if capital < exposures[default]:
                    next_defaults.append(institution)
                    break
        self.defaults += next_defaults

        
class DeterministicNetwork:
    
    def __init__(self, size, liabilities=None, recovery_rate=0.0):
        self.size = size
        self.liabilities = liabilities if liabilities is not None else np.zeros((size, size))
        self.recovery_rate = recovery_rate

    def reset_net(self):
        for i in range(self.size):
            for j in range(i + 1, self.size):
                self.liabilities[i, j] = max(self.liabilities[i, j] - self.liabilities[j, i], 0)
                self.liabilities[j, i] = max(self.liabilities[j, i] - self.liabilities[i, j], 0)

    def default(self, i):
        self.liabilities[i, i] = 0

    def recover(self, i):
        for j in range(self.size):
            if i != j:
                self.liabilities[j, j] += self.recovery_rate * self.liabilities[j, i]
                self.liabilities[j, i] = 0

    def step(self):
        for i in range(self.size):
            capital = self.liabilities[i, i]
            assets = self.liabilities[i, :].sum()
            liabilities = self.liabilities[:, i].sum()
            net = capital + assets - liabilities
            print(i, assets, liabilities, capital, net)
            if net < 0:
                self.default(i)
                self.recover(i)

    def show(self):
        fig = plt.figure()
        ax = fig.add_subplot(1,1,1)
        ax.set_aspect('equal')
        plt.imshow(self.liabilities, interpolation='nearest', cmap=plt.cm.hot)
        plt.colorbar()
        plt.show()