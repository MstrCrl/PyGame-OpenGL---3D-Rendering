from OpenGL.GL import *   # Import all OpenGL functions and constants

# Vertex shader source code (GLSL)
vertex_shader_src = """#version 330 core
layout (location = 0) in vec3 aPos;       // Vertex position attribute (x, y, z)
layout (location = 1) in vec2 aTexCoord;  // Vertex texture coordinate attribute (u, v)

uniform mat4 model;       // Model transformation matrix
uniform mat4 view;        // View (camera) transformation matrix
uniform mat4 projection;  // Projection matrix (perspective or orthographic)

out vec2 TexCoord;       // Output texture coordinate to fragment shader

void main()
{
    // Compute final vertex position in clip space by applying model, view, projection transforms
    gl_Position = projection * view * model * vec4(aPos, 1.0);
    TexCoord = aTexCoord;  // Pass texture coordinate through to fragment shader
}
"""

# Fragment shader source code (GLSL)
fragment_shader_src = """#version 330 core
out vec4 FragColor;      // Output fragment color
in vec2 TexCoord;        // Interpolated texture coordinate from vertex shader

uniform sampler2D texture1;  // Texture sampler uniform

void main()
{
    // Sample the texture at TexCoord and set as the output color
    FragColor = texture(texture1, TexCoord);
}
"""

def compile_shader(shader_type, source):
    shader = glCreateShader(shader_type)    # Create a shader object of given type
    glShaderSource(shader, source)           # Attach GLSL source code to shader object
    glCompileShader(shader)                   # Compile the shader

    # Check for compilation errors
    if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
        # If compile failed, raise error with shader info log message
        raise RuntimeError(glGetShaderInfoLog(shader).decode())

    return shader    # Return compiled shader object ID

def create_shader_program():
    # Compile vertex and fragment shaders
    vertex_shader = compile_shader(GL_VERTEX_SHADER, vertex_shader_src)
    fragment_shader = compile_shader(GL_FRAGMENT_SHADER, fragment_shader_src)

    program = glCreateProgram()      # Create a new shader program object
    glAttachShader(program, vertex_shader)    # Attach compiled vertex shader
    glAttachShader(program, fragment_shader)  # Attach compiled fragment shader
    glLinkProgram(program)           # Link program (combine shaders)

    # Check for linking errors
    if glGetProgramiv(program, GL_LINK_STATUS) != GL_TRUE:
        # If linking failed, raise error with program info log message
        raise RuntimeError(glGetProgramInfoLog(program).decode())

    # Once linked, shaders can be deleted as they are no longer needed separately
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return program   # Return linked shader program ID for use in rendering
