from OpenGL.GL import *      # Import OpenGL functions/constants
from PIL import Image       # Pillow for image loading and processing
import os                   # OS module for path operations

def load_texture(path):
    abs_path = os.path.abspath(path)   # Convert relative path to absolute path for reliability
    #print("Loading texture from:", abs_path)  # Optional debug print for texture path

    image = Image.open(abs_path).convert("RGBA")   # Open image file and convert to RGBA format
    image = image.transpose(Image.FLIP_TOP_BOTTOM)  # Flip image vertically to match OpenGL texture coordinate system
    img_data = image.tobytes()                      # Convert image data to raw bytes suitable for OpenGL

    texture = glGenTextures(1)           # Generate one new OpenGL texture ID
    glBindTexture(GL_TEXTURE_2D, texture)  # Bind the generated texture as a 2D texture

    # Set texture wrapping parameters to repeat the texture on S and T axes
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # Set texture filtering parameters for minification and magnification to linear interpolation
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # Upload the image data to the GPU as a 2D texture
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    glGenerateMipmap(GL_TEXTURE_2D)  # Generate mipmaps for the texture to improve rendering quality at smaller scales

    return texture   # Return the OpenGL texture ID for use in rendering
