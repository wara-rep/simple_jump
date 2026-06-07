# remote_client.py

import pygame
import socket
import sys
import time
import json 
import threading 

from core.config import GameConfig 

config = GameConfig()
SERVER_IP = config.HOST
SERVER_PORT = config.PORT

SCREEN_WIDTH = 600 # Kita perbesar sedikit agar ada ruang untuk dua panel
SCREEN_HEIGHT = 400 # Perbesar juga tingginya
FPS = 30
GAME_CAPTION = "Remote Control Client"

# Warna
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
BLUE = (0, 100, 200)
LIGHT_BLUE_BG = (100, 150, 200) # Warna biru untuk latar belakang jendela
DARK_GREY_PANEL = (30, 30, 30) # Warna untuk panel

class RemoteClient:
    def __init__(self, server_ip, server_port):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_CAPTION)
        self.clock = pygame.time.Clock()
        self.running = True

        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.client_player_id = None 

        # --- State untuk Input Nama Grafis ---
        self.player_name = ""
        self.input_active = True # Mulai dengan input aktif
        self.font_large = pygame.font.Font(None, 48) # Font lebih besar untuk judul
        self.font_medium = pygame.font.Font(None, 32) # Font sedang untuk teks biasa
        self.font_small = pygame.font.Font(None, 24) # Font kecil untuk detail

        # Posisi dan ukuran kotak input
        self.input_box = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50, 300, 40)
        self.color_inactive = GRAY
        self.color_active = BLUE
        self.color = self.color_active
        self.text_surface_input = self.font_medium.render(self.player_name, True, BLACK)

        # Status koneksi untuk panel kanan
        self.connection_status = "Connecting..." # Initial status
        self.connection_color = GRAY
        
        # Inisialisasi key_states untuk kontrol game (setelah input nama selesai)
        self.key_states = {
            pygame.K_LEFT: False,
            pygame.K_RIGHT: False,
            pygame.K_UP: False,
            pygame.K_DOWN: False
        }
        
        # Koneksi ke server tidak dilakukan di __init__ lagi,
        # akan dipanggil setelah nama dimasukkan dan pemain menekan Enter.

    def connect_to_server(self):
        try:
            print(f"Client: Attempting to connect to {self.server_ip}:{self.server_port}...")
            self.connection_status = f"Connecting to {self.server_ip}:{self.server_port}..."
            self.connection_color = BLUE

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set timeout untuk connect agar tidak hang selamanya
            self.client_socket.settimeout(5) 
            self.client_socket.connect((self.server_ip, self.server_port))
            self.client_socket.settimeout(None) # Hapus timeout setelah terkoneksi

            print(f"Client: Successfully connected to game server at {self.server_ip}:{self.server_port}")
            self.connection_status = "Successfully connected!"
            self.connection_color = (0, 200, 0) # Green for success
            
            # Kirim perintah READY dengan nama pemain dan ID awal (ID akan ditimpa server)
            self.send_command({"command": "CLIENT_READY", "name": self.player_name, "id": 0}) 
            print(f"Client: Sent CLIENT_READY with name '{self.player_name}'.")
            
            self.receive_thread = threading.Thread(target=self._receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            print("Client: Receive thread started.")

        except ConnectionRefusedError:
            self.connection_status = f"Connection refused. Is server running at {self.server_ip}:{self.server_port}?"
            self.connection_color = (200, 0, 0) # Red for error
            print(self.connection_status)
            # self.running = False # Jangan langsung shutdown, biarkan pengguna melihat pesan
        except socket.timeout:
            self.connection_status = f"Connection timed out. Check IP/firewall for {self.server_ip}:{self.server_port}."
            self.connection_color = (200, 0, 0) # Red for error
            print(self.connection_status)
            # self.running = False
        except Exception as e:
            self.connection_status = f"An unexpected error occurred during connection: {e}"
            self.connection_color = (200, 0, 0) # Red for error
            print(self.connection_status)
            # self.running = False

    def _receive_messages(self):
        buffer = ""
        print("Client: Receive thread is listening...")
        while self.running:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    print("Client: Server disconnected.")
                    self.connection_status = "Server disconnected."
                    self.connection_color = (200, 0, 0)
                    self.running = False
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    try:
                        message = json.loads(line)
                        if message.get("command") == "SET_ID":
                            old_id = self.client_player_id
                            self.client_player_id = message.get("id")
                            print(f"Client: Server assigned Player ID: {self.client_player_id} (was {old_id})")
                            self.connection_status = f"Connected! Player ID: {self.client_player_id}"
                            self.connection_color = (0, 200, 0) # Green
                        elif message.get("command") == "GAME_STATE":
                            pass 
                        else:
                            print(f"Client: Received unknown command: {message}")
                            self.connection_status = f"Unknown command: {message.get('command')}"
                            self.connection_color = (200, 100, 0) # Orange
                    except json.JSONDecodeError:
                        print(f"Client: Invalid JSON from server: {line}")
                        self.connection_status = "Received invalid data from server."
                        self.connection_color = (200, 0, 0)
            except Exception as e:
                print(f"Client: Error receiving data: {e}")
                self.connection_status = f"Network error: {e}"
                self.connection_color = (200, 0, 0)
                self.running = False
                break
        print("Client: Receive thread stopped.")
        self.shutdown()

    def send_command(self, command_dict): 
        # Hanya kirim command jika sudah terhubung dan input nama selesai
        if self.client_socket and self.running and not self.input_active: 
            try:
                if self.client_player_id is not None:
                    command_dict["id"] = self.client_player_id
                
                message = json.dumps(command_dict) + '\n' 
                self.client_socket.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Client: Error sending command: {e}")
                self.connection_status = f"Failed to send data: {e}"
                self.connection_color = (200, 0, 0)
                self.running = False
    
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Client: QUIT event detected.")
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.input_active:
                    if self.input_box.collidepoint(event.pos):
                        self.color = self.color_active
                    else:
                        self.color = self.color_inactive
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    print("Client: ESC pressed, quitting.")
                    self.running = False
                
                if self.input_active: # Jika sedang dalam mode input nama
                    if event.key == pygame.K_RETURN:
                        if not self.player_name.strip(): 
                            self.player_name = "Pemain Anonim"
                        self.input_active = False # Matikan mode input
                        # Langsung coba koneksi setelah nama diinput
                        self.connect_to_server() 
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    else:
                        if len(self.player_name) < 15: # Batasi panjang nama
                            if event.unicode.isalnum() or event.unicode in [' ', '_', '-']:
                                self.player_name += event.unicode
                    self.text_surface_input = self.font_medium.render(self.player_name, True, WHITE)
                else: # Jika sudah dalam mode game (input nama sudah selesai)
                    if event.key == pygame.K_LEFT and not self.key_states[pygame.K_LEFT]:
                        self.send_command({"command": "LEFT_PRESS"})
                        self.key_states[pygame.K_LEFT] = True
                    elif event.key == pygame.K_RIGHT and not self.key_states[pygame.K_RIGHT]:
                        self.send_command({"command": "RIGHT_PRESS"})
                        self.key_states[pygame.K_RIGHT] = True
                    elif event.key == pygame.K_UP and not self.key_states[pygame.K_UP]:
                        self.send_command({"command": "JUMP_PRESS"})
                        self.key_states[pygame.K_UP] = True

            elif event.type == pygame.KEYUP and not self.input_active: 
                if event.key == pygame.K_LEFT and self.key_states[pygame.K_LEFT]:
                    self.send_command({"command": "RELEASE_LEFT"})
                    self.key_states[pygame.K_LEFT] = False
                elif event.key == pygame.K_RIGHT and self.key_states[pygame.K_RIGHT]:
                    self.send_command({"command": "RELEASE_RIGHT"})
                    self.key_states[pygame.K_RIGHT] = False
                elif event.key == pygame.K_UP and self.key_states[pygame.K_UP]:
                    self.key_states[pygame.K_UP] = False
                    
    def update(self):
        pass

    def draw(self):
        self.screen.fill(LIGHT_BLUE_BG) # Latar belakang jendela secara keseluruhan

        # --- Gambar area judul ---
        title_font = pygame.font.Font(None, 60)
        title_text = title_font.render("Remote Client Panel", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)

        # --- Definisi Panel ---
        panel_width = (SCREEN_WIDTH - 60) // 2 # 20 margin kiri, 20 margin kanan, 20 margin tengah
        panel_height = SCREEN_HEIGHT - 150 # Ruang di bawah judul

        # Panel Kiri (Informasi Pemain)
        left_panel_rect = pygame.Rect(20, 100, panel_width, panel_height)
        pygame.draw.rect(self.screen, DARK_GREY_PANEL, left_panel_rect)
        pygame.draw.rect(self.screen, WHITE, left_panel_rect, 2) # Border

        # Panel Kanan (Status Koneksi)
        right_panel_rect = pygame.Rect(left_panel_rect.right + 20, 100, panel_width, panel_height)
        pygame.draw.rect(self.screen, DARK_GREY_PANEL, right_panel_rect)
        pygame.draw.rect(self.screen, WHITE, right_panel_rect, 2) # Border

        # --- Konten Panel Kiri ---
        if self.input_active: # Jika sedang menunggu input nama
            prompt_text = self.font_medium.render("Masukkan Nama Anda:", True, WHITE)
            prompt_rect = prompt_text.get_rect(center=(left_panel_rect.centerx, left_panel_rect.top + 50))
            self.screen.blit(prompt_text, prompt_rect)

            # Gambar kotak input
            input_box_centered = pygame.Rect(left_panel_rect.centerx - self.input_box.width // 2, left_panel_rect.top + 100, self.input_box.width, self.input_box.height)
            pygame.draw.rect(self.screen, self.color, input_box_centered, 2) # border
            
            # Text input di dalam kotak
            text_x = input_box_centered.x + 5
            text_y = input_box_centered.y + input_box_centered.height // 2 - self.text_surface_input.get_height() // 2
            self.screen.blit(self.text_surface_input, (text_x, text_y))
            
            # Sesuaikan lebar kotak input agar sesuai dengan teks (tetapi tetap dalam panel)
            self.input_box.w = min(panel_width - 10, max(200, self.text_surface_input.get_width() + 10))
            
            # Instruksi Enter
            enter_prompt = self.font_small.render("Tekan ENTER untuk Lanjut", True, GRAY)
            enter_prompt_rect = enter_prompt.get_rect(center=(left_panel_rect.centerx, left_panel_rect.bottom - 30))
            self.screen.blit(enter_prompt, enter_prompt_rect)

        else: # Jika nama sudah diinput dan sedang terhubung/terhubung
            connected_text = self.font_medium.render(f"Connected as:", True, WHITE)
            name_text = self.font_large.render(self.player_name, True, WHITE)
            id_text = self.font_medium.render(f"Player ID: {self.client_player_id if self.client_player_id is not None else 'Waiting...'}", True, WHITE)

            connected_rect = connected_text.get_rect(midtop=(left_panel_rect.centerx, left_panel_rect.top + 40))
            name_rect = name_text.get_rect(midtop=(left_panel_rect.centerx, connected_rect.bottom + 10))
            id_rect = id_text.get_rect(midtop=(left_panel_rect.centerx, name_rect.bottom + 30))

            self.screen.blit(connected_text, connected_rect)
            self.screen.blit(name_text, name_rect)
            self.screen.blit(id_text, id_rect)

        # --- Konten Panel Kanan (Konektivitas) ---
        connectivity_title = self.font_medium.render("Connectivity Progress:", True, WHITE)
        connectivity_title_rect = connectivity_title.get_rect(midtop=(right_panel_rect.centerx, right_panel_rect.top + 40))
        self.screen.blit(connectivity_title, connectivity_title_rect)

        status_text = self.font_small.render(self.connection_status, True, self.connection_color)
        status_text_rect = status_text.get_rect(midtop=(right_panel_rect.centerx, connectivity_title_rect.bottom + 20))
        self.screen.blit(status_text, status_text_rect)
        
        # Tambahkan indikator visual sederhana (opsional)
        if "Connecting" in self.connection_status and "Successfully" not in self.connection_status:
            loading_dots = ""
            current_time = time.time()
            num_dots = int(current_time * 2) % 4 # 0, 1, 2, 3 dots
            loading_dots = "." * num_dots
            
            dots_surface = self.font_small.render(loading_dots, True, self.connection_color)
            dots_rect = dots_surface.get_rect(midtop=(right_panel_rect.centerx, status_text_rect.bottom + 10))
            self.screen.blit(dots_surface, dots_rect)


        pygame.display.flip()

    def run(self):
        print("Client: Entering main game loop.")
        while self.running:
            self.clock.tick(FPS)
            self.handle_input()
            self.update()
            self.draw()
        print("Client: Exited main game loop.")
        self.shutdown()

    def shutdown(self):
        print("Client: Shutting down remote client...")
        if self.client_socket:
            try:
                # Menutup socket dengan aman
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError as e:
                print(f"Client: Error during client socket shutdown: {e}")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    client = RemoteClient(SERVER_IP, SERVER_PORT)
    client.run()