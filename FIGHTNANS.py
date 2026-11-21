#imports
import pygame
import sys
import random

#constants
BG_COLOUR = (25, 25, 25)
DEADZONE = 0.15
TRIGGER_THRESHOLD = 0.5
PLAYER_WIDTH = 64 #px
PLAYER_HEIGHT = 64 #px
ENEMY_WIDTH = 64 #px
ENEMY_HEIGHT = 64 #px
ENEMY_STOPPING_DISTANCE = 64 #px
OBJECTIVE_WIDTH = 128 #px
OBJECTIVE_HEIGHT = 128 #px
MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"
COMPLETE = "complete"
PLAYER_COLOURS = {1:(70, 130, 220),2:(70, 190, 90)}

#configuration variables
screen_width = 1280
screen_height = 720
fps = 60
players_amt = 2
start_intermission = True
enemy_health_draw = True
debug_controller_connections = False
debug_movement = False
debug_movement_vectors = False
debug_aiming = False
debug_aiming_vectors = False
debug_shooting = False
debug_combat = False

#functions
def debug_print(category, message):
    if category:
        print(message)

def spawn_enemy():
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        return Enemy(random.uniform(0, screen_width-ENEMY_WIDTH), 0, ENEMY_WIDTH, ENEMY_HEIGHT, (170,90,90))
    elif edge == "bottom":
        return Enemy(random.uniform(0, screen_width-ENEMY_WIDTH), screen_height-ENEMY_HEIGHT, ENEMY_WIDTH, ENEMY_HEIGHT, (170,90,90))
    elif edge == "left":
        return Enemy(0, random.uniform(0, screen_height-ENEMY_HEIGHT), ENEMY_WIDTH, ENEMY_HEIGHT, (170,90,90))
    elif edge == "right":
        return Enemy(screen_width-ENEMY_WIDTH, random.uniform(0, screen_height-ENEMY_HEIGHT), ENEMY_WIDTH, ENEMY_HEIGHT, (170,90,90))

def start_game():
    global projectiles, players, enemies, objective_objects, current_wave, start_intermission
    start_intermission = True
    projectiles = []
    players = []
    objective_objects = []
    for p in range(players_amt):
        players.append(Player(random.uniform(0, screen_width - PLAYER_WIDTH), random.uniform(0, screen_height - PLAYER_HEIGHT), PLAYER_COLOURS[p+1], p+1))
    for player, controller_id in zip(players, active_controllers):
        player.joystick_id = controller_id
    objective_objects.append(Objective(random.uniform(0, screen_width - OBJECTIVE_WIDTH), random.uniform(0, screen_height - OBJECTIVE_HEIGHT)))
    enemies = []
    current_wave = Wave(1, 5, 1.5)
    current_wave.wait_active = True

def draw_menu(screen):
    title_text = menu_title_font.render("FIGHTNANS", True, (255, 255, 255))
    title_x = (screen_width - title_text.get_width()) / 2
    screen.blit(title_text, (title_x, 180))
    for i, option in enumerate(menu_options):
        colour = (255, 255, 255) if i == selected_menu_option else (140, 140, 140)
        option_text = menu_option_font.render(option, True, colour)
        option_x = (screen_width - option_text.get_width()) / 2
        screen.blit(option_text, (option_x, 390 + i * 70))

def draw_game_over(screen):
    title_text = menu_title_font.render("GAME OVER", True, (217, 71, 71))
    title_x = (screen_width - title_text.get_width()) / 2
    screen.blit(title_text, (title_x, 180))
    for i, option in enumerate(game_over_options):
        colour = (255, 255, 255) if i == selected_game_over_option else (140, 140, 140)
        option_text = menu_option_font.render(option, True, colour)
        option_x = (screen_width - option_text.get_width()) / 2
        screen.blit(option_text, (option_x, 390 + i * 70))

def draw_mission_complete(screen):
    title_text = menu_title_font.render("MISSION COMPLETE", True, (71, 217, 71))
    title_x = (screen_width - title_text.get_width()) / 2
    screen.blit(title_text, (title_x, 180))
    for i, option in enumerate(mission_complete_options):
        colour = (255, 255, 255) if i == selected_mission_complete_option else (140, 140, 140)
        option_text = menu_option_font.render(option, True, colour)
        option_x = (screen_width - option_text.get_width()) / 2
        screen.blit(option_text, (option_x, 390 + i * 70))

#classes
class Wave:
    def __init__(self, wave_number, enemies_per_wave, spawn_interval):
        self.wave_number = wave_number
        self.enemies_per_wave = enemies_per_wave
        self.spawn_interval = spawn_interval
        self.enemies_spawned = 0
        self.spawn_elapsed = spawn_interval
        self.wait_duration = 3
        self.wait_elapsed = 0
        self.wait_active = False
    
    def wait_complete(self):
        return self.wait_active and self.wait_elapsed >= self.wait_duration
    
    def update(self, dt, enemies):
        #wave complete, wait begin
        if self.complete(enemies) and not self.wait_active:
            self.wait_active = True
        if self.wait_active:
            self.wait_elapsed += dt
            return
        #spawn enemies
        if self.enemies_spawned < self.enemies_per_wave:
            self.spawn_elapsed += dt
            if self.spawn_elapsed >= self.spawn_interval:
                    enemies.append(spawn_enemy())
                    self.enemies_spawned += 1
                    self.spawn_elapsed = 0
    
    def complete(self, enemies):
        if self.enemies_spawned == self.enemies_per_wave and len(enemies) == 0:
            return True
        else:
            return False
    
    def start(self):
        self.wait_active = False
        self.wait_elapsed = 0
        self.spawn_elapsed = self.spawn_interval

class Projectile:
    def __init__(self, pos, direction, colour, speed=600, damage=25, owner="player"):
        self.pos = pygame.Vector2(pos)
        self.direction = direction.copy()
        self.speed = speed
        self.owner = owner
        self.alive = True
        self.damage = damage
        self.radius = 10
        self.colour = tuple(int(c * 0.7) for c in colour)
    
    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        if (self.pos.x < 0 or self.pos.x > screen_width or self.pos.y < 0 or self.pos.y > screen_height):
            self.alive = False
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.colour, self.pos, self.radius)
    
    def check_collision(self, target):
        projectile_rect = pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius, self.radius * 2, self.radius * 2)
        target_rect = pygame.Rect(target.pos.x, target.pos.y, (target.width if hasattr(target, "width") else PLAYER_WIDTH), (target.height if hasattr(target, "height") else PLAYER_HEIGHT))
        return projectile_rect.colliderect(target_rect)

class Player:
    def __init__(self, x, y, colour, player_num):
        self.joystick_id = None
        self.colour = colour
        self.player_num = player_num
        self.pos = pygame.Vector2(x, y)
        self.max_health = 100
        self.health = self.max_health
        self.alive = True
        self.speed = 300 #px/s
        self.aim_direction = pygame.Vector2(1, 0)
        self.shooting = False
    
    def update(self, joysticks, dt, projectiles, enemies, players):
        if not self.alive or self.joystick_id is None or self.joystick_id not in joysticks:
            return
        joystick = joysticks[self.joystick_id]
        
        #movement
        x_pos = joystick.get_axis(0)
        y_pos = joystick.get_axis(1)
        movement = pygame.Vector2(x_pos, y_pos)
        if movement.length() < DEADZONE:
            movement = pygame.Vector2(0, 0)
        if movement.length() > 1:
            movement.normalize_ip()
        debug_print(debug_movement_vectors, f"Normalised Movement Magnitude: {movement.length():.2f}")
        
        #previous position
        previous_pos = self.pos.copy()
        
        #horizontal movement
        self.pos.x += movement.x * self.speed * dt
        #horizontal player-enemy collision
        player_rect = pygame.Rect(self.pos.x, self.pos.y, PLAYER_WIDTH, PLAYER_HEIGHT)
        for enemy in enemies:
            enemy_rect = pygame.Rect(enemy.pos.x, enemy.pos.y, enemy.width, enemy.height)
            if player_rect.colliderect(enemy_rect):
                if previous_pos.x + PLAYER_WIDTH <= enemy_rect.left:
                    self.pos.x = enemy_rect.left - PLAYER_WIDTH
                elif previous_pos.x >= enemy_rect.right:
                    self.pos.x = enemy_rect.right
                player_rect.x = self.pos.x
        
        #vertical movement
        self.pos.y += movement.y * self.speed * dt
        #vertical player-enemy collision
        player_rect.y = self.pos.y
        for enemy in enemies:
            enemy_rect = pygame.Rect(enemy.pos.x, enemy.pos.y, enemy.width, enemy.height)
            if player_rect.colliderect(enemy_rect):
                if previous_pos.y + PLAYER_HEIGHT <= enemy_rect.top:
                    self.pos.y = enemy_rect.top - PLAYER_HEIGHT
                elif previous_pos.y >= enemy_rect.bottom:
                    self.pos.y = enemy_rect.bottom
                player_rect.y = self.pos.y 
        #screen border collision
        if self.pos.x < 0:
            self.pos.x = 0
            debug_print(debug_movement, f"Player attempted to exceed negative X screen boundary.")
        if self.pos.x > screen_width - PLAYER_WIDTH:
            self.pos.x = screen_width - PLAYER_WIDTH
            debug_print(debug_movement, f"Player attempted to exceed positive X screen boundary.")
        if self.pos.y < 0:
            self.pos.y = 0
            debug_print(debug_movement, f"Player attempted to exceed positive Y screen boundary.")
        if self.pos.y > screen_height - PLAYER_HEIGHT:
            self.pos.y = screen_height - PLAYER_HEIGHT
            debug_print(debug_movement, f"Player attempted to exceed negative Y screen boundary.")
        
        #aiming
        debug_print(debug_aiming_vectors, f"Right stick: X={joystick.get_axis(2):.2f}, Y={joystick.get_axis(3):.2f}")
        x_dir = joystick.get_axis(2)
        y_dir = joystick.get_axis(3)
        aim = pygame.Vector2(x_dir, y_dir)
        if aim.length() > DEADZONE:
            aim.normalize_ip()
            self.aim_direction = aim
        debug_print(debug_aiming, f"Aim direction: {self.aim_direction}")
        
        #shooting
        rt_axis = joystick.get_axis(5)
        if rt_axis > TRIGGER_THRESHOLD:
            if not self.shooting:
                self.shoot(projectiles)
                debug_print(debug_shooting, "Shoot (RT) input detected.")
            self.shooting = True
        else:
            self.shooting = False
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.colour, (int(self.pos.x), int(self.pos.y), PLAYER_WIDTH, PLAYER_HEIGHT))
        centre =  self.pos + pygame.Vector2(PLAYER_WIDTH/2, PLAYER_HEIGHT/2)
        aim_endpoint = centre + self.aim_direction * 48
        pygame.draw.line(screen, (255,255,255), centre, aim_endpoint, 4)
    
    def draw_name(self, screen):
        player_text = player_font.render(f"PLAYER {self.player_num}", True, self.colour)
        text_x = self.pos.x + (PLAYER_WIDTH - player_text.get_width()) / 2
        text_y = self.pos.y - player_text.get_height() - 10
        screen.blit(player_text, (text_x, text_y))
    
    def get_pip_fill(self, pip_index):
        pip_health = (self.health/self.max_health)*10
        pip_fill = max(0, min(1, pip_health - pip_index))
        return pip_fill
    
    def get_health_colour(self):
        health_percentage = (self.health / self.max_health) * 100
        if health_percentage >= 70:
            return (90, 197, 79)
        elif health_percentage >= 50:
            return (229, 211, 74)
        elif health_percentage >= 30:
            return (229, 138, 53)
        else:
            return (217, 71, 71)
    
    def draw_floating_health_bar(self, screen):
        health_colour = self.get_health_colour()
        bar_width = 64
        bar_height = 7
        pip_gap = 2
        pip_width = (bar_width - (9*pip_gap))/10
        bar_x = self.pos.x + (PLAYER_WIDTH - bar_width) / 2
        bar_y = self.pos.y - player_font.get_height() + 12
        for i in range(10):
            fill = self.get_pip_fill(i)
            pip_x = bar_x + i * (pip_width + pip_gap)
            pygame.draw.rect(screen,(60, 60, 60), (pip_x, bar_y, pip_width, bar_height))
            if fill > 0:
                pygame.draw.rect(screen,health_colour,(pip_x, bar_y, pip_width * fill, bar_height))
    
    def draw_psup(self, screen):
        panel_width = 250
        panel_height = 75
        padding = 10
        panel_y = screen_height - panel_height - padding
        if self.player_num == 1:
            panel_x = padding
        else:
            panel_x = screen_width - panel_width - padding
        name_text = player_font.render(f"PLAYER {self.player_num}",True,self.colour)
        health_text = player_font.render(f"{int(self.health)} / {self.max_health} HP",True,(255, 255, 255))
        if self.player_num == 1:
            screen.blit(name_text, (panel_x + 12, panel_y + 5))
            screen.blit(health_text,(panel_x + panel_width - health_text.get_width() - 12, panel_y + 5))
        else:
            screen.blit(health_text, (panel_x + 12, panel_y + 5))
            screen.blit(name_text,(panel_x + panel_width - name_text.get_width() - 12, panel_y + 5))
        bar_width = panel_width - 24
        bar_height = 16
        pip_gap = 3
        pip_width = (bar_width - (9 * pip_gap)) / 10
        bar_x = panel_x + 12
        bar_y = panel_y + 43
        health_colour = self.get_health_colour()
        for i in range(10):
            fill = self.get_pip_fill(i)
            pip_x = bar_x + i * (pip_width + pip_gap)
            pygame.draw.rect(screen,(60, 60, 60),(pip_x, bar_y, pip_width, bar_height))
            if fill > 0:
                pygame.draw.rect(screen,health_colour,(pip_x, bar_y, pip_width * fill, bar_height))

    def shoot(self, projectiles):
        centre = self.pos + pygame.Vector2(PLAYER_WIDTH/2, PLAYER_HEIGHT/2)
        projectile = Projectile(centre, self.aim_direction, self.colour)
        projectiles.append(projectile)

class Enemy:
    def __init__(self, x, y, width, height, colour, inaccuracy=12):
        self.colour = colour
        self.pos = pygame.Vector2(x, y)
        self.width = width
        self.height = height
        self.speed = 200
        self.max_health = 100
        self.health = self.max_health
        self.alive = True
        self.preferred_distance = 250 #px
        self.fire_interval = random.uniform(0.5, 1.5) #s between shots
        self.fire_elapsed = 0 #s since shot
        self.projectile_speed = 250
        self.projectile_damage = 10
        self.movement_direction = pygame.Vector2(0, 0)
        self.inaccuracy = inaccuracy
        self.aim_direction = pygame.Vector2(1, 0)
    
    def update(self, dt, players, projectiles):
        #find nearest
        closest_player = None
        closest_distance = float("inf") #enemy will always want to find a player
        enemy_centre = self.pos + pygame.Vector2(self.width / 2, self.height / 2)
        for player in players:
            if not player.alive:
                continue
            player_centre = player.pos + pygame.Vector2(PLAYER_WIDTH / 2, PLAYER_HEIGHT / 2)
            distance = enemy_centre.distance_to(player_centre)
            if distance < closest_distance:
                closest_player = player
                closest_distance = distance

        #target player
        if closest_player is not None:
            player_centre = closest_player.pos + pygame.Vector2(PLAYER_WIDTH / 2, PLAYER_HEIGHT / 2)
            movement_direction = player_centre - enemy_centre
            if movement_direction.length_squared() > 0:
                self.movement_direction = movement_direction.normalize()
            #aim towards player
            direction = player_centre - enemy_centre
            if direction.length_squared() > 0:
                self.aim_direction = direction.normalize()
            
            #firing
            self.fire_elapsed += dt
            if self.fire_elapsed >= self.fire_interval:
                enemy_centre = self.pos + pygame.Vector2(self.width/2, self.height/2)
                shot_direction = self.aim_direction.rotate(random.uniform(-self.inaccuracy, self.inaccuracy))
                projectiles.append(Projectile(enemy_centre, shot_direction, self.colour, speed=self.projectile_speed, damage=self.projectile_damage, owner="enemy"))
                self.fire_elapsed = 0
            
            #move to preferred range
            if closest_distance > self.preferred_distance + 10:
                self.pos += self.movement_direction * self.speed * dt
            elif closest_distance < self.preferred_distance - 10:
                self.pos -= self.movement_direction * self.speed * dt
            if self.pos.x < 0:
                self.pos.x = 0
                debug_print(debug_movement, f"Enemy attempted to exceed negative X screen boundary.")
            if self.pos.x > screen_width - self.width:
                self.pos.x = screen_width - self.width
                debug_print(debug_movement, f"Enemy attempted to exceed positive X screen boundary.")
            if self.pos.y < 0:
                self.pos.y = 0
                debug_print(debug_movement, f"Enemy attempted to exceed positive Y screen boundary.")
            if self.pos.y > screen_height - self.height:
                self.pos.y = screen_height - self.height
                debug_print(debug_movement, f"Enemy attempted to exceed negative Y screen boundary.")
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.colour, (int(self.pos.x), int(self.pos.y), self.width, self.height))
        centre =  self.pos + pygame.Vector2(self.width/2, self.height/2)
        aim_endpoint = centre + self.aim_direction * (self.width * 0.75)
        pygame.draw.line(screen, (255,255,255), centre, aim_endpoint, 4)
    
    def draw_health_bar(self, screen):
        bar_width = self.width
        bar_height = 6
        bar_x = self.pos.x
        bar_y = self.pos.y - 12
        health_percentage = self.health / self.max_health
        if health_percentage >= 0.7:
            health_colour = (90, 197, 79)
        elif health_percentage >= 0.5:
            health_colour = (229, 211, 74)
        elif health_percentage >= 0.3:
            health_colour = (229, 138, 53)
        else:
            health_colour = (217, 71, 71)
        pygame.draw.rect(screen, (60, 60, 60),
                        (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, health_colour,
                        (bar_x, bar_y, bar_width * health_percentage, bar_height))

class Objective:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.width = OBJECTIVE_WIDTH
        self.height = OBJECTIVE_HEIGHT
        self.colour = (220, 220, 80)
        self.max_health = 500
        self.health = self.max_health
        self.alive = True
        self.spawn_req = random.randint(3, 5)
        self.name = random.choice(["Pension Machine", "Denture Polisher", "Fountain of Un-Youth", "Biscuit Tin Production Line", "Wrinkle Generator", "Box of Hip Bones", "Arthritis & Co. Scrabble Stand", "Arthritis & Co. Bingo Hall"])
    
    def draw(self, screen):
            pygame.draw.rect(screen, self.colour, (int(self.pos.x), int(self.pos.y), self.width, self.height))
            centre =  self.pos + pygame.Vector2(self.width/2, self.height/2)
    
    def draw_health_bar(self, screen):
            bar_width = self.width
            bar_height = 6
            bar_x = self.pos.x
            bar_y = self.pos.y - 12
            health_percentage = self.health / self.max_health
            health_colour = (170, 170, 80)
            pygame.draw.rect(screen, (60, 60, 60),
                            (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(screen, health_colour,
                            (bar_x, bar_y, bar_width * health_percentage, bar_height))
    

#variables
active_controllers = {}

#initialisation
start_game()
pygame.init()
wave_font = pygame.font.Font("fonts/PixelifySans-Bold.ttf", 48)
sub_wave_font = pygame.font.Font("fonts/PixelifySans-SemiBold.ttf", 36)
player_font = pygame.font.Font("fonts/PixelifySans-Medium.ttf", 20)
menu_title_font = pygame.font.Font("fonts/Bungee-Regular.ttf", 96)
menu_option_font = pygame.font.Font("fonts/PixelifySans-SemiBold.ttf", 40)
objective_font = pygame.font.Font("fonts/PixelifySans-Regular.ttf", 36)
objective_detail_font = pygame.font.Font("fonts/PixelifySans-Regular.ttf", 24)

icon = pygame.image.load("fightnans.ico")
pygame.display.set_icon(icon)
pygame.joystick.init()

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("FIGHTNANS Prototype v0.3")
clock = pygame.time.Clock()
running = True
game_state = MENU
menu_options = ["PLAY", "QUIT"]
selected_menu_option = 0
game_over_options = ["RESTART", "MAIN MENU"]
selected_game_over_option = 0
mission_complete_options = ["RESTART", "MAIN MENU"]
selected_mission_complete_option = 0

#game loop
while running:
    #events
    for event in pygame.event.get():
        #quit event
        if event.type == pygame.QUIT:
            running = False
        #controller connected event
        if event.type == pygame.JOYDEVICEADDED:
            joystick = pygame.joystick.Joystick(event.device_index)
            instance_id = joystick.get_instance_id()
            active_controllers[instance_id] = joystick
            debug_print(debug_controller_connections, f"------------------------------ \nController Connected. \nController ID: {instance_id} \nController Name: {joystick.get_name()} \nController Index: {event.device_index} \nController Axes: {joystick.get_numaxes()} \nActive Controllers: {len(list(active_controllers.keys()))} ({list(active_controllers.keys())})")
            for player in players:
                if player.joystick_id is None:
                    player.joystick_id = instance_id
                    debug_print(debug_controller_connections, f"Controller {joystick.get_name()} (ID {instance_id}) assigned to player.")
                    if debug_controller_connections:
                        for i, player in enumerate(players):
                            print(f"Player {i + 1}: Controller {player.joystick_id}")
                    break
        #controller disconnected event
        if event.type == pygame.JOYDEVICEREMOVED:
            instance_id = event.instance_id
            disconnected_joystick = active_controllers.get(instance_id)
            controller_name = disconnected_joystick.get_name() if disconnected_joystick else "Unknown Controller"
            debug_print(debug_controller_connections, f"------------------------------ \nController Disconnected. \nController ID: {instance_id} \nController Name: {controller_name}")
            if instance_id in active_controllers:
                del active_controllers[instance_id]
            for player in players:
                if player.joystick_id == instance_id:
                    player.joystick_id = None
                    debug_print(debug_controller_connections, f"Controller {controller_name} (ID {instance_id}) unassigned from player.")
                    if debug_controller_connections:
                        print(f"Active Controllers: {len(list(active_controllers.keys()))} ({list(active_controllers.keys())})")
                        for i, player in enumerate(players):
                            print(f"Player {i + 1}: Controller {player.joystick_id}")
                    break
        #main menu controls
        if game_state == MENU:
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    if selected_menu_option == 0:
                        start_game()
                        game_state = PLAYING
                    elif selected_menu_option == 1:
                        running = False
            if event.type == pygame.JOYHATMOTION:
                if event.value[1] == 1:
                    selected_menu_option = (selected_menu_option - 1) % len(menu_options)
                elif event.value[1] == -1:
                    selected_menu_option = (selected_menu_option + 1) % len(menu_options)
        #game over menu controls
        if game_state == GAME_OVER:
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    if selected_game_over_option == 0:
                        start_game()
                        game_state = PLAYING
                    elif selected_game_over_option == 1:
                        game_state = MENU
            if event.type == pygame.JOYHATMOTION:
                if event.value[1] == 1:
                    selected_game_over_option = (selected_game_over_option - 1) % len(game_over_options)
                elif event.value[1] == -1:
                    selected_game_over_option = (selected_game_over_option + 1) % len(game_over_options)
        #mission complete menu controls
        if game_state == COMPLETE:
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    if selected_mission_complete_option == 0:
                        start_game()
                        game_state = PLAYING
                    elif selected_mission_complete_option == 1:
                        game_state = MENU
            if event.type == pygame.JOYHATMOTION:
                if event.value[1] == 1:
                    selected_mission_complete_option = (selected_mission_complete_option - 1) % len(mission_complete_options)
                elif event.value[1] == -1:
                    selected_mission_complete_option = (selected_mission_complete_option + 1) % len(mission_complete_options)
    
    dt = clock.tick(fps) /1000
    screen.fill(BG_COLOUR)
    
    #draw menu
    if game_state == MENU:
        draw_menu(screen)
    
    if game_state == COMPLETE:
        draw_mission_complete(screen)
    
    elif game_state == PLAYING:
        #update + draw player
        for player in players:
            if player.alive:
                player.update(active_controllers, dt, projectiles, enemies, players)
                player.draw(screen)
        
        #update enemies
        for enemy in enemies:
            if enemy.alive:
                enemy.update(dt, players, projectiles)
        enemies = [enemy for enemy in enemies if enemy.alive]
        
        #update projectiles
        for projectile in projectiles:
            projectile.update(dt)
            if projectile.owner == "player":
                #player-enemy hits
                for enemy in enemies:
                    if not enemy.alive:
                        continue
                    #collision detection
                    if projectile.check_collision(enemy):
                        projectile.alive = False
                        enemy.health -= projectile.damage
                        debug_print(debug_combat, f"Player projectile collided with enemy. Enemy health reduced by {projectile.damage}. Enemy health: {enemy.health}.")
                        if enemy.health <= 0:
                            enemy.health = 0
                            enemy.alive = False
                            debug_print(debug_combat, "Enemy killed.")
                        break
                #player-objective hits
                if projectile.alive:
                    for objective in objective_objects:
                        if not objective.alive or current_wave.wave_number < objective.spawn_req:
                            continue
                        #collision detection
                        if projectile.check_collision(objective):
                            projectile.alive = False
                            objective.health -= projectile.damage
                            debug_print(debug_combat, f"Player projectile collided with objective. Objective health reduced by {projectile.damage}. Objective health: {objective.health}.")
                            if objective.health <= 0:
                                objective.health = 0
                                objective.alive = False
                                debug_print(debug_combat, "Objective killed.")
                            break
            #enemy-player hits
            elif projectile.owner == "enemy":
                for player in players:
                    if not player.alive:
                        continue
                    #collision detection
                    if projectile.check_collision(player):
                        projectile.alive = False
                        player.health -= projectile.damage
                        debug_print(debug_combat, f"Enemy projectile collided with player. Player health reduced by {projectile.damage}. Player health: {player.health}.")
                        if player.health <= 0:
                            player.health = 0
                            player.alive = False
                            debug_print(debug_combat, "Player killed.")
                        break
        
        #draw enemies and projectiles
        for enemy in enemies:
            enemy.draw(screen)
            if enemy_health_draw == True:
                enemy.draw_health_bar(screen)
        for projectile in projectiles:
            projectile.draw(screen)
        
        #draw objectives
        for object in objective_objects:
            if object.alive:
                if current_wave.wave_number >= object.spawn_req:
                    object.draw(screen)
                    object.draw_health_bar(screen)
        
        #draw psup and health bar
        for player in players:
            if player.alive:
                player.draw_name(screen)
                player.draw_floating_health_bar(screen)
            player.draw_psup(screen)
        
        #clear dead objects
        enemies = [enemy for enemy in enemies if enemy.alive]
        projectiles = [projectile for projectile in projectiles if projectile.alive]
        
        #create wave
        current_wave.update(dt, enemies)
        
        if current_wave.wait_complete():
            if start_intermission:
                current_wave.start()
                start_intermission = False
            else:
                next_wave_number = current_wave.wave_number + 1
                next_wave_size = current_wave.enemies_per_wave + 2
                next_spawn_interval = current_wave.spawn_interval
                current_wave = Wave(next_wave_number, next_wave_size, next_spawn_interval)
        
        #draw wave text
        if not current_wave.complete(enemies):
            wave_text = wave_font.render(f"WAVE {current_wave.wave_number}", True, (255, 255, 255))
        else:
            wave_text = wave_font.render(f"WAVE {current_wave.wave_number} COMPLETE", True, (255, 255, 255))
        wave_x = (screen_width - wave_text.get_width()) / 2
        screen.blit(wave_text, (wave_x, 20))
        #draw wait/enemies text
        if current_wave.wait_active:
            intermission_text = "STARTING IN" if start_intermission else "NEXT WAVE IN"
            wait_text = sub_wave_font.render(f"{intermission_text} {current_wave.wait_duration-current_wave.wait_elapsed:.1f}", True, (200, 200, 200))
            wait_x = (screen_width - wait_text.get_width()) / 2
            screen.blit(wait_text, (wait_x, 60))
        else:
            enemies_text = sub_wave_font.render(f"{len(enemies) + (current_wave.enemies_per_wave - current_wave.enemies_spawned)}/{current_wave.enemies_per_wave} ENEMIES REMAINING", True, (200, 200, 200))
            enemies_x = (screen_width - enemies_text.get_width()) / 2
            screen.blit(enemies_text, (enemies_x, 60))
        
        #draw objective text
        for object in objective_objects:
            objective_text = objective_font.render(f"OBJECTIVE(S):", True, (255, 255, 255))
            if current_wave.wave_number < object.spawn_req:
                objective_detail = objective_detail_font.render(f"-Survive until wave {object.spawn_req}", True, (255, 255, 255))
            else:
                objective_detail = objective_detail_font.render(f"-Destroy the {objective.name} ({object.health}/{object.max_health})", True, (255, 255, 255))
            screen.blit(objective_text, (20, 20))
            screen.blit(objective_detail, (20, 70))
        
        for object in objective_objects:
            if not object.alive:
                game_state = COMPLETE
        
        if not any(player.alive for player in players):
            game_state = GAME_OVER
    elif game_state == GAME_OVER:
        draw_game_over(screen)
    
    pygame.display.update()

pygame.quit()
sys.exit()