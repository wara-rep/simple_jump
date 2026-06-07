import pygame

class Player:
    def __init__(self, player_id, x, y, spritesheet_path, name="Player"): # Tambah player_id
        # Player attributes (constants)
        self.speed = 500  # pixels per second
        self.gravity = 1800 # pixels/second^2
        self.jump_power = -600 # initial vertical velocity for jump

        # Dynamic state attributes
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.current_network_dx = 0 # Added for network-controlled horizontal movement

        # Animation attributes
        self.frames = []
        self.frame_index = 0
        self.animation_timer = 0
        self.animation_speed = 0.1 # Time in seconds per frame for each frame transition

        # Load frames and create rect
        self.load_frames(spritesheet_path)
        # Ensure rect is created after frames are loaded, even if placeholder
        self.rect = self.frames[0].get_rect(topleft=(x, y))

        # Player identity for display
        self.player_id = player_id # Simpan ID pemain
        self.name = name
        # Initialize font for player name display
        pygame.font.init() 
        self.font = pygame.font.Font(None, 30)

    def load_frames(self, spritesheet_path):
        """Loads frames from a spritesheet. Assumes 4 frames horizontally."""
        try:
            spritesheet = pygame.image.load(spritesheet_path).convert_alpha()
        except pygame.error as e:
            print(f"Error loading spritesheet {spritesheet_path}: {e}")
            self.frames = [pygame.Surface((50, 50), pygame.SRCALPHA)]
            self.frames[0].fill((255, 0, 255, 128)) 
            return

        sheet_width, sheet_height = spritesheet.get_size()
        num_frames_x = 4 
        frame_width = sheet_width // num_frames_x
        
        self.frames = []
        for i in range(num_frames_x):
            frame = pygame.Surface((frame_width, sheet_height), pygame.SRCALPHA)
            frame.blit(spritesheet, (0, 0), (i * frame_width, 0, frame_width, sheet_height))
            self.frames.append(frame)
        
        if not self.frames: 
            self.frames = [pygame.Surface((50, 50), pygame.SRCALPHA)]
            self.frames[0].fill((255, 0, 255, 128))

    def update(self, keys_dict, dt, world_width, world_height):
        """Updates player's position and animation based on input and physics."""
        dx = 0

        # --- Horizontal Movement ---
        # Prioritize keyboard input if available for movement (hanya untuk player 0)
        if self.player_id == 0: # Hanya player 0 yang menggunakan keyboard
            if pygame.K_LEFT in keys_dict and keys_dict[pygame.K_LEFT]:
                dx -= self.speed * dt
                self.facing_right = False
            elif pygame.K_RIGHT in keys_dict and keys_dict[pygame.K_RIGHT]:
                dx += self.speed * dt
                self.facing_right = True
            else:
                dx = 0 # Tidak ada input keyboard horizontal
        
        # Untuk semua pemain (termasuk player 0 jika tidak ada input keyboard, atau pemain remote)
        # Gunakan network movement jika ada dan tidak ada input keyboard horizontal
        if self.player_id != 0 or dx == 0: # Jika ini pemain remote ATAU pemain lokal tanpa input keyboard
            if self.current_network_dx != 0:
                dx = self.current_network_dx * dt
                self.facing_right = self.current_network_dx > 0


        # --- Jumping ---
        # Keyboard jump (hanya untuk player 0)
        if self.player_id == 0 and pygame.K_SPACE in keys_dict and keys_dict[pygame.K_SPACE] and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False
        # Note: Network jump commands are handled directly in Game.handle_input()
        # by directly setting player.vel_y, so no need to check current_network_jump here.


        # Apply Gravity
        self.vel_y += self.gravity * dt
        self.rect.y += self.vel_y * dt
        
        # Vertical World Bounds Check
        if self.rect.bottom >= world_height:
            self.rect.bottom = world_height
            self.vel_y = 0
            self.on_ground = True
        elif self.rect.top < 0: 
            self.rect.top = 0
            self.vel_y = 0

        self.rect.x += dx

        # Horizontal World Bounds Check
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(world_width, self.rect.right)

        # Animation Update
        # Animate if moving horizontally (by keyboard or network) or if in the air
        if dx != 0 or not self.on_ground:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0
                self.frame_index = (self.frame_index + 1) % len(self.frames)
        else:
            self.frame_index = 0 # Assume first frame is idle

    def draw(self, surface, camera_offset_x, camera_offset_y, camera_zoom):
        """Draws the player on the given surface, adjusted by camera's offset and zoom."""
        current_frame = self.frames[self.frame_index]
        
        # Flip frame if facing left
        if not self.facing_right:
            current_frame = pygame.transform.flip(current_frame, True, False)

        # Scale the frame based on camera zoom
        scaled_frame = pygame.transform.rotozoom(current_frame, 0, camera_zoom)

        # Calculate position relative to camera's view (world coordinates to screen coordinates)
        draw_x = int((self.rect.x - camera_offset_x) * camera_zoom)
        draw_y = int((self.rect.y - camera_offset_y) * camera_zoom)
        
        # Draw player sprite
        surface.blit(scaled_frame, (draw_x, draw_y))

        # --- Draw Player Name ---
        if self.name:
            name_surface = self.font.render(self.name, True, (255, 255, 255)) 
            name_rect = name_surface.get_rect()
            
            name_rect.centerx = draw_x + scaled_frame.get_width() // 2
            name_rect.bottom = draw_y - 5 

            surface.blit(name_surface, name_rect)