import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join

pygame.init()
pygame.mixer.init()

pygame.mixer.music.load("Sounds/BGmusic.mp3")
pygame.mixer.music.play(-1)
pygame.mixer.music.set_volume(0.5)

pygame.display.set_caption("Platformer")
WIDTH, HEIGHT = 1000, 500
FPS = 60
PLAYER_VEL = 3.5

jump_sound = pygame.mixer.Sound("Sounds/jump/jump.mp3")
hit_sound = pygame.mixer.Sound("Sounds/Hit/firehit.wav")
death_sound = pygame.mixer.Sound("Sounds/Hit/death.wav")

window = pygame.display.set_mode((WIDTH, HEIGHT))


def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size):
    path = join("assets", "terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    SPRITES = load_sprite_sheets("characters", "PinkMan", 32, 32, True)
    ANIMATION_DELAY = 5

    def __init__(self, x, y, width, height):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.max_health = 100
        self.health = 100
        self.riding_platform = None

    def jump(self):
        self.y_vel = -self.GRAVITY * 8
        self.jump_count += 1
        self.animation_count = 0
        if self.jump_count == 1:
            self.fall_count = 0

        self.riding_platform = None
        jump_sound.play()

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def make_hit(self):
        self.hit = True
        self.hit_count = 0

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    def loop(self, fps):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"

        elif self.y_vel != 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction

        sprites = self.SPRITES[sprite_sheet_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()

    def update(self):
        if self.sprite:
            self.rect = self.sprite.get_rect(
                topleft=(self.rect.x, self.rect.y))
            self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class MovingPlatform(Object):
    def __init__(self, x, y, size, move_distance, axis="x", speed=2):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)
        self.name = "moving_platform"

        self.start_x = x
        self.start_y = y
        self.move_distance = move_distance
        self.axis = axis
        self.speed = speed
        self.direction = 1

    def loop(self):
        if self.axis == "x":
            self.rect.x += self.speed * self.direction
            if abs(self.rect.x - self.start_x) >= self.move_distance:
                self.direction *= -1
        elif self.axis == "y":
            self.rect.y += self.speed * self.direction
            if abs(self.rect.y - self.start_y) >= self.move_distance:
                self.direction *= -1


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]

        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(
            topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


# ➡️ FIXED GENERATION ALGORITHM
def generate_infinite_level(start_grid_x, end_grid_x, block_size):
    generated_objects = []
    current_x = start_grid_x

    while current_x < end_grid_x:
        feature_type = random.choice(
            ["floating_island", "staircase", "fire_gap"])

        if feature_type == "floating_island":
            # ➡️ PASSING EXPLICIT VALUE ARRAY SO IT NEVER FREEZES
            height_multiplier = random.choice([2, 3])
            island_length = random.randint(1, 3)

            for i in range(island_length):
                generated_objects.append(
                    Block(block_size * (current_x + i), HEIGHT -
                          block_size * height_multiplier, block_size)
                )
            current_x += island_length + 2

        elif feature_type == "staircase":
            generated_objects.append(
                Block(block_size * current_x, HEIGHT - block_size * 2, block_size))
            generated_objects.append(
                Block(block_size * (current_x + 1), HEIGHT - block_size * 3, block_size))
            current_x += 4

        elif feature_type == "fire_gap":
            trap = Fire(block_size * current_x + 32,
                        HEIGHT - block_size - 64, 16, 32)
            trap.on()
            generated_objects.append(trap)
            current_x += 3

    return generated_objects


def get_background(name):
    image = pygame.image.load(join("assets", "background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image


def draw_health_bar(window, player, x, y, width, height):
    health_ratio = player.health / player.max_health
    pygame.draw.rect(window, (50, 50, 50), (x, y, width, height))
    if health_ratio > 0.5:
        bar_color = (0, 255, 0)
    elif health_ratio > 0.25:
        bar_color = (255, 165, 0)
    else:
        bar_color = (255, 0, 0)
    pygame.draw.rect(window, bar_color, (x + 2, y + 2,
                     int((width - 4) * health_ratio), height - 4))


def draw_game_over_card(window):
    card_rect = pygame.Rect(300, 150, 400, 200)
    pygame.draw.rect(window, (30, 30, 30), card_rect, border_radius=12)
    pygame.draw.rect(window, (255, 65, 65), card_rect,
                     width=3, border_radius=12)

    pygame.font.init()
    title_font = pygame.font.SysFont("Impact", 40, bold=True)
    sub_font = pygame.font.SysFont("Georgia", 20)

    title_surface = title_font.render("GAME OVER", True, (255, 255, 255))
    sub_surface = sub_font.render(
        "Press SPACE to Respawn", True, (200, 200, 200))
    window.blit(title_surface, (WIDTH // 2 -
                title_surface.get_width() // 2, 180))
    window.blit(sub_surface, (WIDTH // 2 - sub_surface.get_width() // 2, 260))
    pygame.display.update()


def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)
    draw_health_bar(window, player, 20, 20, 200, 25)
    pygame.display.update()


def handle_vertical_collision(player, objects, dy):
    collied_objects = []
    if dy > 0:
        player.riding_platform = None

    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
                if getattr(obj, "name", "") == "moving_platform":
                    player.riding_platform = obj
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()
            collied_objects.append(obj)

    return collied_objects


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object


def handle_move(player, objects):
    if player.riding_platform and player.riding_platform.axis == "x":
        platform_displacement = player.riding_platform.speed * \
            player.riding_platform.direction
        if not collide(player, objects, platform_displacement):
            player.rect.x += platform_displacement

    keys = pygame.key.get_pressed()
    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)

    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]
    for obj in to_check:
        if obj and obj.name == "fire":
            if not player.hit:
                hit_sound.play()
                player.health -= 20
                if player.health < 0:
                    player.health = 0
            player.make_hit()


def main(window):
    clock = pygame.time.Clock()
    background, bg_image = get_background("Dawn.png")
    block_size = 96
    player = Player(100, 100, 50, 50)

    floor = [Block(i * block_size, HEIGHT - block_size, block_size)
             for i in range(-WIDTH // block_size, WIDTH * 150 // block_size)]

    parkour_course = generate_infinite_level(
        start_grid_x=4, end_grid_x=150, block_size=block_size)
    objects = [*floor, *parkour_course]

    offset_x = 0
    scroll_area_width = 200

    run = True
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()

        player.loop(FPS)

        for obj in objects:
            if hasattr(obj, "loop") and obj.name == "fire":
                obj.loop()

        handle_move(player, objects)
        draw(window, background, bg_image, player, objects, offset_x)

        if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (player.rect.left - offset_x <= scroll_area_width and player.x_vel < 0):
            offset_x += player.x_vel

        if player.health <= 0:
            pygame.mixer.music.pause()
            death_sound.play()
            draw_game_over_card(window)

            waiting_for_respawn = True
            while waiting_for_respawn:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        quit()
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            player.health = player.max_health
                            player.rect.x = 100
                            player.rect.y = 100
                            offset_x = 0
                            pygame.mixer.music.unpause()
                            waiting_for_respawn = False
                clock.tick(15)

    pygame.quit()
    quit()


if __name__ == "__main__":
    main(window)
