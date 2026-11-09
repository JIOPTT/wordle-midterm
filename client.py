import sys
import os
import pygame
import requests

# 桌面 client 在本機執行，透過這個網址呼叫雲端 FastAPI server。
#API_BASE_URL = "https://wordle-server-a076.onrender.com"
API_BASE_URL = "https://wordle-midterm-axqo.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
WIDTH, HEIGHT = 600, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, R to restart"

        self.total_games = 0
        self.wins = 0
        self.win_rate = 0
        self.hard_mode = False

        self.start_new_game()
        self.get_stats()
    
    def get_stats(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)

            if res.status_code == 200:
                data = res.json()
                self.total_games = data["total_games"]
                self.wins = data["wins"]
                self.win_rate = data["win_rate"]

        except requests.exceptions.RequestException:
            pass

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局 """
        
        try:
            # Render 免費服務休眠後，第一次請求可能需要較久才會喚醒。
            res = requests.post(f"{API_BASE_URL}/api/new-game", timeout=60)
            if res.status_code == 200:
                self.game_id = res.json()["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.message = "New game started!"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id,
            "guess": guess_word,
            "hard_mode": self.hard_mode
            }
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                remaining =data["remaining_guesses"]
                
                # 依據後端回傳更新格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                    self.get_stats()
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        target = data["target_word"]
                        self.message = f"Game Over! The word was {target}. Press R to restart."
                        self.game_over = True
                        self.get_stats()
                    else:
                        self.message = f"Keep guessing!({remaining} tries left)"
            else:
                self.message = res.json().get("detail", "Error processing guess")
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            self.get_stats()
            return

        if event.key == pygame.K_h and event.mod & pygame.KMOD_CTRL:
            self.hard_mode = not self.hard_mode
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
                self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        # 繪製 6x5 網格
        
        stats_text = f"Total: {self.total_games} | Wins: {self.wins} | Win Rate: {self.win_rate}%"
        stats_surface = small_font.render(stats_text, True, COLOR_TEXT)
        stats_rect = stats_surface.get_rect(center=(WIDTH // 2, 40))
        surface.blit(stats_surface, stats_rect)

        mode_text = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_surface = small_font.render(mode_text, True, COLOR_TEXT)
        mode_rect = mode_surface.get_rect(topright=(WIDTH - 15, 75))
        surface.blit(mode_surface, mode_rect)

        margin_x, margin_y = 125, 100
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                # 畫背景框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                # 畫字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 畫底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()