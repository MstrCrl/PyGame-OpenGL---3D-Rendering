import pygame
from pygame.locals import *          # Pygame constants like QUIT, KEYDOWN, etc.
from OpenGL.GL import *              # OpenGL functions
import glm                           # OpenGL Mathematics library for matrix/vector math
import config                        # Your config module for constants like window size, colors, FPS
import cv2                           # OpenCV for video capture
import random                        # For random view switching
from loader.model_loader import create_textured_object    # Load model data for OpenGL
from loader.texture_loader import load_texture            # Load textures for OpenGL
from loader.textured_shader import create_shader_program  # Create OpenGL shader program for textured objects
from loader.bg_loader import create_bg_shader_program, create_bg_quad, init_video_texture, update_video_texture # Utilities for background video rendering using OpenGL


def main():
    pygame.init()            # Initialize Pygame modules (video, events)
    pygame.mixer.init()      # Initialize Pygame sound mixer for audio playback

    display = (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)  # Get display size from config
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)     # Create OpenGL-capable window with double buffering

    # Set window title and icon
    pygame.display.set_caption("Minecraft 3D Castle <3")
    icon_surface = pygame.image.load("source/image.png")     # Load image for window icon
    pygame.display.set_icon(icon_surface)

    glEnable(GL_DEPTH_TEST)                  # Enable depth testing so nearer objects occlude farther ones
    glClearColor(*config.BACKGROUND_COLOR)   # Set the clear color for the background (RGBA)

    # Setup video capture for background video with OpenCV
    cap = cv2.VideoCapture("source/bg5.mp4")

    video_texture = init_video_texture()            # Create OpenGL texture for video frames
    bg_shader = create_bg_shader_program()          # Create shader program for rendering video background quad
    bg_VAO, bg_VBO = create_bg_quad()               # Create vertex array and buffer for fullscreen quad to render video

    # Load 3D model and create shader program for it
    shader = create_shader_program()
    glUseProgram(shader)                             # Use this shader program for subsequent drawing calls

    # Create the textured castle model from vertices and indices files
    vao_castle, ebo_castle, count_castle = create_textured_object(
        "source\\castle_vertices.txt", "source\\castle_indices.txt")

    tex_castle = load_texture("source\\castle.jpg") # Load castle texture image into OpenGL texture object

    # Set uniform sampler to use texture unit 0 for the shader
    glUniform1i(glGetUniformLocation(shader, "texture1"), 0)

    # Cache uniform locations for model, view, and projection matrices
    model_loc = glGetUniformLocation(shader, "model")
    view_loc = glGetUniformLocation(shader, "view")
    proj_loc = glGetUniformLocation(shader, "projection")

    # Create a perspective projection matrix with 100 degree FOV, aspect ratio from display,
    # near plane 0.1 and far plane 100 units, and pass it to the shader
    proj = glm.perspective(glm.radians(100.0), display[0] / display[1], 0.1, 100.0)
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm.value_ptr(proj))

    clock = pygame.time.Clock()      # For controlling frame rate
    running = True                   # Main loop control flag

    # Initial states and flags
    auto_mode = True                # Automatically cycle through predefined views
    auto_mode_locked = True         # Lock user input during initial auto mode
    showing_video_only = True       # Start by showing only the video background
    music_switched = False          # Track if music switched to looping track
    mouse_down = False              # Track if left mouse button is pressed

    position = glm.vec3(0, 1, 0)   # Initial 3D position of the castle model
    startup_time = pygame.time.get_ticks()   # Time when program started (milliseconds)

    view_index = 0                 # Index for manual views navigation
    auto_view_index = 0            # Index for auto mode views navigation
    current_view = views[auto_view_index]   # Current active camera view parameters

    # Initialize camera rotation and zoom from current view
    rot_x = current_view["rot_x"]
    rot_y = current_view["rot_y"]
    camera_distance = current_view["zoom"]

    # Target values for smooth interpolation
    target_rot_x, target_rot_y = rot_x, rot_y
    target_camera_distance = camera_distance

    # Interpolation (lerp) speed controls smooth camera motion
    lerp_speed = 0.1
    min_lerp_speed = 0.01
    max_lerp_speed = 1.0

    # Zoom limits for camera distance and cooldown for feedback beep when limit reached
    zoom_min = 1.0
    zoom_max = 30.0
    zoom_feedback_cooldown = 500  # milliseconds
    last_zoom_feedback_time = 0

    # Durations between automatic camera view switches in milliseconds
    # Should be one less than number of views because switching happens between views
    auto_switch_intervals = [2500] * 3 + [1500] * 5 + [1125] * 11  # total 19 intervals for 20 views
    last_auto_switch_time = pygame.time.get_ticks()                # Last time auto switch happened

    # Try to load beep sound for feedback, fallback to None if unavailable
    try:
        beep_sound = pygame.mixer.Sound("source/beep.wav")
    except Exception:
        beep_sound = None

    # Helper function to set the camera target parameters from a view dictionary
    def set_view(view):
        nonlocal current_view, target_camera_distance, target_rot_x, target_rot_y
        current_view = view
        target_camera_distance = view["zoom"]
        target_rot_x = view["rot_x"]
        target_rot_y = view["rot_y"]

    # Main application loop
    while running:
        current_time = pygame.time.get_ticks()  # Get current time in milliseconds

        # Process all events (input, window events)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Window close event
                running = False

            # If inputs are locked (during initial auto mode), ignore all except quit
            if auto_mode_locked:
                continue

            if event.type == pygame.KEYDOWN:
                # Toggle auto mode on/off with 'm' key
                if event.key == pygame.K_m:
                    auto_mode = not auto_mode
                    print(f"Auto mode toggled to: {'ON' if auto_mode else 'OFF'}")

                    if auto_mode:
                        # On first auto mode start, start from FAR FAR (index 0)
                        # Else start from second view to skip FAR FAR (index 1)
                        if auto_view_index == 0:
                            auto_view_index = 0
                        else:
                            auto_view_index = 1
                        set_view(views[auto_view_index])
                        last_auto_switch_time = current_time
                        auto_mode_locked = False  # Unlock manual input now

                # Increase lerp speed with '+' keys
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    lerp_speed = min(max_lerp_speed, lerp_speed + 0.05)
                    print(f"Lerp speed increased to {lerp_speed:.2f}")
                # Decrease lerp speed with '-' keys
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    lerp_speed = max(min_lerp_speed, lerp_speed - 0.05)
                    print(f"Lerp speed decreased to {lerp_speed:.2f}")

                # Manual mode controls (when auto_mode is off)
                if not auto_mode:
                    # Cycle views forward on Right Arrow, D, or W keys
                    if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_w):
                        view_index = (view_index + 1) % len(manual_views)
                        set_view(manual_views[view_index])
                        print(f"Switched to: {current_view['name']}")

                    # Cycle views backward on Left Arrow, A, or S keys
                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_s):
                        view_index = (view_index - 1) % len(manual_views)
                        set_view(manual_views[view_index])
                        print(f"Switched to: {current_view['name']}")

                    # Jump directly to a view with number keys 1-9 and 0 (0 maps to 10th view)
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                       pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
                                       pygame.K_9, pygame.K_0):
                        idx = 9 if event.key == pygame.K_0 else event.key - pygame.K_1
                        if idx < len(manual_views):
                            view_index = idx
                            set_view(manual_views[view_index])
                            print(f"Jumped to view {view_index + 1}: {current_view['name']}")

                    # Random view on pressing 'r' or spacebar
                    elif event.key == pygame.K_r or event.key == pygame.K_SPACE:
                        view_index = random.randint(0, len(manual_views) - 1)
                        set_view(manual_views[view_index])
                        print(f"Randomly switched to view {view_index + 1}: {current_view['name']}")

            # Mouse wheel zoom and left-button drag for rotation
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Mouse wheel up
                    if target_camera_distance > zoom_min:
                        target_camera_distance = max(zoom_min, target_camera_distance - 0.5)
                    else:
                        # Play beep and print if zoom limit reached and cooldown passed
                        if current_time - last_zoom_feedback_time > zoom_feedback_cooldown:
                            print("Reached minimum zoom limit")
                            if beep_sound:
                                beep_sound.play()
                            last_zoom_feedback_time = current_time
                elif event.button == 5:  # Mouse wheel down
                    if target_camera_distance < zoom_max:
                        target_camera_distance = min(zoom_max, target_camera_distance + 0.5)
                    else:
                        if current_time - last_zoom_feedback_time > zoom_feedback_cooldown:
                            print("Reached maximum zoom limit")
                            if beep_sound:
                                beep_sound.play()
                            last_zoom_feedback_time = current_time
                elif event.button == 1:  # Left mouse button pressed
                    mouse_down = True
                    last_mouse_pos = pygame.mouse.get_pos()  # Save current mouse position

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_down = False  # Left mouse button released

            if event.type == pygame.MOUSEMOTION and mouse_down:
                x, y = pygame.mouse.get_pos()
                dx = x - last_mouse_pos[0]  # Mouse movement delta X
                dy = y - last_mouse_pos[1]  # Mouse movement delta Y
                target_rot_y += dx * 0.5    # Update target rotation around Y-axis (horizontal)
                target_rot_x += dy * 0.5    # Update target rotation around X-axis (vertical)
                last_mouse_pos = (x, y)     # Update last mouse position

        # Auto mode: switch views automatically after intervals
        if auto_mode:
            if auto_view_index < len(auto_switch_intervals):
                elapsed = current_time - last_auto_switch_time
                interval = auto_switch_intervals[auto_view_index]
                if elapsed > interval:
                    auto_view_index += 1
                    # If no more intervals, end auto mode and enable manual control
                    if auto_view_index >= len(auto_switch_intervals):
                        auto_mode = False
                        auto_mode_locked = False
                        view_index = 0
                        print("Auto mode ended, manual control enabled.")
                    else:
                        # Switch to next view
                        set_view(views[auto_view_index])
                        print(f"Auto-switched to: {current_view['name']}")
                    last_auto_switch_time = current_time

        # Render the video background
        glClear(GL_COLOR_BUFFER_BIT)     # Clear color buffer (don't clear depth yet)
        glDisable(GL_DEPTH_TEST)         # Disable depth test so quad draws over everything

        update_video_texture(cap, video_texture)  # Update the OpenGL video texture with latest video frame

        glUseProgram(bg_shader)          # Use background shader program
        glBindVertexArray(bg_VAO)        # Bind quad VAO
        glActiveTexture(GL_TEXTURE0)     # Activate texture unit 0
        glBindTexture(GL_TEXTURE_2D, video_texture)  # Bind video texture to unit 0
        bg_tex_loc = glGetUniformLocation(bg_shader, "backgroundTexture")  # Get uniform location
        glUniform1i(bg_tex_loc, 0)       # Set uniform sampler to texture unit 0
        glDrawArrays(GL_TRIANGLES, 0, 6)  # Draw two triangles forming the quad
        glBindVertexArray(0)             # Unbind VAO

        glEnable(GL_DEPTH_TEST)          # Enable depth testing again for 3D scene
        glClear(GL_DEPTH_BUFFER_BIT)     # Clear depth buffer for new frame

        # Initially only show video background, delay before switching to music & 3D model
        if showing_video_only:
            if current_time - startup_time < 2000:  # Show video only for 2 seconds
                pygame.display.flip()
                clock.tick(120)            # Limit to 120 FPS while waiting
                continue
            # After delay, load and play music.mp4 audio track once
            pygame.mixer.music.load("source/music.mp4")
            pygame.mixer.music.play()
            showing_video_only = False    # Switch to 3D rendering next frames

        # If initial music finished, switch to looping music1.mp3 with fade in
        if not music_switched and not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("source/music1.mp3")
            pygame.mixer.music.play(-1, fade_ms=5000)  # Loop indefinitely with 5s fade-in
            music_switched = True

        # Smoothly interpolate current camera distance and rotations toward targets using lerp
        camera_distance += (target_camera_distance - camera_distance) * lerp_speed
        rot_x += (target_rot_x - rot_x) * lerp_speed
        rot_y += (target_rot_y - rot_y) * lerp_speed

        # Setup view matrix with camera position looking at origin
        view = glm.lookAt(glm.vec3(0, camera_distance, 0),  # Camera position along Y axis
                          glm.vec3(0, 0, 0),                # Look at origin (castle)
                          glm.vec3(0, 0, -1))               # Up vector pointing backward on Z axis
        glUseProgram(shader)
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))

        # Model matrix for castle including translation and rotations
        model1 = glm.mat4(1.0)                       # Identity matrix
        model1 = glm.translate(model1, position)    # Translate to position vector (0,1,0)
        model1 = glm.rotate(model1, glm.radians(rot_x), glm.vec3(1, 0, 0))  # Rotate around X axis
        model1 = glm.rotate(model1, glm.radians(rot_y), glm.vec3(0, 1, 0))  # Rotate around Y axis
        model1 = glm.translate(model1, position)    # Translate again by position? (may be redundant)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model1))   # Pass model matrix to shader

        # Bind the castle texture and VAO, then draw the elements
        glBindTexture(GL_TEXTURE_2D, tex_castle)
        glBindVertexArray(vao_castle)
        glDrawElements(GL_TRIANGLES, count_castle, GL_UNSIGNED_INT, None)

        pygame.display.flip()           # Swap buffers to display rendered frame
        clock.tick(config.FPS)          # Limit to configured FPS

    # Cleanup resources on exit
    cap.release()
    glDeleteVertexArrays(1, [vao_castle, bg_VAO])
    glDeleteBuffers(1, [ebo_castle, bg_VBO])
    glDeleteTextures(1, [tex_castle, video_texture])
    glDeleteProgram(shader)
    glDeleteProgram(bg_shader)
    pygame.mixer.music.stop()
    pygame.quit()

# List of predefined camera views with name, zoom level, and rotation angles (degrees)
# The first view "FAR FAR" is auto-only, skipped in manual mode
views = [
    {"name": "FAR FAR", "zoom": 107.5, "rot_x": -13.0, "rot_y": -449.0},  # AUTO ONLY
    {"name": "CASTLE TOP VIEW", "zoom": 10.5, "rot_x": -13.0, "rot_y": -449.0},
    {"name": "CASTLE MAIN VIEW", "zoom": 9.0, "rot_x": -45.0, "rot_y": -90.0},
    {"name": "OUTER GATE", "zoom": 8.0, "rot_x": -51.0, "rot_y": -90.0},
    {"name": "VENDORS UNDER BRIDGE", "zoom": 6.5, "rot_x": -36.0, "rot_y": -66.5},
    {"name": "MARKET PLACE", "zoom": 6.0, "rot_x": -50.5, "rot_y": -56.0},
    {"name": "TAVERN", "zoom": 7.0, "rot_x": -49.5, "rot_y": -48.5},
    {"name": "BLACKSMITH", "zoom": 5.5, "rot_x": -54.5, "rot_y": -24.0},
    {"name": "PEASANT HUT", "zoom": 6.5, "rot_x": -52.5, "rot_y": 7.5},
    {"name": "FARM", "zoom": 7.0, "rot_x": -52.5, "rot_y": 26.5},
    {"name": "WINDMILL", "zoom": 8.0, "rot_x": -50.5, "rot_y": 18.5},
    {"name": "UPPER CLASS RESIDENTIAL", "zoom": 7.0, "rot_x": -49.5, "rot_y": -138.5},
    {"name": "POND", "zoom": 7.0, "rot_x": -62.5, "rot_y": -142.5},
    {"name": "CHAPPEL", "zoom": 7.5, "rot_x": -49.5, "rot_y": -218.5},
    {"name": "OUTER OUTPOST", "zoom": 8.5, "rot_x": -58.0, "rot_y": -217.5},
    {"name": "INNER GATE", "zoom": 5.5, "rot_x": -30.5, "rot_y": -89.0},
    {"name": "INNER OUTPOST", "zoom": 7.0, "rot_x": -24.5, "rot_y": -153.0},
    {"name": "CASTLE MAIN VIEW", "zoom": 9.0, "rot_x": -45.0, "rot_y": -90.0},
    {"name": "CASTLE TOP VIEW", "zoom": 10.5, "rot_x": -13.0, "rot_y": -449.0},
]

manual_views = views[1:]  # Exclude the first "FAR FAR" view from manual mode navigation


if __name__ == "__main__":
    main()
