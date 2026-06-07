# game.py
import pygame
import socket 
import threading 
import queue 
import sys
import json # Import json

# Import kelas-kelas lain yang dibutuhkan Game
from player import Player
from camera import Camera
from network_manager import NetworkManager

# --- KONSTANTA (Pastikan ini sesuai dengan main.py yang baru) ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GAME_CAPTION = "Multiplayer Platformer"
FPS = 60

# --- Network Settings (Harus sama dengan main.py yang akan datang) ---
HOST = '192.168.1.2' 
PORT = 12345
MAX_PLAYERS = 4 


class Game:
    def __init__(self):
        pygame.init() 
        self.info = pygame.display.Info()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE) 
        pygame.display.set_caption(GAME_CAPTION)
        self.clock = pygame.time.Clock()
        self.running = True

        # Inisialisasi Camera
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, 2000, 1200)

        self.camera.set_background_image("assets/bg.png")

        
        # Inisialisasi daftar pemain (dictionary)
        self.players = {}
        # Player 0: Controlled by keyboard (local)
        self.add_player(0, 300, 300, "assets/meme4.png", name="Player 1 (Local)") 
        
        # Network manager (pass self to it so it can interact with game state)
        # Assuming HOST, PORT, MAX_PLAYERS are defined in config or here
        from core.config import GameConfig # Import GameConfig here
        game_config = GameConfig()
        
        #self.network_manager = NetworkManager(game_config.HOST, game_config.PORT, game_config.MAX_PLAYERS, self)
        #self.network_manager.start_server()
        # Inisialisasi NetworkManager
        self.network_manager = NetworkManager(HOST, PORT, MAX_PLAYERS, game_instance=self)
        self.network_manager.start_server()
        
        # Pastikan pemain berada di batas dunia awal (pemain yang sudah ada)
        for player_id, player in self.players.items():
            player.rect.left = max(0, min(player.rect.left, self.camera.world_width - player.rect.width))
            player.rect.top = max(0, min(player.rect.top, self.camera.world_height - player.rect.height))
        
        # DEBUGGING PEMAIN
        print(f"DEBUG: Jumlah total pemain yang dibuat saat inisialisasi: {len(self.players)}")
        for idx, p in self.players.items():
            print(f"DEBUG: Player {idx}: Nama='{p.name}', Posisi Awal=({p.rect.x}, {p.rect.y}), ID Memori={id(p)}")
        # AKHIR DEBUGGING

    def add_player(self, player_id, x, y, spritesheet_path, name="Player"):
        """Menambahkan pemain baru ke game."""
        if player_id not in self.players:
            new_player = Player(player_id, x, y, spritesheet_path, name) # Kirim player_id ke Player
            self.players[player_id] = new_player
            print(f"Game: Player {player_id} ({name}) ditambahkan!")
            return new_player
        else:
            # Jika pemain sudah ada, update saja namanya jika berbeda
            if self.players[player_id].name != name:
                self.players[player_id].name = name
                print(f"Game: Updated Player {player_id} name to '{name}'")
            return self.players[player_id] # Kembalikan pemain yang sudah ada

    def remove_player(self, player_id):
        """Removes a player from the game state."""
        if player_id in self.players:
            del self.players[player_id]
            print(f"Game: Player {player_id} removed from game state due to disconnection.")
        else:
            print(f"Game: Attempted to remove non-existent player {player_id}.")
    
    def handle_input(self):
        self.keys_pressed = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                # Tambahkan kontrol keyboard untuk player 0
                if event.key == pygame.K_SPACE and self.players[0].on_ground:
                    self.players[0].vel_y = self.players[0].jump_power
                    self.players[0].on_ground = False
            elif event.type == pygame.VIDEORESIZE:
                pass 

        # --- Process Network Inputs ---
        network_inputs = self.network_manager.get_network_input()
        for player_id, message_dict in network_inputs: # message_dict adalah dictionary JSON
            command = message_dict.get("command")
            player_id_from_msg = message_dict.get("id") # Ambil ID dari pesan

            if player_id_from_msg is None or player_id_from_msg != player_id:
                print(f"Error: Mismatched player ID in network input! Expected {player_id}, got {player_id_from_msg}. Command: {command}")
                continue # Lewati jika ID tidak cocok atau tidak ada

            if player_id in self.players:
                player = self.players[player_id]
                print(f"Player {player_id} received command: {command}") # Debugging
                if command == "LEFT_PRESS":
                    player.current_network_dx = -player.speed 
                elif command == "RIGHT_PRESS":
                    player.current_network_dx = player.speed 
                elif command == "RELEASE_LEFT" or command == "RELEASE_RIGHT":
                    player.current_network_dx = 0 
                elif command == "JUMP_PRESS" and player.on_ground:
                    player.vel_y = player.jump_power
                    player.on_ground = False
                elif command == "CLIENT_READY": # Tangani jika CLIENT_READY diterima lagi (harus sekali)
                    player_name = message_dict.get("name", f"Player {player_id+1} (Remote)")
                    player.name = player_name
                    print(f"Updated name for Player {player_id} to '{player_name}'")
            else:
                print(f"Received input for non-existent player_id: {player_id} from network input.")

    def update(self, dt):
        # Update Player 0 (keyboard)
        keys_dict = {
            pygame.K_LEFT: self.keys_pressed[pygame.K_LEFT],
            pygame.K_RIGHT: self.keys_pressed[pygame.K_RIGHT],
            pygame.K_SPACE: self.keys_pressed[pygame.K_SPACE] 
        }
        self.players[0].update(keys_dict, dt, self.camera.world_width, self.camera.world_height)

        # Update pemain remote (iterasi dictionary)
        for player_id, player_obj in self.players.items():
            if player_id != 0: 
                player_obj.update({}, dt, self.camera.world_width, self.camera.world_height) 

        # Update kamera
        if self.players:
            active_players_pos = []
            for p_id, p_obj in self.players.items():
                 active_players_pos.append(p_obj.rect.center)
            
            avg_x = sum([pos[0] for pos in active_players_pos]) / len(active_players_pos)
            avg_y = sum([pos[1] for pos in active_players_pos]) / len(active_players_pos)
            avg_rect = pygame.Rect(0, 0, 1, 1)
            avg_rect.centerx = int(avg_x)
            avg_rect.centery = int(avg_y)
            self.camera.update_offset(avg_rect)
        else:
            self.camera.update_offset(pygame.Rect(0,0,1,1)) 

    def draw(self):
        self.screen.fill((0, 0, 0)) 
        self.camera.draw_background(self.screen)

        # Gambar semua pemain
        for player_id, player in self.players.items():
            player.draw(self.screen, self.camera.offset_x, self.camera.offset_y, self.camera.zoom)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  
            self.handle_input()
            self.update(dt)
            self.draw()

        self.shutdown()

    def shutdown(self):
        print("Shutting down game...")
        if self.network_manager:
            self.network_manager.shutdown()
        pygame.quit()
        sys.exit()