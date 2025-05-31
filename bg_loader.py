import cv2                  # OpenCV for video capture and frame processing
import numpy as np          # NumPy for array handling
from OpenGL.GL import *     # OpenGL functions/constants
import ctypes               # For pointer arithmetic in OpenGL buffer setup

# Vertex shader for rendering a textured fullscreen quad (background video)
bg_vertex_shader = """
#version 330 core
layout(location = 0) in vec2 position;    // Vertex position attribute (x, y)
layout(location = 1) in vec2 texCoord;    // Texture coordinate attribute (u, v)
out vec2 TexCoord;                        // Pass texture coords to fragment shader
void main() {
    gl_Position = vec4(position, 0.0, 1.0);  // Set vertex position in clip space
    TexCoord = texCoord;                      // Pass through texture coordinate
}
"""

# Fragment shader to sample from the background texture and output the color
bg_fragment_shader = """
#version 330 core
in vec2 TexCoord;                         // Texture coordinate from vertex shader
out vec4 FragColor;                       // Output fragment color
uniform sampler2D backgroundTexture;     // Background texture sampler
void main() {
    FragColor = texture(backgroundTexture, TexCoord);  // Sample texture at TexCoord
}
"""

def create_bg_shader_program():
    vs = glCreateShader(GL_VERTEX_SHADER)     # Create vertex shader object
    fs = glCreateShader(GL_FRAGMENT_SHADER)   # Create fragment shader object
    glShaderSource(vs, bg_vertex_shader)      # Attach vertex shader source code
    glShaderSource(fs, bg_fragment_shader)    # Attach fragment shader source code
    glCompileShader(vs)                        # Compile vertex shader
    glCompileShader(fs)                        # Compile fragment shader

    program = glCreateProgram()                # Create shader program
    glAttachShader(program, vs)                # Attach vertex shader to program
    glAttachShader(program, fs)                # Attach fragment shader to program
    glLinkProgram(program)                     # Link program (create executable)
    glDeleteShader(vs)                         # Delete vertex shader object (no longer needed)
    glDeleteShader(fs)                         # Delete fragment shader object (no longer needed)
    return program                             # Return the linked shader program ID

def create_bg_quad():
    # Define vertices for two triangles forming a fullscreen quad
    # Each vertex has 2D position followed by 2D texture coordinates
    quad_vertices = np.array([
        # positions   # texCoords
        -1.0,  1.0,   0.0, 1.0,  # Top-left
        -1.0, -1.0,   0.0, 0.0,  # Bottom-left
         1.0, -1.0,   1.0, 0.0,  # Bottom-right
        -1.0,  1.0,   0.0, 1.0,  # Top-left (again)
         1.0, -1.0,   1.0, 0.0,  # Bottom-right (again)
         1.0,  1.0,   1.0, 1.0,  # Top-right
    ], dtype=np.float32)

    VAO = glGenVertexArrays(1)    # Generate vertex array object
    VBO = glGenBuffers(1)         # Generate vertex buffer object

    glBindVertexArray(VAO)        # Bind VAO to record vertex attribute configuration
    glBindBuffer(GL_ARRAY_BUFFER, VBO)    # Bind VBO as the current array buffer
    glBufferData(GL_ARRAY_BUFFER, quad_vertices.nbytes, quad_vertices, GL_STATIC_DRAW)  # Upload vertex data

    # Enable vertex attribute 0 for position (2 floats)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * quad_vertices.itemsize, ctypes.c_void_p(0))

    # Enable vertex attribute 1 for texture coordinate (2 floats)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * quad_vertices.itemsize, ctypes.c_void_p(2 * quad_vertices.itemsize))

    glBindVertexArray(0)          # Unbind VAO to avoid accidental modifications
    return VAO, VBO              # Return VAO and VBO handles for use in rendering

def init_video_texture():
    tex_id = glGenTextures(1)            # Generate a texture ID
    glBindTexture(GL_TEXTURE_2D, tex_id) # Bind the texture as 2D texture

    # Set texture filtering parameters to linear for smooth scaling
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glBindTexture(GL_TEXTURE_2D, 0)      # Unbind texture to prevent accidental modification
    return tex_id                        # Return texture ID for use in uploading frames

def update_video_texture(cap, texture_id):
    ret, frame = cap.read()              # Read next frame from video capture
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # If at end, reset to first frame to loop video
        ret, frame = cap.read()
    # Convert BGR (OpenCV default) to RGB for OpenGL
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.flip(frame, 0)           # Flip vertically to match OpenGL texture coords

    height, width, _ = frame.shape       # Get frame dimensions

    glBindTexture(GL_TEXTURE_2D, texture_id)   # Bind video texture
    # Upload the frame as a texture image
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height,
                 0, GL_RGB, GL_UNSIGNED_BYTE, frame)
    glBindTexture(GL_TEXTURE_2D, 0)      # Unbind texture after updating
