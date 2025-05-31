from OpenGL.GL import *   # OpenGL functions and constants
import numpy as np       # NumPy for array handling
import ctypes            # ctypes for pointer arithmetic in OpenGL calls

def create_textured_object(vertex_path, index_path):
    # Read vertex data from the specified file
    with open(vertex_path, "r") as f:
        vertex_lines = f.readlines()

    vertices = []
    for line in vertex_lines:
        # Skip empty lines or comment lines starting with '#'
        if line.strip() and not line.startswith("#"):
            line = line.strip()
            # Support both comma-separated and space-separated floats
            if "," in line:
                parts = list(map(float, line.split(",")))
            else:
                parts = list(map(float, line.split()))
            vertices.extend(parts)   # Append parsed floats to vertices list

    vertices = np.array(vertices, dtype=np.float32)  # Convert to NumPy float32 array

    # Read index data from specified file
    with open(index_path, "r") as f:
        index_lines = f.readlines()

    indices = []
    for line in index_lines:
        # Skip empty lines or comments
        if line.strip() and not line.startswith("#"):
            # Indices assumed to be comma-separated integers on each line
            parts = list(map(int, line.strip().split(",")))
            indices.extend(parts)

    indices = np.array(indices, dtype=np.uint32)  # Convert to NumPy uint32 array for element indices

    # Generate OpenGL Vertex Array Object (VAO), Vertex Buffer Object (VBO), and Element Buffer Object (EBO)
    VAO = glGenVertexArrays(1)
    VBO = glGenBuffers(1)
    EBO = glGenBuffers(1)

    glBindVertexArray(VAO)   # Bind VAO to record vertex attribute setup

    # Upload vertex data to GPU
    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Upload index data to GPU
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # Define vertex attributes:
    # Each vertex consists of 5 floats: 3 for position (x,y,z) and 2 for texture coordinates (u,v)
    stride = 5 * ctypes.sizeof(ctypes.c_float)  # Total size per vertex in bytes

    # Position attribute setup (location = 0): 3 floats starting at offset 0
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)   # Enable attribute 0

    # Texture coordinate attribute setup (location = 1): 2 floats starting at offset 3 floats
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)   # Enable attribute 1

    glBindVertexArray(0)   # Unbind VAO to prevent accidental changes

    # Return VAO, EBO, and the count of indices for use in rendering calls
    return VAO, EBO, len(indices)
