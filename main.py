import pygame
import random
import json
import os
import sys

pygame.init()
pygame.mixer.init()

# --- Configuration ---
WIDTH, HEIGHT = 900, 760
BLOCK = 40
FPS = 10

UI_TOP = 120
PLAY_W = 800
PLAY_H = 600
PLAY_X = (WIDTH - PLAY_W) // 2
PLAY_Y = UI_TOP

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")
clock = pygame.time.Clock()

# --- Path Helpers ---
def asset_path(filename):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, "assets", filename)

def app_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

# --- Asset Loading ---
try:
    font = pygame.font.Font(asset_path("PressStart2P-Regular.ttf"), 26)
    small_font = pygame.font.Font(asset_path("PressStart2P-Regular.ttf"), 20)
except:
    font = pygame.font.SysFont("Arial", 26)
    small_font = pygame.font.SysFont("Arial", 20)

def load_img(filename, size=None, alpha=True, fallback_color=(80, 80, 80)):
    path = asset_path(filename)
    if not os.path.exists(path):
        surface = pygame.Surface(size if size else (40, 40), pygame.SRCALPHA)
        surface.fill(fallback_color)
        return surface
    img = pygame.image.load(path)
    img = img.convert_alpha() if alpha else img.convert()
    if size:
        img = pygame.transform.scale(img, size)
    return img

# Load Images
snake_head_img = load_img("snake_head.png", (BLOCK, BLOCK), fallback_color=(0, 255, 0))
snake_body_img = load_img("snake_body.png", (BLOCK, BLOCK), fallback_color=(0, 180, 0))
snake_tail_img = load_img("snake_tail.png", (BLOCK, BLOCK), fallback_color=(0, 120, 0))
snake_bend_img = load_img("snake_bend.png", (BLOCK, BLOCK), fallback_color=(0, 150, 0))
snake_logo = load_img("snake_logo.png", (WIDTH // 2, HEIGHT // 4))
menu_bg = load_img("menu_bg.png", (WIDTH, HEIGHT), alpha=False)
gameover_bg = load_img("gameover_bg.png", (WIDTH, HEIGHT), alpha=False)
game_bg = load_img("game_bg.png", (WIDTH, HEIGHT), alpha=False)
food_img = load_img("food.png", (BLOCK, BLOCK), fallback_color=(220, 40, 40))
outer_background_img = load_img("outer_background.png", (WIDTH, HEIGHT), alpha=False, fallback_color=(6, 69, 8))
play_area_img = load_img("play_area.png", (PLAY_W, PLAY_H), alpha=False, fallback_color=(120, 170, 60))
apple_icon_img = load_img("apple_icon.png", (40, 40), fallback_color=(220, 40, 40))
trophy_icon_img = load_img("trophy_icon.png", (40, 40), fallback_color=(240, 200, 0))

# Sounds
try:
    death_sound = pygame.mixer.Sound(asset_path("death.wav"))
    eat_sound = pygame.mixer.Sound(asset_path("eat.wav"))
    menu_music = asset_path("menu_music.wav")
    game_music = asset_path("game_music.wav")
    gameover_music = asset_path("gameover_music.wav")
except:
    death_sound = eat_sound = None 

# --- Data Management ---
SAVE_FILE = os.path.join(app_path(), "save_data.json")

def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {"players": {}, "previous_players": []}

def save_data(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# --- UI Helpers ---
def draw_text(text, x, y, color=(255, 255, 255), small=False, center=False):
    used_font = small_font if small else font
    img = used_font.render(text, True, color)
    rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))
    screen.blit(img, rect)

def fade_transition(draw_next_frame, speed=5):
    fade = pygame.Surface((WIDTH, HEIGHT))
    fade.fill((0, 0, 0))
    for alpha in range(0, 255, speed):
        draw_next_frame()
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.update()
    for alpha in range(255, -1, -speed):
        draw_next_frame()
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.update()

def blit_scaled(img, pos=(0, 0)):
    scaled = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
    screen.blit(scaled, pos)

# --- Gameplay Functions ---
def spawn_food(snake):
    while True:
        food = (random.randrange(PLAY_X, PLAY_X + PLAY_W, BLOCK), random.randrange(PLAY_Y, PLAY_Y + PLAY_H, BLOCK))
        if food not in snake: return food

def draw_ui(player_name, score):
    high_score = data["players"][player_name]["high_score"]
    
    # Draw Score
    screen.blit(apple_icon_img, (30, 20))
    draw_text(str(score), 80, 30) 
    
    # Draw High Score
    screen.blit(trophy_icon_img, (200, 20))
    draw_text(str(high_score), 250, 30)
    
    # Draw Player Name (Only once, correctly aligned)
    name_surf = small_font.render(player_name, True, (255, 255, 255))
    name_x = WIDTH - name_surf.get_width() - 30
    screen.blit(name_surf, (name_x, 35))

def draw_snake(snake, current_dir):
    for i, part in enumerate(snake):
        angle = 0
        img = None
        if i == 0:  
            img = snake_head_img
            dx, dy = current_dir
            if dx > 0: angle = 0
            elif dx < 0: angle = 180
            elif dy > 0: angle = 270
            elif dy < 0: angle = 90
        elif i == len(snake) - 1:
            img = snake_tail_img
            prev_part = snake[i-1]
            dx, dy = prev_part[0] - part[0], prev_part[1] - part[1]
            if dx > 0: angle = 0
            elif dx < 0: angle = 180
            elif dy > 0: angle = 270
            elif dy < 0: angle = 90
        else:
            prev_p, next_p = snake[i-1], snake[i+1]
            if prev_p[0] == next_p[0] or prev_p[1] == next_p[1]:
                img = snake_body_img
                angle = 0 if prev_p[0] - part[0] != 0 else 90
            else:
                img = snake_bend_img
                p1 = (prev_p[0] - part[0], prev_p[1] - part[1])
                p2 = (next_p[0] - part[0], next_p[1] - part[1])
                if (p1 == (0, -BLOCK) and p2 == (BLOCK, 0)) or (p2 == (0, -BLOCK) and p1 == (BLOCK, 0)): angle = 0
                elif (p1 == (BLOCK, 0) and p2 == (0, BLOCK)) or (p2 == (BLOCK, 0) and p1 == (0, BLOCK)): angle = 270
                elif (p1 == (0, BLOCK) and p2 == (-BLOCK, 0)) or (p2 == (0, BLOCK) and p1 == (-BLOCK, 0)): angle = 180
                else: angle = 90
        if img:
            screen.blit(pygame.transform.rotate(img, angle), part)

def countdown(draw_frame):
    for i in range(3, 0, -1):
        draw_frame()
        draw_text(str(i), WIDTH // 2, HEIGHT // 2, center=True)
        pygame.display.update()
        pygame.time.delay(1000)

# --- Screens ---
def main_menu():
    if os.path.exists(menu_music):
        pygame.mixer.music.load(menu_music)
        pygame.mixer.music.play(-1)
    while True:
        blit_scaled(menu_bg)
        logo_rect = snake_logo.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        screen.blit(snake_logo, logo_rect)
        draw_text("Click to continue", WIDTH // 2, HEIGHT // 2 + 120, small=True, center=True)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                return

def ask_player_name():
    name = ""
    typing = True
    sorted_players = sorted(data["players"].items(), key=lambda x: x[1]['high_score'], reverse=True)

    while typing:
        blit_scaled(menu_bg)
        center_y = HEIGHT // 2
        draw_text("Enter Player Name", WIDTH // 2, center_y - 140, center=True)
        
        input_rect = pygame.Rect(WIDTH // 2 - 200, center_y - 70, 400, 50)
        pygame.draw.rect(screen, (30, 30, 30), input_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), input_rect, 2, border_radius=10)
        
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        draw_text(name + cursor, WIDTH // 2, center_y - 45, small=True, center=True)
        draw_text("Press ENTER to start", WIDTH // 2, center_y, small=True, center=True)

        if sorted_players:
            draw_text("PREVIOUS PLAYERS (TOP 5)", WIDTH // 2, center_y + 70, (255, 215, 0), small=True, center=True)
            for i, (p_name, p_data) in enumerate(sorted_players[:5]):
                player_score = p_data['high_score']
                y_pos = center_y + 110 + (i * 35)
                draw_text(f"{i+1}. {p_name}", WIDTH // 2 - 180, y_pos, small=True)
                draw_text(f"{player_score}", WIDTH // 2 + 120, y_pos, small=True)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_data(data); pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip():
                    typing = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif len(name) < 10 and event.unicode.isprintable():
                    name += event.unicode

    name = name.strip()
    if name not in data["players"]:
        data["players"][name] = {"high_score": 0}
    if name not in data["previous_players"]:
        data["previous_players"].append(name)
    save_data(data)
    return name

def game(player_name):
    start_x = PLAY_X + (PLAY_W // (2 * BLOCK)) * BLOCK
    start_y = PLAY_Y + (PLAY_H // (2 * BLOCK)) * BLOCK
    snake = [(start_x, start_y), (start_x - BLOCK, start_y)]
    direction = (BLOCK, 0)
    next_direction = direction
    food = spawn_food(snake)
    score = 0
    dead = False
    death_timer = 0
    death_duration = 2000 
    paused = False

    def draw_frame(is_visible=True):
        screen.blit(outer_background_img, (0, 0))
        screen.blit(play_area_img, (PLAY_X, PLAY_Y))
        draw_ui(player_name, score)
        if is_visible:
            draw_snake(snake, direction)
        screen.blit(apple_icon_img, food)

    countdown(draw_frame)

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_data(data); pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: paused = not paused
                if not dead and not paused:
                    if event.key == pygame.K_UP and direction != (0, BLOCK): next_direction = (0, -BLOCK)
                    elif event.key == pygame.K_DOWN and direction != (0, -BLOCK): next_direction = (0, BLOCK)
                    elif event.key == pygame.K_LEFT and direction != (BLOCK, 0): next_direction = (-BLOCK, 0)
                    elif event.key == pygame.K_RIGHT and direction != (-BLOCK, 0): next_direction = (BLOCK, 0)

        if paused:
            draw_text("PAUSED", WIDTH // 2, HEIGHT // 2, center=True)
            pygame.display.update(); continue

        if not dead:
            direction = next_direction
            head = (snake[0][0] + direction[0], snake[0][1] + direction[1])
            if (head[0] < PLAY_X or head[0] >= PLAY_X + PLAY_W or 
                head[1] < PLAY_Y or head[1] >= PLAY_Y + PLAY_H or head in snake):
                dead = True
                death_timer = pygame.time.get_ticks()
                if death_sound: death_sound.play()
                if score > data["players"][player_name]["high_score"]:
                    data["players"][player_name]["high_score"] = score
                save_data(data)
            else:
                snake.insert(0, head)
                if head == food:
                    score += 1
                    if eat_sound: eat_sound.play()
                    food = spawn_food(snake)
                else:
                    snake.pop()

        if dead:
            current_time = pygame.time.get_ticks()
            if current_time - death_timer > death_duration: return score
            blink_visible = (current_time // 150) % 2 == 0
            draw_frame(is_visible=blink_visible)
        else:
            draw_frame(is_visible=True)

        pygame.display.update()

def game_over_screen(score):
    if os.path.exists(gameover_music):
        pygame.mixer.music.load(gameover_music)
        pygame.mixer.music.play(0)
    restart_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 20, 240, 60)
    quit_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 100, 240, 60)
    while True:
        blit_scaled(gameover_bg)
        draw_text("Game Over", WIDTH // 2, HEIGHT // 2 - 120, center=True)
        draw_text(f"Score: {score}", WIDTH // 2, HEIGHT // 2 - 60, center=True)
        pygame.draw.rect(screen, (50, 200, 80), restart_rect, border_radius=10)
        draw_text("RESTART", restart_rect.centerx, restart_rect.centery, center=True, small=True)
        pygame.draw.rect(screen, (200, 60, 60), quit_rect, border_radius=10)
        draw_text("QUIT", quit_rect.centerx, quit_rect.centery, center=True, small=True)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if restart_rect.collidepoint(event.pos): return "restart"
                if quit_rect.collidepoint(event.pos): pygame.quit(); sys.exit()

# --- Main Logic ---
while True:
    main_menu()
    player = ask_player_name()
    while True:
        if os.path.exists(game_music):
            pygame.mixer.music.load(game_music)
            pygame.mixer.music.play(-1)
        final_score = game(player)
        result = game_over_screen(final_score)
        if result != "restart": break