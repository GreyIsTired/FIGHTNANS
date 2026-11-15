#imports
import pygame
import sys
import random

#constants
BG_COLOUR = (35, 35, 40)
DEADZONE = 0.15
TRIGGER_THRESHOLD = 0.5
PLAYER_WIDTH = 64 #px
PLAYER_HEIGHT = 64 #px
ENEMY_WIDTH = 64 #px
ENEMY_HEIGHT = 64 #px
ENEMY_STOPPING_DISTANCE = 64 #px

#configuration variables
screen_width = 1280
screen_height = 720
fps = 60
gamemode = "multiplayer"
debug_controller_connections = False
debug_movement = False
debug_movement_vectors = False
debug_aiming = False
debug_aiming_vectors = False
debug_shooting = False
debug_combat = True
debug_enemies = False

#functions
def debug_print(category, message):
    if category:
        print(message)

#classes
class Projectile:
    def __init__(self, pos, direction, speed=600, owner="player"):
        self.pos = pygame.Vector2(pos)
        self.direction = direction.copy()
        self.speed = speed
        self.owner = owner
        self.alive = True
        self.damage = 25
        self.radius = 10
        self.colour = (255, 220, 100)
    
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
    def __init__(self, x, y, colour):
        self.joystick_id = None
        self.colour = colour
        self.pos = pygame.Vector2(x, y)
        self.health = 100
        self.alive = True
        self.speed = 300 #px/s
        self.aim_direction = pygame.Vector2(1,0)
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
            movement = pygame.Vector2(0,0)
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
    
    def shoot(self, projectiles):
        centre = self.pos + pygame.Vector2(PLAYER_WIDTH/2, PLAYER_HEIGHT/2)
        projectile = Projectile(centre, self.aim_direction)
        projectiles.append(projectile)

class Enemy:
    def __init__(self, x, y, width, height):
        self.colour = (180, 70, 70)
        self.pos = pygame.Vector2(x, y)
        self.width = width
        self.height = height
        self.speed = 200 #px/s
        self.health = ((self.width+self.height) * 0.78125) #100 at 64x64
        self.alive = True
        self.preferred_distance = 250 #px
        self.fire_interval = random.uniform(0.5, 1.5) #s between shots
        self.fire_elapsed = 0 #s since shot
        self.projectile_speed = 350
        self.aim_direction = pygame.Vector2(1, 0)
        
    
    def update(self, dt, players, projectiles):
        #find nearest
        closest_player = None
        closest_distance = float("inf") #enemy will always want to find a player
        enemy_centre = self.pos + pygame.Vector2(ENEMY_WIDTH / 2, ENEMY_HEIGHT / 2)
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
            if closest_distance > ENEMY_STOPPING_DISTANCE:
                player_centre = closest_player.pos + pygame.Vector2(PLAYER_WIDTH / 2, PLAYER_HEIGHT / 2)
                direction = player_centre - enemy_centre
                if direction.length_squared() > 0:
                    self.aim_direction = direction.normalize()
            
            #firing
            self.fire_elapsed += dt
            if self.fire_elapsed >= self.fire_interval:
                enemy_centre = self.pos + pygame.Vector2(self.width/2, self.height/2)
                projectiles.append(Projectile(enemy_centre, self.aim_direction, self.projectile_speed, "enemy"))
                self.fire_elapsed = 0
            
            #move to preferred range
            if closest_distance > self.preferred_distance + 10:
                self.pos += self.aim_direction * self.speed * dt
            elif closest_distance < self.preferred_distance - 10:
                self.pos -= self.aim_direction * self.speed * dt
            if self.pos.x < 0:
                self.pos.x = 0
                debug_print(debug_movement, f"Enemy attempted to exceed negative X screen boundary.")
            if self.pos.x > screen_width - ENEMY_WIDTH:
                self.pos.x = screen_width - ENEMY_WIDTH
                debug_print(debug_movement, f"Enemy attempted to exceed positive X screen boundary.")
            if self.pos.y < 0:
                self.pos.y = 0
                debug_print(debug_movement, f"Enemy attempted to exceed positive Y screen boundary.")
            if self.pos.y > screen_height - ENEMY_HEIGHT:
                self.pos.y = screen_height - ENEMY_HEIGHT
                debug_print(debug_movement, f"Enemy attempted to exceed negative Y screen boundary.")
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.colour, (int(self.pos.x), int(self.pos.y), ENEMY_WIDTH, ENEMY_HEIGHT))
        centre =  self.pos + pygame.Vector2(ENEMY_WIDTH/2, ENEMY_HEIGHT/2)
        aim_endpoint = centre + self.aim_direction * 48
        pygame.draw.line(screen, (255,255,255), centre, aim_endpoint, 4)

#variables
projectiles = []
if gamemode == "singleplayer":
    players = [Player(screen_width*0.33, screen_height*0.5, (70, 180, 70))]
else:
    players = [Player(screen_width*0.33, screen_height*0.5, (70, 180, 70)), Player(screen_width*0.67, screen_height*0.5, (70, 70, 180))]
enemies = [Enemy(screen_width*0.5, screen_height*0.66, ENEMY_WIDTH, ENEMY_HEIGHT), Enemy(screen_width*0.5, screen_height*0.33, ENEMY_WIDTH, ENEMY_HEIGHT)]
active_controllers = {}

#initialisation
pygame.init()
pygame.joystick.init()

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("FIGHTNANS Prototype")
clock = pygame.time.Clock()
running = True

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
            debug_print(debug_controller_connections, f"------------------------------ \nController Disconnected. \nController ID: {instance_id} \nController Name: {joystick.get_name()}")
            if instance_id in active_controllers:
                del active_controllers[instance_id]
            for player in players:
                if player.joystick_id == instance_id:
                    player.joystick_id = None
                    debug_print(debug_controller_connections, f"Controller {joystick.get_name()} (ID {instance_id}) unassigned from player.")
                    if debug_controller_connections:
                        print(f"Active Controllers: {len(list(active_controllers.keys()))} ({list(active_controllers.keys())})")
                        for i, player in enumerate(players):
                            print(f"Player {i + 1}: Controller {player.joystick_id}")
                    break
    
    dt = clock.tick(fps) /1000
    screen.fill(BG_COLOUR)
    
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
        elif projectile.owner == "enemy":
            for player in players:
                if not player.alive:
                    continue
                if projectile.check_collision(player):
                    projectile.alive = False
                    player.health -= projectile.damage
                    debug_print(debug_combat, f"Enemy projectile collided with player. Player health reduced by {projectile.damage}. Player health: {player.health}.")
                    if player.health <= 0:
                        player.health = 0
                        player.alive = False
                        debug_print(debug_combat, "Player killed.")
                
    #clear dead objects
    enemies = [enemy for enemy in enemies if enemy.alive]
    projectiles = [projectile for projectile in projectiles if projectile.alive]
    
    #draw enemies and projectiles
    for enemy in enemies:
        enemy.draw(screen)
    for projectile in projectiles:
        projectile.draw(screen)
    
    pygame.display.update()

pygame.quit()
sys.exit()