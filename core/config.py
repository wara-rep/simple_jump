# my_game_project/core/config.py

class GameConfig:
    def __init__(self):
        # Resolusi jendela awal yang Anda inginkan
        self.SCREEN_WIDTH = 2400
        self.SCREEN_HEIGHT = 800

        self.TILE_SIZE = 42  # Ukuran dasar untuk sprite dan tile

        self.GAME_TITLE = "CODING COMBAT SMPIA47"

        self.WORLD_WIDTH = 2400 # Lebar dunia (sama dengan SCREEN_WIDTH untuk latar belakang yang pas)
        # PENTING: Tinggi dunia sama dengan tinggi layar. Ini berarti TIDAK ADA scrolling vertikal pada kamera.
        self.WORLD_HEIGHT = self.SCREEN_HEIGHT 

        # Offset dari bagian bawah layar tempat kaki pemain akan berada
        self.PLAYER_GROUND_OFFSET_FROM_BOTTOM_SCREEN = 10 
        
        # Posisi X awal pemain di tengah dunia
        self.INITIAL_PLAYER_X = self.WORLD_WIDTH // 2 
        # Posisi Y awal pemain akan dihitung di game.py berdasarkan tinggi layar saat ini

        self.GRAVITY = 900 # Piksel per detik kuadrat
        self.JUMP_STRENGTH = -400 # Kecepatan lompat awal

        self.BACKGROUND_IMAGE_PATH = "assets/background.jpg" # Pastikan ini .jpg
        
        
        self.HOST = '192.168.1.2'  # localhost
        self.PORT = 12345       # Port yang akan digunakan
        self.MAX_PLAYERS = 5    # Contoh: Jumlah maksimum klien yang bisa terhubung