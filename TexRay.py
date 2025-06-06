import pygame
import math
import sys

# --- Grundkonfiguration ---
WIDTH, HEIGHT = 640, 480
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 120
TAN_HALF_FOV = math.tan(HALF_FOV)
MAX_DEPTH = 800
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * TAN_HALF_FOV)
PROJ_COEFF = 3 * DIST * 40
SCALE = WIDTH // NUM_RAYS
TILE = 64

# --- Map (1 = Wand, 0 = leer) ---
game_map = [
    [1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,1],
    [1,0,1,0,0,0,0,1],
    [1,0,0,0,1,0,0,1],
    [1,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1]
]
MAP_WIDTH = len(game_map[0])
MAP_HEIGHT = len(game_map)

# --- Spielerposition ---
player_x, player_y = 100, 100
player_angle = 0
player_speed = 3
BUFFER = 5

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# --- Texturen laden ---
TEXTURE_WIDTH = 64
TEXTURE_HEIGHT = 64

wall_texture = pygame.image.load("textures/wall1.png").convert()
wall_texture = pygame.transform.scale(wall_texture, (TEXTURE_WIDTH, TEXTURE_HEIGHT))

floor_texture = pygame.image.load("textures/floor.png").convert()
floor_texture = pygame.transform.scale(floor_texture, (TEXTURE_WIDTH, TEXTURE_HEIGHT))

sky_image = pygame.image.load("textures/sky.png").convert()
sky_width = sky_image.get_width()

# --- Hilfsfunktionen ---
def mapping(x, y):
    return int(x // TILE), int(y // TILE)

def is_wall(x, y):
    map_x, map_y = mapping(x, y)
    if 0 <= map_x < MAP_WIDTH and 0 <= map_y < MAP_HEIGHT:
        return game_map[map_y][map_x] == 1
    return True

def move_player(dx, dy):
    global player_x, player_y
    scale = 4
    next_x = player_x + dx
    next_y = player_y + dy
    if not is_wall(next_x + scale, player_y):
        player_x = next_x
    if not is_wall(player_x, next_y + scale):
        player_y = next_y

# --- Raycasting mit DDA und Texturen ---
def ray_casting(sc, px, py, pa):
    cur_angle = pa - HALF_FOV
    for ray in range(NUM_RAYS):
        sin_a = math.sin(cur_angle)
        cos_a = math.cos(cur_angle)

        # vertikal
        x_vert, dx = (math.floor(px / TILE) + 1) * TILE, 1
        if cos_a < 0:
            x_vert = math.floor(px / TILE) * TILE - 0.0001
            dx = -1
        depth_v = (x_vert - px) / cos_a
        y_vert = py + depth_v * sin_a

        for i in range(0, MAX_DEPTH, TILE):
            tile_x = int(x_vert / TILE + (dx < 0) - 1 * (dx < 0))
            tile_y = int(y_vert / TILE)
            if 0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT and game_map[tile_y][tile_x]:
                break
            x_vert += dx * TILE
            y_vert += dx * TILE * sin_a / cos_a

        depth_v = (x_vert - px) / cos_a
        offset_v = int(y_vert) % TILE

        # horizontal
        y_hor, dy = (math.floor(py / TILE) + 1) * TILE, 1
        if sin_a < 0:
            y_hor = math.floor(py / TILE) * TILE - 0.0001
            dy = -1
        depth_h = (y_hor - py) / sin_a
        x_hor = px + depth_h * cos_a

        for i in range(0, MAX_DEPTH, TILE):
            tile_x = int(x_hor / TILE)
            tile_y = int(y_hor / TILE + (dy < 0) - 1 * (dy < 0))
            if 0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT and game_map[tile_y][tile_x]:
                break
            y_hor += dy * TILE
            x_hor += dy * TILE * cos_a / sin_a

        depth_h = (y_hor - py) / sin_a
        offset_h = int(x_hor) % TILE

        if depth_v < depth_h:
            depth = depth_v
            offset = offset_v
            brightness = 1.0
        else:
            depth = depth_h
            offset = offset_h
            brightness = 0.7

        # Fish-eye-Korrektur
        depth *= math.cos(pa - cur_angle)

        # Projektion
        proj_height = PROJ_COEFF / (depth + 0.0001)
        proj_height = min(HEIGHT * 2, proj_height)

        texture_x = int(offset / TILE * TEXTURE_WIDTH)
        texture_x = max(0, min(TEXTURE_WIDTH - 1, texture_x))

        wall_column = wall_texture.subsurface(texture_x, 0, 1, TEXTURE_HEIGHT)
        wall_column = pygame.transform.scale(wall_column, (SCALE, int(proj_height)))

        wall_y = HEIGHT // 2 - int(proj_height) // 2

        if wall_y < 0:
            visible_height = min(HEIGHT, int(proj_height) + wall_y)
            wall_column = wall_column.subsurface((0, -wall_y, SCALE, visible_height))
            wall_y = 0

        light = max(30, min(255, int(255 * brightness / (1 + depth * depth * 0.0001))))
        wall_column.fill((light, light, light), special_flags=pygame.BLEND_MULT)

        sc.blit(wall_column, (ray * SCALE, wall_y))

        cur_angle += DELTA_ANGLE

# --- Floor Casting ---
def draw_floor(sc, px, py, pa):
    floor_y_start = HEIGHT // 2 + 1
    for y in range(floor_y_start, HEIGHT):
        p = y - HEIGHT / 2
        row_distance = (TILE * DIST) / p

        left_ray_angle = pa - HALF_FOV
        right_ray_angle = pa + HALF_FOV

        for ray in range(NUM_RAYS):
            ray_angle = left_ray_angle + (ray / NUM_RAYS) * (right_ray_angle - left_ray_angle)

            world_x = px + row_distance * math.cos(ray_angle)
            world_y = py + row_distance * math.sin(ray_angle)

            tex_x = int(world_x) % TEXTURE_WIDTH
            tex_y = int(world_y) % TEXTURE_HEIGHT

            color = floor_texture.get_at((tex_x, tex_y))

            for i in range(SCALE):
                sc.set_at((ray * SCALE + i, y), color)

# --- Minimap ---
def draw_minimap():
    mini_scale = 5
    for y, row in enumerate(game_map):
        for x, cell in enumerate(row):
            color = (200, 200, 200) if cell == 1 else (50, 50, 50)
            pygame.draw.rect(screen, color,
                (x * TILE // mini_scale, y * TILE // mini_scale, TILE // mini_scale, TILE // mini_scale))
    pygame.draw.circle(screen, (255, 0, 0),
        (int(player_x // mini_scale), int(player_y // mini_scale)), 3)

# --- Hauptloop ---
def game_loop():
    global player_angle
    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            player_angle -= 0.04
        if keys[pygame.K_RIGHT]:
            player_angle += 0.04

        dx = dy = 0
        if keys[pygame.K_w]:
            dx += player_speed * math.cos(player_angle)
            dy += player_speed * math.sin(player_angle)
        if keys[pygame.K_s]:
            dx -= player_speed * math.cos(player_angle)
            dy -= player_speed * math.sin(player_angle)

        move_player(dx, dy)

        # Himmel zeichnen
        sky_offset = int(-player_angle / (2 * math.pi) * sky_width) % sky_width
        screen.blit(sky_image, (0, 0), (sky_offset, 0, WIDTH, HEIGHT // 2))

        # Boden zeichnen
        draw_floor(screen, player_x, player_y, player_angle)

        # Wände zeichnen
        ray_casting(screen, player_x, player_y, player_angle)

        # Minimap
        draw_minimap()

        pygame.display.flip()
        clock.tick(60)

game_loop()