import pygame
from pygame.locals import *
from OpenGL.GL import *
import glm
import config
import cv2
import random
from model_loader import create_textured_object
from texture_loader import load_texture
from textured_shader import create_shader_program
from bg_loader import create_bg_shader_program, create_bg_quad, init_video_texture, update_video_texture


def main():
    pygame.init()
    pygame.mixer.init()

    display = (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    # Set custom window title and icon
    pygame.display.set_caption("Minecraft 3D Castle <3")
    icon_surface = pygame.image.load("source/image.png")
    pygame.display.set_icon(icon_surface)

    glEnable(GL_DEPTH_TEST)
    glClearColor(*config.BACKGROUND_COLOR)

    # Initialize background video capture and related GL objects
    cap = cv2.VideoCapture("source/bg5.mp4")
    video_texture = init_video_texture()
    bg_shader = create_bg_shader_program()
    bg_VAO, bg_VBO = create_bg_quad()

    # Load 3D model and shader program
    shader = create_shader_program()
    glUseProgram(shader)
    vao_castle, ebo_castle, count_castle = create_textured_object(
        "source\\castle_vertices.txt", "source\\castle_indices.txt")
    tex_castle = load_texture("source\\castle.jpg")

    glUniform1i(glGetUniformLocation(shader, "texture1"), 0)
    model_loc = glGetUniformLocation(shader, "model")
    view_loc = glGetUniformLocation(shader, "view")
    proj_loc = glGetUniformLocation(shader, "projection")
    proj = glm.perspective(glm.radians(100.0), display[0] / display[1], 0.1, 100.0)
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm.value_ptr(proj))

    clock = pygame.time.Clock()
    running = True

    # States
    auto_mode = True
    auto_mode_locked = True  # Lock inputs during first auto mode
    showing_video_only = True
    music_switched = False
    mouse_down = False

    position = glm.vec3(0, 1, 0)
    startup_time = pygame.time.get_ticks()

    view_index = 0
    auto_view_index = 0
    current_view = views[auto_view_index]

    # Camera and rotation variables
    rot_x = current_view["rot_x"]
    rot_y = current_view["rot_y"]
    camera_distance = current_view["zoom"]
    target_rot_x, target_rot_y = rot_x, rot_y
    target_camera_distance = camera_distance

    # Adjustable lerp speed for smooth camera movement
    lerp_speed = 0.1
    min_lerp_speed = 0.01
    max_lerp_speed = 1.0

    # Zoom limits and feedback setup
    zoom_min = 1.0
    zoom_max = 30.0
    zoom_feedback_cooldown = 500  # ms cooldown for beep/print
    last_zoom_feedback_time = 0

    # auto_switch_intervals length should be one less than views length
    auto_switch_intervals = [2500] * 3 + [1500] * 5 + [1125] * 11  # 19 intervals for 20 views
    last_auto_switch_time = pygame.time.get_ticks()

    # Load beep sound or fallback to None
    try:
        beep_sound = pygame.mixer.Sound("source/beep.wav")
    except Exception:
        beep_sound = None

    # Helper: update camera target based on selected view
    def set_view(view):
        nonlocal current_view, target_camera_distance, target_rot_x, target_rot_y
        current_view = view
        target_camera_distance = view["zoom"]
        target_rot_x = view["rot_x"]
        target_rot_y = view["rot_y"]

    while running:
        current_time = pygame.time.get_ticks()

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Ignore all inputs except QUIT during locked auto mode
            if auto_mode_locked:
                continue

            if event.type == pygame.KEYDOWN:
                # Toggle auto mode with 'm'
                if event.key == pygame.K_m:
                    auto_mode = not auto_mode
                    print(f"Auto mode toggled to: {'ON' if auto_mode else 'OFF'}")

                    if auto_mode:
                        # If first auto mode run, start from 0 (FAR FAR),
                        # else start from 1 (skip FAR FAR)
                        if auto_view_index == 0:
                            auto_view_index = 0
                        else:
                            auto_view_index = 1
                        set_view(views[auto_view_index])
                        last_auto_switch_time = current_time
                        auto_mode_locked = False  # allow manual inputs after toggle

                # Adjust lerp speed with '+' and '-'
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    lerp_speed = min(max_lerp_speed, lerp_speed + 0.05)
                    print(f"Lerp speed increased to {lerp_speed:.2f}")
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    lerp_speed = max(min_lerp_speed, lerp_speed - 0.05)
                    print(f"Lerp speed decreased to {lerp_speed:.2f}")

                if not auto_mode:
                    # Navigate with arrow keys or WASD
                    if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_w):
                        view_index = (view_index + 1) % len(manual_views)
                        set_view(manual_views[view_index])
                        print(f"Switched to: {current_view['name']}")

                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_s):
                        view_index = (view_index - 1) % len(manual_views)
                        set_view(manual_views[view_index])
                        print(f"Switched to: {current_view['name']}")

                    # Number keys 1-9 and 0 to jump directly to a view
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                       pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8,
                                       pygame.K_9, pygame.K_0):
                        idx = 9 if event.key == pygame.K_0 else event.key - pygame.K_1
                        if idx < len(manual_views):
                            view_index = idx
                            set_view(manual_views[view_index])
                            print(f"Jumped to view {view_index + 1}: {current_view['name']}")

                    # Random view on pressing 'r' or space
                    elif event.key == pygame.K_r or event.key == pygame.K_SPACE:
                        view_index = random.randint(0, len(manual_views) - 1)
                        set_view(manual_views[view_index])
                        print(f"Randomly switched to view {view_index + 1}: {current_view['name']}")

            # Mouse wheel zoom and drag rotation
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    if target_camera_distance > zoom_min:
                        target_camera_distance = max(zoom_min, target_camera_distance - 0.5)
                    else:
                        if current_time - last_zoom_feedback_time > zoom_feedback_cooldown:
                            print("Reached minimum zoom limit")
                            if beep_sound:
                                beep_sound.play()
                            last_zoom_feedback_time = current_time
                elif event.button == 5:
                    if target_camera_distance < zoom_max:
                        target_camera_distance = min(zoom_max, target_camera_distance + 0.5)
                    else:
                        if current_time - last_zoom_feedback_time > zoom_feedback_cooldown:
                            print("Reached maximum zoom limit")
                            if beep_sound:
                                beep_sound.play()
                            last_zoom_feedback_time = current_time
                elif event.button == 1:
                    mouse_down = True
                    last_mouse_pos = pygame.mouse.get_pos()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_down = False

            if event.type == pygame.MOUSEMOTION and mouse_down:
                x, y = pygame.mouse.get_pos()
                dx = x - last_mouse_pos[0]
                dy = y - last_mouse_pos[1]
                target_rot_y += dx * 0.5
                target_rot_x += dy * 0.5
                last_mouse_pos = (x, y)

        # Auto mode switching of views with safe bounds checking
        if auto_mode:
            if auto_view_index < len(auto_switch_intervals):
                elapsed = current_time - last_auto_switch_time
                interval = auto_switch_intervals[auto_view_index]
                if elapsed > interval:
                    auto_view_index += 1
                    if auto_view_index >= len(auto_switch_intervals):
                        auto_mode = False
                        auto_mode_locked = False  # Unlock manual controls now
                        view_index = 0
                        print("Auto mode ended, manual control enabled.")
                    else:
                        set_view(views[auto_view_index])
                        print(f"Auto-switched to: {current_view['name']}")
                    last_auto_switch_time = current_time

        # Render background video
        glClear(GL_COLOR_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        update_video_texture(cap, video_texture)
        glUseProgram(bg_shader)
        glBindVertexArray(bg_VAO)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, video_texture)
        bg_tex_loc = glGetUniformLocation(bg_shader, "backgroundTexture")
        glUniform1i(bg_tex_loc, 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        glBindVertexArray(0)
        glEnable(GL_DEPTH_TEST)
        glClear(GL_DEPTH_BUFFER_BIT)

        # Delay before switching to music & 3D scene
        if showing_video_only:
            if current_time - startup_time < 2000:
                pygame.display.flip()
                clock.tick(120)
                continue
            pygame.mixer.music.load("source/music.mp4")
            pygame.mixer.music.play()
            showing_video_only = False

        if not music_switched and not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("source/music1.mp3")
            pygame.mixer.music.play(-1, fade_ms=5000)
            music_switched = True

        # Smooth interpolation for camera and rotation using lerp_speed
        camera_distance += (target_camera_distance - camera_distance) * lerp_speed
        rot_x += (target_rot_x - rot_x) * lerp_speed
        rot_y += (target_rot_y - rot_y) * lerp_speed

        # Setup view matrix
        view = glm.lookAt(glm.vec3(0, camera_distance, 0), glm.vec3(0, 0, 0), glm.vec3(0, 0, -1))
        glUseProgram(shader)
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))

        # Model matrix with rotations and translations
        model1 = glm.mat4(1.0)
        model1 = glm.translate(model1, position)
        model1 = glm.rotate(model1, glm.radians(rot_x), glm.vec3(1, 0, 0))
        model1 = glm.rotate(model1, glm.radians(rot_y), glm.vec3(0, 1, 0))
        model1 = glm.translate(model1, position)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model1))

        # Bind texture and draw model
        glBindTexture(GL_TEXTURE_2D, tex_castle)
        glBindVertexArray(vao_castle)
        glDrawElements(GL_TRIANGLES, count_castle, GL_UNSIGNED_INT, None)

        pygame.display.flip()
        clock.tick(config.FPS)


# Views (FAR FAR is auto-only)
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
manual_views = views[1:]  # Skip "FAR FAR" in manual mode


if __name__ == "__main__":
    main()
