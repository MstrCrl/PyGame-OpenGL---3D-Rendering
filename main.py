import pygame
from pygame.locals import *
from OpenGL.GL import *
import glm
import config
import cv2
from model_loader import create_textured_object
from texture_loader import load_texture
from textured_shader import create_shader_program
from bg_loader import create_bg_shader_program, create_bg_quad, init_video_texture, update_video_texture

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
    {"name": "CASTLE TOP VIEW", "zoom": 10.5, "rot_x": -13.0, "rot_y": -449.0},
    {"name": "CASTLE MAIN VIEW", "zoom": 9.0, "rot_x": -45.0, "rot_y": -90.0},
]
manual_views = views[1:]  # Skip "FAR FAR" in manual mode

def main():
    pygame.init()
    pygame.mixer.init()

    display = (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    glEnable(GL_DEPTH_TEST)
    glClearColor(*config.BACKGROUND_COLOR)

    # Initialize background
    cap = cv2.VideoCapture("source/bg5.mp4")
    video_texture = init_video_texture()
    bg_shader = create_bg_shader_program()
    bg_VAO, bg_VBO = create_bg_quad()

    # Load model and shader
    shader = create_shader_program()
    glUseProgram(shader)
    vao_castle, ebo_castle, count_castle = create_textured_object("source\\castle_vertices.txt", "source\\castle_indices.txt")
    tex_castle = load_texture("source\\castle.jpg")
    glUniform1i(glGetUniformLocation(shader, "texture1"), 0)
    model_loc = glGetUniformLocation(shader, "model")
    view_loc = glGetUniformLocation(shader, "view")
    proj_loc = glGetUniformLocation(shader, "projection")
    proj = glm.perspective(glm.radians(100.0), display[0] / display[1], 0.1, 100.0)
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm.value_ptr(proj))

    clock = pygame.time.Clock()
    running = True
    auto_mode = True
    showing_video_only = True
    music_switched = False

    mouse_down = False 
    
    position = glm.vec3(0, 1, 0)
    startup_time = pygame.time.get_ticks()
    view_index = 0
    auto_view_index = 0
    current_view = views[auto_view_index]

    rot_x = current_view["rot_x"]
    rot_y = current_view["rot_y"]
    camera_distance = current_view["zoom"]
    target_rot_x, target_rot_y = rot_x, rot_y
    target_camera_distance = camera_distance

    auto_switch_intervals = [2500] * 3 + [1500] * 5 + [1125] * 11
    last_auto_switch_time = pygame.time.get_ticks()

    while running:
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                view_info = f"Zoom: {camera_distance:.2f}, rot_x: {rot_x:.2f}, rot_y: {rot_y:.2f}"
                print(view_info)
                with open("view_log.txt", "a") as log:
                    log.write(view_info + "\n")

            if not auto_mode:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        view_index = (view_index + 1) % len(manual_views)
                    elif event.key == pygame.K_LEFT:
                        view_index = (view_index - 1) % len(manual_views)
                    current_view = manual_views[view_index]
                    target_camera_distance = current_view["zoom"]
                    target_rot_x = current_view["rot_x"]
                    target_rot_y = current_view["rot_y"]
                    print(f"Switched to: {current_view['name']}")

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        target_camera_distance = max(1.0, target_camera_distance - 0.5)
                    elif event.button == 5:
                        target_camera_distance += 0.5
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

        # Auto switching
        if auto_mode and (current_time - last_auto_switch_time) > auto_switch_intervals[auto_view_index]:
            auto_view_index += 1
            if auto_view_index >= len(auto_switch_intervals):
                auto_mode = False
                view_index = 0
                print("Auto mode ended, manual control enabled.")
                continue
            current_view = views[auto_view_index]
            target_camera_distance = current_view["zoom"]
            target_rot_x = current_view["rot_x"]
            target_rot_y = current_view["rot_y"]
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

        # Delay before music & 3D
        if showing_video_only:
            if current_time - startup_time < 2000:
                pygame.display.flip()
                clock.tick(120)
                continue
            else:
                pygame.mixer.music.load("source/music.mp4")
                pygame.mixer.music.play()
                showing_video_only = False

        if not music_switched and not pygame.mixer.music.get_busy():
            pygame.mixer.music.load("source/music1.mp3")
            pygame.mixer.music.play(-1, fade_ms=5000)
            music_switched = True

        # Smooth transition
        lerp_speed = 0.1
        camera_distance += (target_camera_distance - camera_distance) * lerp_speed
        rot_x += (target_rot_x - rot_x) * lerp_speed
        rot_y += (target_rot_y - rot_y) * lerp_speed

        # Render 3D scene
        view = glm.lookAt(glm.vec3(0, camera_distance, 0), glm.vec3(0, 0, 0), glm.vec3(0, 0, -1))
        glUseProgram(shader)
        glUniformMatrix4fv(view_loc, 1, GL_FALSE, glm.value_ptr(view))

        model1 = glm.mat4(1.0)
        model1 = glm.translate(model1, position)
        model1 = glm.rotate(model1, glm.radians(rot_x), glm.vec3(1, 0, 0))
        model1 = glm.rotate(model1, glm.radians(rot_y), glm.vec3(0, 1, 0))
        model1 = glm.translate(model1, position)
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, glm.value_ptr(model1))

        glBindTexture(GL_TEXTURE_2D, tex_castle)
        glBindVertexArray(vao_castle)
        glDrawElements(GL_TRIANGLES, count_castle, GL_UNSIGNED_INT, None)

        pygame.display.flip()
        clock.tick(config.FPS)

    cap.release()
    glDeleteVertexArrays(1, [vao_castle, bg_VAO])
    glDeleteBuffers(1, [ebo_castle, bg_VBO])
    glDeleteTextures(1, [tex_castle, video_texture])
    glDeleteProgram(shader)
    glDeleteProgram(bg_shader)
    pygame.mixer.music.stop()
    pygame.quit()

if __name__ == "__main__":
    main()
