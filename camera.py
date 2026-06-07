# camera.py
import pygame

class Camera:
    def __init__(self, screen_width, screen_height, world_width, world_height):
        # Ukuran tampilan kamera
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Ukuran dunia game (lebih besar dari layar)
        self.world_width = world_width
        self.world_height = world_height

        # Offset kamera (seberapa jauh kamera "bergeser" dari sudut kiri atas dunia)
        self.offset_x = 0
        self.offset_y = 0

        # Zoom level. 1.0 adalah zoom normal. >1.0 adalah zoom in, <1.0 adalah zoom out.
        self.zoom = 1.0 
        
        # Batas zoom
        self.min_zoom = 0.5
        self.max_zoom = 2.0

        self.background_image = None

    def set_background_image(self, image_path):
        """Memuat gambar latar belakang untuk kamera."""
        try:
            self.background_image = pygame.image.load(image_path).convert_alpha()
        except pygame.error as e:
            print(f"Error loading background image {image_path}: {e}")
            self.background_image = None

    def update_offset(self, target_rect, margin_x=0.2, margin_y=0.3):
        """
        Mengupdate offset kamera agar target_rect tetap di dalam pandangan,
        dan juga mengatur zoom berdasarkan seberapa jauh target_rect dari batas.
        """
        # Hitung pusat kamera relatif terhadap dunia (sebelum zoom)
        center_x = target_rect.centerx
        center_y = target_rect.centery

        # Hitung target offset tanpa zoom
        target_offset_x = center_x - (self.screen_width / 2)
        target_offset_y = center_y - (self.screen_height / 2)

        # Batasi offset agar kamera tidak keluar dari batas dunia
        self.offset_x = max(0, min(target_offset_x, self.world_width - self.screen_width / self.zoom))
        self.offset_y = max(0, min(target_offset_y, self.world_height - self.screen_height / self.zoom))
        
        # --- Logika Zoom Adaptif (Opsional, bisa di tweak) ---
        # Hitung rasio jarak target dari batas dunia
        # Jika target mendekati batas, zoom out. Jika di tengah, zoom in.
        
        # Jarak horizontal dari pusat dunia
        dist_x_ratio = abs(center_x - self.world_width / 2) / (self.world_width / 2)
        # Jarak vertikal dari pusat dunia
        dist_y_ratio = abs(center_y - self.world_height / 2) / (self.world_height / 2)
        
        # Gunakan rasio terbesar untuk menentukan zoom
        overall_dist_ratio = max(dist_x_ratio, dist_y_ratio)

        # Sesuaikan zoom. Semakin jauh dari pusat, semakin zoom out.
        # Anda bisa menyesuaikan angka 0.5 dan 1.5 ini.
        # Misalnya, ketika overall_dist_ratio = 0 (di tengah dunia), zoom = 1.5 (zoom in)
        # Ketika overall_dist_ratio = 1 (di batas dunia), zoom = 0.5 (zoom out)
        new_zoom = self.max_zoom - (overall_dist_ratio * (self.max_zoom - self.min_zoom))
        
        # Batasi zoom ke min/max
        self.zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        
        # Karena zoom berubah, offset juga perlu disesuaikan agar kamera tetap di posisi relatif yang sama
        # Ini penting agar tidak ada "lompatan" visual saat zoom berubah
        self.offset_x = center_x - (self.screen_width / 2 / self.zoom)
        self.offset_y = center_y - (self.screen_height / 2 / self.zoom)

        # Batasi offset lagi setelah zoom
        self.offset_x = max(0, min(self.offset_x, self.world_width - self.screen_width / self.zoom))
        self.offset_y = max(0, min(self.offset_y, self.world_height - self.screen_height / self.zoom))


    def draw_background(self, surface):
        """Menggambar latar belakang, disesuaikan dengan offset kamera dan zoom."""
        if self.background_image:
            # Skala gambar latar belakang agar sesuai dengan ukuran dunia di zoom saat ini
            scaled_bg_width = int(self.world_width * self.zoom)
            scaled_bg_height = int(self.world_height * self.zoom)
            scaled_bg = pygame.transform.scale(self.background_image, (scaled_bg_width, scaled_bg_height))

            # Hitung posisi gambar background relatif terhadap kamera
            # Gambar background digambar dari sudut kiri atas dunia, disesuaikan offset kamera
            draw_x = -int(self.offset_x * self.zoom)
            draw_y = -int(self.offset_y * self.zoom)
            
            surface.blit(scaled_bg, (draw_x, draw_y))