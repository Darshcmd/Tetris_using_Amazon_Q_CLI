import pygame
import random
import time
import json
import os
import math
from pygame import mixer
import struct
import wave

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30
GRID_OFFSET_X = (SCREEN_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
GRID_OFFSET_Y = (SCREEN_HEIGHT - GRID_HEIGHT * BLOCK_SIZE) // 2 + 50
SCORE_FILE = "high_scores.json"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
LIGHT_GRAY = (100, 100, 100)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
DARK_BLUE = (0, 0, 139)
BG_COLOR = (10, 10, 10)

# Tetromino shapes (rotated versions of 0 degrees)
# Each shape is represented by a list of relative coordinates (x, y)
SHAPES = {
    'I': [
        [(0, 1), (1, 1), (2, 1), (3, 1)],  # I
        [(1, 0), (1, 1), (1, 2), (1, 3)]
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],  # J
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)]
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],  # L
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (1, 2)]
    ],
    'O': [
        [(0, 0), (1, 0), (0, 1), (1, 1)]  # O
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],  # S
        [(0, 0), (0, 1), (1, 1), (1, 2)]
    ],
    'T': [
        [(1, 0), (0, 1), (1, 1), (2, 1)],  # T
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)]
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],  # Z
        [(2, 0), (1, 1), (2, 1), (1, 2)]
    ]
}

# Colors for each Tetromino
COLORS = {
    'I': CYAN,
    'J': DARK_BLUE,
    'L': ORANGE,
    'O': YELLOW,
    'S': GREEN,
    'T': PURPLE,
    'Z': RED
}

# Sound generation parameters
SAMPLE_RATE = 44100  # samples per second
BITS_PER_SAMPLE = 16  # 16-bit audio
NUM_CHANNELS = 1 # Mono audio

def create_simple_sound(filename, duration, frequency, amplitude=0.5):
    """
    Creates a simple sine wave sound and saves it to a WAV file.
    """
    num_samples = int(duration * SAMPLE_RATE)
    max_amplitude = 32767 # For 16-bit audio (signed)

    # Generate raw samples as signed 16-bit integers
    raw_samples = []
    for i in range(num_samples):
        value = int(amplitude * max_amplitude * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE))
        raw_samples.append(value)

    # Convert samples to a byte string
    # '<h' means little-endian, signed short (2 bytes)
    byte_data = b''.join(struct.pack('<h', sample) for sample in raw_samples)

    # Write to WAV file using the wave module
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(NUM_CHANNELS)
        wf.setsampwidth(BITS_PER_SAMPLE // 8)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(byte_data)

class Tetris:
    def __init__(self):
        pygame.init()
        mixer.init(SAMPLE_RATE, -BITS_PER_SAMPLE, NUM_CHANNELS, 4096) # Initialize mixer for sound effects

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        self.small_font = pygame.font.Font(None, 24)

        self.grid = self.create_empty_grid()
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.drop_speed = 1000  # milliseconds
        self.last_drop_time = time.time() * 1000
        self.game_over = False
        self.paused = False
        self.show_high_scores = False
        self.high_scores = self.load_high_scores()

        self.particles = []

        self.load_sounds()
        # REMOVED: self.load_music() - No background music desired

    def load_sounds(self):
        # Create sound files if they don't exist
        self.create_sound_files()

        self.sound_clear = mixer.Sound("clear.wav")
        self.sound_drop = mixer.Sound("drop.wav")
        self.sound_gameover = mixer.Sound("gameover.wav")
        self.sound_move = mixer.Sound("move.wav")
        self.sound_rotate = mixer.Sound("rotate.wav")

    def create_sound_files(self):
        # Only create files if they don't exist to avoid re-generating every time
        if not os.path.exists("clear.wav"):
            create_simple_sound("clear.wav", 0.1, 880)  # A5 note
        if not os.path.exists("drop.wav"):
            create_simple_sound("drop.wav", 0.05, 110)  # A2 note
        if not os.path.exists("gameover.wav"):
            create_simple_sound("gameover.wav", 1.0, 55, amplitude=0.7)  # A1 note
        if not os.path.exists("move.wav"):
            create_simple_sound("move.wav", 0.05, 220)  # A3 note
        if not os.path.exists("rotate.wav"):
            create_simple_sound("rotate.wav", 0.1, 440)  # A4 note

    # REMOVED: load_music method entirely
    # def load_music(self):
    #     if not os.path.exists("tetris_music.wav"):
    #         create_simple_sound("tetris_music.wav", 5.0, 440, amplitude=0.2) # A4, 5 seconds loop
    #     mixer.music.load("tetris_music.wav")
    #     mixer.music.set_volume(0.3)
    #     mixer.music.play(-1) # -1 means loop indefinitely

    def create_empty_grid(self):
        return [['' for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    def new_piece(self):
        shape_name = random.choice(list(SHAPES.keys()))
        return {
            'shape': SHAPES[shape_name],
            'color': COLORS[shape_name],
            'x': GRID_WIDTH // 2 - 2,
            'y': 0,
            'rotation': 0,
            'name': shape_name
        }

    def draw_grid(self):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(GRID_OFFSET_X + x * BLOCK_SIZE,
                                   GRID_OFFSET_Y + y * BLOCK_SIZE,
                                   BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(self.screen, LIGHT_GRAY, rect, 1)  # Draw grid lines

                # Draw fallen blocks
                color = self.grid[y][x]
                if color:
                    pygame.draw.rect(self.screen, color, rect)
                    pygame.draw.rect(self.screen, BLACK, rect, 1)  # Block borders

    def draw_piece(self, piece, offset_x=0, offset_y=0):
        for x_offset, y_offset in piece['shape'][piece['rotation']]:
            block_x = piece['x'] + x_offset
            block_y = piece['y'] + y_offset
            if 0 <= block_x < GRID_WIDTH and 0 <= block_y < GRID_HEIGHT:
                rect = pygame.Rect(offset_x + block_x * BLOCK_SIZE,
                                   offset_y + block_y * BLOCK_SIZE,
                                   BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(self.screen, piece['color'], rect)
                pygame.draw.rect(self.screen, BLACK, rect, 1)

    def draw_ghost_piece(self):
        ghost_piece = self.current_piece.copy()
        while self.valid_position(ghost_piece, y_offset=1):
            ghost_piece['y'] += 1

        # Draw the ghost piece with a transparent or different color
        for x_offset, y_offset in ghost_piece['shape'][ghost_piece['rotation']]:
            block_x = ghost_piece['x'] + x_offset
            block_y = ghost_piece['y'] + y_offset
            if 0 <= block_x < GRID_WIDTH and 0 <= block_y < GRID_HEIGHT:
                rect = pygame.Rect(GRID_OFFSET_X + block_x * BLOCK_SIZE,
                                   GRID_OFFSET_Y + block_y * BLOCK_SIZE,
                                   BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(self.screen, (150, 150, 150), rect, 1) # Gray outline

    def valid_position(self, piece, x_offset=0, y_offset=0, rotation_offset=0):
        test_rotation = (piece['rotation'] + rotation_offset) % len(piece['shape'])
        for x_rel, y_rel in piece['shape'][test_rotation]:
            block_x = piece['x'] + x_rel + x_offset
            block_y = piece['y'] + y_rel + y_offset

            # Check boundaries
            if not (0 <= block_x < GRID_WIDTH and 0 <= block_y < GRID_HEIGHT):
                return False
            # Check collision with existing blocks in the grid
            if self.grid[block_y][block_x]:
                return False
        return True

    def rotate_piece(self):
        original_rotation = self.current_piece['rotation']
        self.current_piece['rotation'] = (self.current_piece['rotation'] + 1) % len(self.current_piece['shape'])

        # Wall kick (simple implementation)
        kicks = {
            'I': [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)], # SRS kicks for I
            'J': [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)], # SRS kicks for JLSTZ
            'L': [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
            'S': [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
            'T': [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
            'Z': [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
            'O': [(0,0)] # O doesn't rotate relative to its center
        }

        # Determine which kick set to use based on current and next rotation state
        # Simplified: using kick data for 0->1, 1->2, 2->3, 3->0 rotation
        # This is a very basic SRS-like implementation. A full SRS would involve
        # specific kick tables for each rotation state transition.
        kick_data_index = original_rotation % 4 if self.current_piece['name'] != 'I' else original_rotation % 2

        kick_offsets = kicks[self.current_piece['name']]

        # Adjust kick attempts based on piece name for different SRS rules
        if self.current_piece['name'] == 'I':
            # For I-piece, use 5 kicks specifically for 0->1, 1->0, 1->2, 2->1, 2->3, 3->2
            # Here we're simplifying, effectively just trying offsets
            effective_kicks = kick_offsets
        else:
            # For JLSTZ, use standard 5 kicks
            effective_kicks = kick_offsets


        for kick_x, kick_y in effective_kicks:
            if self.valid_position(self.current_piece, x_offset=kick_x, y_offset=kick_y):
                self.current_piece['x'] += kick_x
                self.current_piece['y'] += kick_y
                self.sound_rotate.play()
                return

        # If no kick works, revert rotation
        self.current_piece['rotation'] = original_rotation


    def lock_piece(self, piece):
        for x_offset, y_offset in piece['shape'][piece['rotation']]:
            block_x = piece['x'] + x_offset
            block_y = piece['y'] + y_offset
            if 0 <= block_x < GRID_WIDTH and 0 <= block_y < GRID_HEIGHT:
                self.grid[block_y][block_x] = piece['color']

        self.sound_drop.play()
        self.check_lines()

        # Generate new piece
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()

        # Game over condition: new piece can't be placed
        if not self.valid_position(self.current_piece):
            self.game_over = True
            self.sound_gameover.play()
            # REMOVED: mixer.music.stop() # No background music to stop

    def check_lines(self):
        lines_to_clear = []
        for y in range(GRID_HEIGHT):
            if all(self.grid[y][x] != '' for x in range(GRID_WIDTH)):
                lines_to_clear.append(y)

        if lines_to_clear:
            self.sound_clear.play()
            num_cleared = len(lines_to_clear)
            self.score += self.calculate_score(num_cleared)
            self.lines_cleared += num_cleared
            self.update_level()
            self.create_line_clear_particles(lines_to_clear)

            # Remove cleared lines and shift lines down
            for line_y in sorted(lines_to_clear, reverse=True):
                self.grid.pop(line_y)
                self.grid.insert(0, ['' for _ in range(GRID_WIDTH)])

    def calculate_score(self, num_lines):
        # Classic Tetris scoring
        if num_lines == 1:
            return 100 * self.level
        elif num_lines == 2:
            return 300 * self.level
        elif num_lines == 3:
            return 500 * self.level
        elif num_lines == 4: # Tetris!
            return 800 * self.level
        return 0

    def update_level(self):
        new_level = 1 + (self.lines_cleared // 10)
        if new_level > self.level:
            self.level = new_level
            self.drop_speed = max(50, 1000 - (self.level - 1) * 70) # Increase speed, min 50ms

    def hard_drop(self):
        while self.valid_position(self.current_piece, y_offset=1):
            self.current_piece['y'] += 1
            self.score += 2 # Score for each cell hard dropped

        self.lock_piece(self.current_piece)
        self.sound_drop.play()

    def reset_game(self):
        # Save score if it's a high score
        self.save_high_score(self.score)

        self.grid = self.create_empty_grid()
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.drop_speed = 1000
        self.last_drop_time = time.time() * 1000
        self.game_over = False
        self.paused = False
        self.show_high_scores = False
        self.high_scores = self.load_high_scores() # Reload high scores in case of new entry
        # REMOVED: mixer.music.play(-1) # No background music to restart

    def draw_next_piece(self):
        next_text = self.font.render("NEXT", True, WHITE)
        self.screen.blit(next_text, (GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE + 50, GRID_OFFSET_Y))

        # Draw next piece centered in a smaller area
        next_piece_display_x = GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE + 50
        next_piece_display_y = GRID_OFFSET_Y + 40
        self.draw_piece(self.next_piece, next_piece_display_x, next_piece_display_y)

    def draw_ui(self):
        score_text = self.font.render(f"SCORE: {self.score}", True, WHITE)
        level_text = self.font.render(f"LEVEL: {self.level}", True, WHITE)
        lines_text = self.font.render(f"LINES: {self.lines_cleared}", True, WHITE)

        self.screen.blit(score_text, (20, 20))
        self.screen.blit(level_text, (20, 60))
        self.screen.blit(lines_text, (20, 100))

        # Controls Hint
        controls_text = self.small_font.render("Controls:", True, WHITE)
        left_right_text = self.small_font.render("Left/Right Arrows: Move", True, WHITE)
        down_text = self.small_font.render("Down Arrow: Soft Drop", True, WHITE)
        up_z_text = self.small_font.render("Up/Z: Rotate", True, WHITE)
        space_text = self.small_font.render("Space: Hard Drop", True, WHITE)
        p_text = self.small_font.render("P: Pause", True, WHITE)
        r_text = self.small_font.render("R: Restart (Game Over/Paused)", True, WHITE)
        h_text = self.small_font.render("H: High Scores (Game Over)", True, WHITE)

        self.screen.blit(controls_text, (SCREEN_WIDTH - 200, 20))
        self.screen.blit(left_right_text, (SCREEN_WIDTH - 200, 50))
        self.screen.blit(down_text, (SCREEN_WIDTH - 200, 70))
        self.screen.blit(up_z_text, (SCREEN_WIDTH - 200, 90))
        self.screen.blit(space_text, (SCREEN_WIDTH - 200, 110))
        self.screen.blit(p_text, (SCREEN_WIDTH - 200, 130))
        self.screen.blit(r_text, (SCREEN_WIDTH - 200, 150))
        self.screen.blit(h_text, (SCREEN_WIDTH - 200, 170))

    def load_high_scores(self):
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_high_score(self, new_score):
        if new_score > 0:
            self.high_scores.append(new_score)
            self.high_scores = sorted(self.high_scores, reverse=True)[:5] # Keep top 5
            with open(SCORE_FILE, 'w') as f:
                json.dump(self.high_scores, f)

    def draw_high_scores(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))

        title_text = self.big_font.render("HIGH SCORES", True, WHITE)
        self.screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 100))

        y_offset = 200
        if not self.high_scores:
            no_scores_text = self.font.render("No high scores yet!", True, LIGHT_GRAY)
            self.screen.blit(no_scores_text, (SCREEN_WIDTH // 2 - no_scores_text.get_width() // 2, y_offset))
        else:
            for i, score in enumerate(self.high_scores):
                score_display = self.font.render(f"{i + 1}. {score}", True, WHITE)
                self.screen.blit(score_display, (SCREEN_WIDTH // 2 - score_display.get_width() // 2, y_offset + i * 40))

        back_text = self.font.render("Press H to go back", True, LIGHT_GRAY)
        self.screen.blit(back_text, (SCREEN_WIDTH // 2 - back_text.get_width() // 2, SCREEN_HEIGHT - 50))


    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))

        game_over_text = self.big_font.render("GAME OVER", True, RED)
        final_score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        restart_text = self.font.render("Press R to Restart", True, LIGHT_GRAY)
        high_scores_text = self.font.render("Press H for High Scores", True, LIGHT_GRAY)

        self.screen.blit(game_over_text,
                         (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 - 100))
        self.screen.blit(final_score_text,
                         (SCREEN_WIDTH // 2 - final_score_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 - 20))
        self.screen.blit(restart_text,
                         (SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(high_scores_text,
                         (SCREEN_WIDTH // 2 - high_scores_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 + 70))

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))

        paused_text = self.big_font.render("PAUSED", True, WHITE)
        continue_text = self.font.render("Press P to Continue", True, LIGHT_GRAY)
        restart_text = self.font.render("Press R to Restart", True, LIGHT_GRAY)

        self.screen.blit(paused_text,
                         (SCREEN_WIDTH // 2 - paused_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(continue_text,
                         (SCREEN_WIDTH // 2 - continue_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 - 10))
        self.screen.blit(restart_text,
                         (SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
                          SCREEN_HEIGHT // 2 + 30))

    def create_line_clear_particles(self, cleared_lines):
        for y in cleared_lines:
            for x in range(GRID_WIDTH):
                color = self.grid[y][x]
                if color:
                    center_x = GRID_OFFSET_X + x * BLOCK_SIZE + BLOCK_SIZE // 2
                    center_y = GRID_OFFSET_Y + y * BLOCK_SIZE + BLOCK_SIZE // 2
                    for _ in range(5): # Create 5 particles per cleared block
                        self.particles.append(Particle(center_x, center_y, color))

    def draw_particles(self):
        for particle in self.particles:
            particle.update()
            particle.draw(self.screen)
        self.particles = [p for p in self.particles if p.is_alive()]

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if self.show_high_scores:
                    if event.key == pygame.K_h:
                        self.show_high_scores = False
                elif self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_h:
                        self.show_high_scores = True
                elif self.paused:
                    if event.key == pygame.K_p:
                        self.paused = False
                    elif event.key == pygame.K_r:
                        self.reset_game()
                else:
                    if event.key == pygame.K_LEFT:
                        if self.valid_position(self.current_piece, x_offset=-1):
                            self.current_piece['x'] -= 1
                            self.sound_move.play()
                    elif event.key == pygame.K_RIGHT:
                        if self.valid_position(self.current_piece, x_offset=1):
                            self.current_piece['x'] += 1
                            self.sound_move.play()
                    elif event.key == pygame.K_DOWN:
                        if self.valid_position(self.current_piece, y_offset=1):
                            self.current_piece['y'] += 1
                    elif event.key == pygame.K_UP or event.key == pygame.K_z:
                        self.rotate_piece()
                    elif event.key == pygame.K_SPACE:
                        self.hard_drop()
                    elif event.key == pygame.K_p:
                        self.paused = True
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_h:
                        self.show_high_scores = True

        return True

    def update(self):
        if self.game_over or self.paused or self.show_high_scores:
            return

        # Auto drop
        current_time = time.time() * 1000
        if current_time - self.last_drop_time > self.drop_speed:
            if self.valid_position(self.current_piece, y_offset=1):
                self.current_piece['y'] += 1
            else:
                self.lock_piece(self.current_piece)

            self.last_drop_time = current_time

    def draw(self):
        # Clear the screen
        self.screen.fill(BG_COLOR)

        # Draw the game elements
        self.draw_grid()
        self.draw_ghost_piece()
        self.draw_piece(self.current_piece, GRID_OFFSET_X, GRID_OFFSET_Y)
        self.draw_next_piece()
        self.draw_ui()
        self.draw_particles()

        # Draw game over, pause, or high scores screen if needed
        if self.game_over:
            self.draw_game_over()
        elif self.paused:
            self.draw_pause()
        elif self.show_high_scores:
            self.draw_high_scores()

        # Update the display
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)  # 60 FPS

        # Clean up before quitting
        # mixer.music.stop() # No background music to stop
        pygame.quit()


class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 5)
        self.velocity_x = random.uniform(-2, 2)
        self.velocity_y = random.uniform(-4, -1)
        self.alpha = 255
        self.decay_rate = random.randint(5, 15)

    def update(self):
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y += 0.1 # Gravity
        self.alpha = max(0, self.alpha - self.decay_rate)
        self.size = max(0, self.size - 0.05) # Shrink

    def draw(self, screen):
        if self.alpha > 0 and self.size > 0:
            s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            color_with_alpha = self.color + (int(self.alpha),)
            pygame.draw.circle(s, color_with_alpha, (int(self.size), int(self.size)), int(self.size))
            screen.blit(s, (self.x - self.size, self.y - self.size))

    def is_alive(self):
        return self.alpha > 0 and self.size > 0

# Start the game
if __name__ == "__main__":
    game = Tetris()
    game.run()
