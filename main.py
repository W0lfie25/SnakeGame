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

# --- Fonts ---
try:
    font = pygame.font.Font(asset_path("PressStart2P-Regular.ttf"), 26)
    small_font = pygame.font.Font(asset_path("PressStart2P-Regular.ttf"), 20)
except:
    font = pygame.font.SysFont("Arial", 26)
    small_font = pygame.font.SysFont("Arial", 20)

# --- Image Loader ---
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

# --- Images ---
snake_head_img = load_img("snake_head.png", (BLOCK, BLOCK), fallback_color=(0, 255, 0))
snake_body_img = load_img("snake_body.png", (BLOCK, BLOCK), fallback_color=(0, 180, 0))
snake_tail_img = load_img("snake_tail.png", (BLOCK, BLOCK), fallback_color=(0, 120, 0))
snake_bend_img = load_img("snake_bend.png", (BLOCK, BLOCK), fallback_color=(0, 150, 0))

raw_logo = load_img("snake_logo.png")
snake_logo = pygame.transform.smoothscale(raw_logo, (WIDTH // 2, HEIGHT // 4))

menu_bg = load_img("menu_bg.png", (WIDTH, HEIGHT), alpha=False)
gameover_bg = load_img("gameover_bg.png", (WIDTH, HEIGHT), alpha=False)

apple_icon_img = load_img("apple_icon.png", (40, 40), fallback_color=(220, 40, 40))
trophy_icon_img = load_img("trophy_icon.png", (40, 40), fallback_color=(240, 200, 0))

# --- Sounds ---
try:
    death_sound = pygame.mixer.Sound(asset_path("death.wav"))
    eat_sound = pygame.mixer.Sound(asset_path("eat.wav"))

    menu_music = asset_path("menu_music.wav")
    game_music = asset_path("game_music.wav")
    gameover_music = asset_path("gameover_music.wav")

except:
    death_sound = None
    eat_sound = None

    menu_music = ""
    game_music = ""
    gameover_music = ""

# --- Save System ---
SAVE_FILE = os.path.join(app_path(), "save_data.json")

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                loaded = json.load(f)

            # Fix old save formats
            for player in loaded.get("players", {}):
                pdata = loaded["players"][player]

                if "Normal" not in pdata:
                    pdata["Normal"] = pdata.get("high_score", 0)

                if "Hard" not in pdata:
                    pdata["Hard"] = 0

            return loaded

        except:
            pass

    return {"players": {}}

data = load_data()

def save_data(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- UI ---
def draw_text(text, x, y, color=(255,255,255), small=False, center=False):
    used_font = small_font if small else font

    img = used_font.render(text, True, color)

    rect = img.get_rect(center=(x, y)) if center else img.get_rect(topleft=(x, y))

    screen.blit(img, rect)

def blit_scaled(img):
    scaled = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
    screen.blit(scaled, (0, 0))

# --- Input Box ---
class InputBox:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]

            elif len(self.text) < 12 and event.unicode.isprintable():
                if event.key != pygame.K_RETURN:
                    self.text += event.unicode

    def draw(self):
        color = (255,255,255) if self.active else (100,100,100)

        pygame.draw.rect(screen, (30,30,30), self.rect, border_radius=8)
        pygame.draw.rect(screen, color, self.rect, 2, border_radius=8)

        txt_surface = small_font.render(self.text, True, (255,255,255))
        text_rect = txt_surface.get_rect(center=self.rect.center)

        screen.blit(txt_surface, text_rect)

# --- Grid Background ---
def create_checkered_bg():
    surf = pygame.Surface((PLAY_W, PLAY_H))

    color1 = (179, 185, 54)
    color2 = (153, 158, 39)

    for row in range(PLAY_H // BLOCK):
        for col in range(PLAY_W // BLOCK):

            rect_color = color1 if (row + col) % 2 == 0 else color2

            pygame.draw.rect(
                surf,
                rect_color,
                (col * BLOCK, row * BLOCK, BLOCK, BLOCK)
            )

    return surf

play_area_img = create_checkered_bg()

# --- Gameplay ---
def spawn_food(snake):
    while True:
        food = (
            random.randrange(PLAY_X, PLAY_X + PLAY_W, BLOCK),
            random.randrange(PLAY_Y, PLAY_Y + PLAY_H, BLOCK)
        )

        if food not in snake:
            return food

def draw_ui(player_name, score, difficulty):

    player_info = data["players"].get(
        player_name,
        {"Normal": 0, "Hard": 0}
    )

    # BEST SCORE ACROSS BOTH MODES
    stored_high_score = max(
        player_info.get("Normal", 0),
        player_info.get("Hard", 0)
    )

    is_breaking_record = score >= stored_high_score and score > 0

    ui_color = (255, 215, 0) if is_breaking_record else (255,255,255)

    display_high = max(score, stored_high_score)

    # Current Score
    screen.blit(apple_icon_img, (30, 20))
    draw_text(str(score), 80, 30)

    # High Score
    screen.blit(trophy_icon_img, (200, 20))
    draw_text(str(display_high), 250, 30, color=ui_color)

    # New Record Text
    if is_breaking_record:
        draw_text(
            f"NEW RECORD: {player_name.upper()}!",
            WIDTH // 2,
            80,
            color=(255,215,0),
            small=True,
            center=True
        )

    # Player Name
    name_surf = small_font.render(player_name, True, (255,255,255))
    screen.blit(name_surf, (WIDTH - name_surf.get_width() - 30, 35))

def draw_snake(snake, direction):
    for i, part in enumerate(snake):

        angle = 0
        img = None

        if i == 0:
            img = snake_head_img

            dx, dy = direction

            if dx > 0:
                angle = 0
            elif dx < 0:
                angle = 180
            elif dy > 0:
                angle = 270
            elif dy < 0:
                angle = 90

        elif i == len(snake) - 1:
            img = snake_tail_img

            prev_part = snake[i - 1]

            dx = prev_part[0] - part[0]
            dy = prev_part[1] - part[1]

            if dx > 0:
                angle = 0
            elif dx < 0:
                angle = 180
            elif dy > 0:
                angle = 270
            elif dy < 0:
                angle = 90

        else:
            prev_p = snake[i - 1]
            next_p = snake[i + 1]

            if prev_p[0] == next_p[0] or prev_p[1] == next_p[1]:

                img = snake_body_img

                angle = 0 if prev_p[0] != part[0] else 90

            else:
                img = snake_bend_img

                p1 = (prev_p[0] - part[0], prev_p[1] - part[1])
                p2 = (next_p[0] - part[0], next_p[1] - part[1])

                if (
                    (p1 == (0, -BLOCK) and p2 == (BLOCK, 0))
                    or
                    (p2 == (0, -BLOCK) and p1 == (BLOCK, 0))
                ):
                    angle = 0

                elif (
                    (p1 == (BLOCK, 0) and p2 == (0, BLOCK))
                    or
                    (p2 == (BLOCK, 0) and p1 == (0, BLOCK))
                ):
                    angle = 270

                elif (
                    (p1 == (0, BLOCK) and p2 == (-BLOCK, 0))
                    or
                    (p2 == (0, BLOCK) and p1 == (-BLOCK, 0))
                ):
                    angle = 180

                else:
                    angle = 90

        if img:
            screen.blit(pygame.transform.rotate(img, angle), part)

def countdown(draw_frame):
    for i in range(3, 0, -1):

        draw_frame()

        draw_text(
            str(i),
            WIDTH // 2,
            HEIGHT // 2,
            center=True
        )

        pygame.display.update()
        pygame.time.delay(1000)

# --- Screens ---

def intro_screen():

    if os.path.exists(menu_music):
        pygame.mixer.music.load(menu_music)
        pygame.mixer.music.play(-1)

    while True:

        blit_scaled(menu_bg)

        logo_rect = snake_logo.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(snake_logo, logo_rect)

        draw_text(
            "CLICK TO CONTINUE",
            WIDTH // 2,
            HEIGHT - 80,
            small=True,
            center=True
        )

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return
            
def main_menu():
    # Button Dimensions
    BTN_W = 300
    BTN_H = 60
    CENTER_X = WIDTH // 2
    CENTER_Y = HEIGHT // 2

    # Vertical spacing: each button is 80 pixels apart (center to center)
    # This ensures they look identical and balanced
    play_rect = pygame.Rect(CENTER_X - 150, CENTER_Y - 120, BTN_W, BTN_H)
    leaderboard_rect = pygame.Rect(CENTER_X - 150, CENTER_Y - 40, BTN_W, BTN_H)
    exit_rect = pygame.Rect(CENTER_X - 150, CENTER_Y + 40, BTN_W, BTN_H)

    while True:
        blit_scaled(menu_bg)
        
        # --- 1. PLAY BUTTON (Green) ---
        pygame.draw.rect(screen, (50, 200, 80), play_rect, border_radius=10)
        draw_text("PLAY", play_rect.centerx, play_rect.centery, small=True, center=True)

        # --- 2. LEADERBOARD BUTTON (Blue) ---
        pygame.draw.rect(screen, (50, 150, 200), leaderboard_rect, border_radius=10)
        draw_text("LEADERBOARD", leaderboard_rect.centerx, leaderboard_rect.centery, small=True, center=True)

        # --- 3. EXIT BUTTON (Red) ---
        pygame.draw.rect(screen, (200, 60, 60), exit_rect, border_radius=10)
        draw_text("EXIT GAME", exit_rect.centerx, exit_rect.centery, small=True, center=True)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check Play
                if play_rect.collidepoint(event.pos):
                    return "play"
                
                # Check Leaderboard
                if leaderboard_rect.collidepoint(event.pos):
                    leaderboard_screen()
                
                # Check Exit
                if exit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:

                if play_rect.collidepoint(event.pos):
                    return "play"


def settings_form():
    global data
    data = load_data()

    # Layout Constants - Increased width to 380 to prevent "leaking"
    BTN_W = 380
    BTN_H = 55
    CENTER_X = WIDTH // 2
    
    # Position the elements
    name_box = InputBox(CENTER_X - 150, HEIGHT // 2 - 120, 300, 50)
    
    # This is the single Difficulty Box
    diff_rect = pygame.Rect(CENTER_X - (BTN_W // 2), HEIGHT // 2 - 20, BTN_W, BTN_H)
    
    # Play Button
    play_rect = pygame.Rect(CENTER_X - 120, HEIGHT // 2 + 70, 240, 60)
    
    # Back Button
    back_rect = pygame.Rect(20, HEIGHT - 80, 140, 50)

    difficulty = "Normal"

    while True:
        blit_scaled(menu_bg)

        # 1. Name Prompt
        draw_text("Enter Name", CENTER_X, HEIGHT // 2 - 160, small=True, center=True)
        name_box.draw()

        # 2. Difficulty Button
        # Background & Border
        pygame.draw.rect(screen, (40, 40, 40), diff_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), diff_rect, 2, border_radius=8)
        
        # Text - We use small_font to ensure it fits the width
        diff_str = f"Difficulty: {difficulty}"
        # Render text manually to ensure we control the centering
        txt_surf = small_font.render(diff_str, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=diff_rect.center)
        screen.blit(txt_surf, txt_rect)

        # 3. Play Button
        pygame.draw.rect(screen, (50, 200, 80), play_rect, border_radius=10)
        draw_text("PLAY", play_rect.centerx, play_rect.centery, small=True, center=True)

        # 4. Back Button
        pygame.draw.rect(screen, (200, 60, 60), back_rect, border_radius=10)
        draw_text("BACK", back_rect.centerx, back_rect.centery, small=True, center=True)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            name_box.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check for Difficulty Toggle
                if diff_rect.collidepoint(event.pos):
                    difficulty = "Hard" if difficulty == "Normal" else "Normal"

                # Check for Play
                if play_rect.collidepoint(event.pos):
                    name = name_box.text.strip()
                    if name:
                        if name not in data["players"]:
                            data["players"][name] = {"Normal": 0, "Hard": 0}
                            save_data(data)
                        return name, difficulty

                # Check for Back
                if back_rect.collidepoint(event.pos):
                    return None, None

# --- Game ---
def game(player_name, difficulty):

    if player_name not in data["players"]:

        data["players"][player_name] = {
            "Normal": 0,
            "Hard": 0
        }

        save_data(data)

    start_x = PLAY_X + (PLAY_W // (2 * BLOCK)) * BLOCK
    start_y = PLAY_Y + (PLAY_H // (2 * BLOCK)) * BLOCK

    snake = [
        (start_x, start_y),
        (start_x - BLOCK, start_y)
    ]

    direction = (BLOCK, 0)
    next_direction = direction

    food = spawn_food(snake)

    score = 0

    dead = False
    paused = False

    death_timer = 0
    death_duration = 2000

    def draw_frame(is_visible=True):

        screen.fill((74, 117, 44))

        header_height = PLAY_Y - 15

        pygame.draw.rect(
            screen,
            (46, 74, 27),
            (0, 0, WIDTH, header_height)
        )

        border_size = 15

        pygame.draw.rect(
            screen,
            (90,145,55),
            (
                PLAY_X - border_size,
                PLAY_Y - border_size,
                PLAY_W + border_size * 2,
                PLAY_H + border_size * 2
            )
        )

        screen.blit(play_area_img, (PLAY_X, PLAY_Y))

        draw_ui(player_name, score, difficulty)

        if is_visible:
            draw_snake(snake, direction)

        screen.blit(apple_icon_img, food)

    countdown(draw_frame)

    while True:

        speed = 15 if difficulty == "Hard" else 10

        clock.tick(speed)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                save_data(data)
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    paused = not paused

                if not dead and not paused:

                    if event.key == pygame.K_UP and direction != (0, BLOCK):
                        next_direction = (0, -BLOCK)

                    elif event.key == pygame.K_DOWN and direction != (0, -BLOCK):
                        next_direction = (0, BLOCK)

                    elif event.key == pygame.K_LEFT and direction != (BLOCK, 0):
                        next_direction = (-BLOCK, 0)

                    elif event.key == pygame.K_RIGHT and direction != (-BLOCK, 0):
                        next_direction = (BLOCK, 0)

        if paused:

            draw_text(
                "PAUSED",
                WIDTH // 2,
                HEIGHT // 2,
                center=True
            )

            pygame.display.update()
            continue

        if not dead:

            direction = next_direction

            head = (
                snake[0][0] + direction[0],
                snake[0][1] + direction[1]
            )

            if (
                head[0] < PLAY_X
                or head[0] >= PLAY_X + PLAY_W
                or head[1] < PLAY_Y
                or head[1] >= PLAY_Y + PLAY_H
                or head in snake
            ):

                dead = True

                death_timer = pygame.time.get_ticks()

                if death_sound:
                    death_sound.play()

                current_best = max(
                data["players"][player_name].get("Normal", 0),
                data["players"][player_name].get("Hard", 0)
)
                if score > current_best:
                 data["players"][player_name][difficulty] = score
                save_data(data)

            else:

                snake.insert(0, head)

                if head == food:

                    score += 1

                    if eat_sound:
                        eat_sound.play()

                    food = spawn_food(snake)

                    if score > data["players"][player_name][difficulty]:

                        data["players"][player_name][difficulty] = score

                        save_data(data)

                else:
                    snake.pop()

        if dead:

            current_time = pygame.time.get_ticks()

            if current_time - death_timer > death_duration:
                return score

            blink_visible = (current_time // 150) % 2 == 0

            draw_frame(is_visible=blink_visible)

        else:
            draw_frame(is_visible=True)

        pygame.display.update()

# --- Game Over ---
def game_over_screen(score):
    if os.path.exists(gameover_music):
        pygame.mixer.music.load(gameover_music)
        pygame.mixer.music.play(0)

    restart_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 20, 240, 60)
    menu_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 100, 240, 60)
    quit_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 180, 240, 60)

    while True:
        blit_scaled(gameover_bg)

        draw_text("Game Over", WIDTH // 2, HEIGHT // 2 - 120, center=True)
        draw_text(f"Score: {score}", WIDTH // 2, HEIGHT // 2 - 60, center=True)

        # Restart Button
        pygame.draw.rect(screen, (50, 200, 80), restart_rect, border_radius=10)
        draw_text(
            "RESTART",
            restart_rect.centerx,
            restart_rect.centery,
            center=True,
            small=True
        )

        # Main Menu Button
        pygame.draw.rect(screen, (70, 120, 220), menu_rect, border_radius=10)
        draw_text(
            "MAIN MENU",
            menu_rect.centerx,
            menu_rect.centery,
            center=True,
            small=True
        )

        # Quit Button
        pygame.draw.rect(screen, (200, 60, 60), quit_rect, border_radius=10)
        draw_text(
            "QUIT",
            quit_rect.centerx,
            quit_rect.centery,
            center=True,
            small=True
        )

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Keyboard
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "restart"

                if event.key == pygame.K_m:
                    return "menu"

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            # Mouse
            if event.type == pygame.MOUSEBUTTONDOWN:
                if restart_rect.collidepoint(event.pos):
                    return "restart"

                if menu_rect.collidepoint(event.pos):
                    return "menu"

                if quit_rect.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

def leaderboard_screen():

    data = load_data()

    mode = "NORMAL"  # NORMAL / HARD

    normal_rect = pygame.Rect(WIDTH//2 - 180, 120, 160, 45)
    hard_rect = pygame.Rect(WIDTH//2 + 20, 120, 160, 45)

    back_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT - 120, 200, 60)

    while True:

        blit_scaled(menu_bg)

        draw_text("LEADERBOARD", WIDTH//2, 60, center=True)

        # --- TAB BUTTONS ---
        pygame.draw.rect(screen, (60, 60, 60), normal_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), hard_rect, border_radius=8)

        draw_text("NORMAL", normal_rect.centerx, normal_rect.centery, small=True, center=True)
        draw_text("HARD", hard_rect.centerx, hard_rect.centery, small=True, center=True)

        # highlight active tab
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            normal_rect if mode == "NORMAL" else hard_rect,
            2,
            border_radius=8
        )

        # --- SORT PLAYERS ---
        players = list(data["players"].items())

        if mode == "NORMAL":
            players.sort(key=lambda x: x[1].get("Normal", 0), reverse=True)
        else:
            players.sort(key=lambda x: x[1].get("Hard", 0), reverse=True)

        # --- DRAW LIST ---
        y = 200

        for i, (name, scores) in enumerate(players[:10]):

            n = scores.get("Normal", 0)
            h = scores.get("Hard", 0)

            draw_text(f"{i+1}. {name[:12]}", WIDTH//2 - 200, y, small=True)

            if mode == "NORMAL":
                draw_text(str(n), WIDTH//2 + 120, y, small=True)
            else:
                draw_text(str(h), WIDTH//2 + 120, y, small=True)

            y += 40

        # --- BACK BUTTON ---
        pygame.draw.rect(screen, (200, 60, 60), back_rect, border_radius=10)
        draw_text("BACK", back_rect.centerx, back_rect.centery, small=True, center=True)

        pygame.display.update()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:

                if back_rect.collidepoint(event.pos):
                    return

                if normal_rect.collidepoint(event.pos):
                    mode = "NORMAL"

                if hard_rect.collidepoint(event.pos):
                    mode = "HARD"

# --- Main Logic ---
while True:

    intro_screen()

    action = main_menu()

    if action == "play":

        player, difficulty = settings_form()

        if player is None:
            continue
        while True:

            if os.path.exists(game_music):
                pygame.mixer.music.load(game_music)
                pygame.mixer.music.play(-1)

            final_score = game(player, difficulty)
            result = game_over_screen(final_score)

            if result == "restart":
                continue

            elif result == "menu":
                break