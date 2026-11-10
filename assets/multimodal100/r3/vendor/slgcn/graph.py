import numpy as np


def edge2mat(link, num_node):
    A = np.zeros((num_node, num_node))
    for i, j in link:
        A[j, i] = 1
    return A


def normalize_digraph(A):
    Dl = np.sum(A, 0)
    h, w = A.shape
    Dn = np.zeros((w, w))
    for i in range(w):
        if Dl[i] > 0:
            Dn[i, i] = Dl[i] ** (-1)
    AD = np.dot(A, Dn)
    return AD


def get_spatial_graph(num_node, self_link, inward, outward):
    I = edge2mat(self_link, num_node)
    In = normalize_digraph(edge2mat(inward, num_node))
    Out = normalize_digraph(edge2mat(outward, num_node))
    A = np.stack((I, In, Out))
    return A


class Graph:
    def __init__(self, num_node: int, labeling_mode="spatial"):
        inward_ori_index = [
            (5, 6),
            (5, 7),
            (6, 8),
            (8, 10),
            (7, 9),
            (9, 11),
            (12, 13),
            (12, 14),
            (12, 16),
            (12, 18),
            (12, 20),
            (14, 15),
            (16, 17),
            (18, 19),
            (20, 21),
            (22, 23),
            (22, 24),
            (22, 26),
            (22, 28),
            (22, 30),
            (24, 25),
            (26, 27),
            (28, 29),
            (30, 31),
            (10, 12),
            (11, 22),
        ]

        self.num_node = num_node
        self.self_link = [(i, i) for i in range(num_node)]
        self.inward = [(i - 5, j - 5) for (i, j) in inward_ori_index]
        self.outward = [(j, i) for (i, j) in self.inward]
        self.neighbor = self.inward + self.outward
        self.A = self.get_adjacency_matrix(labeling_mode)

    def get_adjacency_matrix(self, labeling_mode=None):
        if labeling_mode is None:
            return self.A
        if labeling_mode == "spatial":
            A = get_spatial_graph(
                self.num_node, self.self_link, self.inward, self.outward
            )
        else:
            raise ValueError()
        return A
