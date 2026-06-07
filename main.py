import pygame
import sys
#from player import Player # Pastikan player.py berada di direktori yang sama
#from network_manager import NetworkManager

# Import kelas Game dari file game.py yang baru
from game import Game

# --- Konstanta yang masih dibutuhkan di sini (jika ada) ---
# Misalnya, jika Anda punya konstanta global lain yang dipakai di banyak tempat
# Tapi untuk saat ini, kita bisa kosongkan atau sisakan yang minimal.

if __name__ == "__main__":
    game = Game()
    game.run()