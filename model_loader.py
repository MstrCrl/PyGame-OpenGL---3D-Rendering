from OpenGL.GL import *
import numpy as np
import ctypes

def create_textured_object(vertex_path, index_path):
    with open(vertex_path, "r") as f:
        vertex_lines = f.readlines()
    vertices = []
    for line in vertex_lines:
        if line.strip() and not line.startswith("#"):
            line = line.strip()
            if "," in line:  # for dragon format
                parts = list(map(float, line.split(",")))
            else:  # for wings format
                parts = list(map(float, line.split()))
            vertices.extend(parts)
    vertices = np.array(vertices, dtype=np.float32)

    with open(index_path, "r") as f:
        index_lines = f.readlines()
    indices = []
    for line in index_lines:
        if line.strip() and not line.startswith("#"):
            parts = list(map(int, line.strip().split(",")))
            indices.extend(parts)
    indices = np.array(indices, dtype=np.uint32)

    VAO = glGenVertexArrays(1)
    VBO = glGenBuffers(1)
    EBO = glGenBuffers(1)

    glBindVertexArray(VAO)

    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # vertex: 3 pos + 2 texcoords
    stride = 5 * ctypes.sizeof(ctypes.c_float)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)
    return VAO, EBO, len(indices)
