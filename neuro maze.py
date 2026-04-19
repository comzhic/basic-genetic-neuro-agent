import pygame
import random
import math
import time

# --- ИНИЦИАЛИЗАЦИЯ ---
pygame.init()

# Пытаемся получить реальный размер экрана устройства
try:
    monitor_info = pygame.display.Info()
    screen_w = monitor_info.current_w
    screen_h = monitor_info.current_h
except:
    screen_w, screen_h = 1440, 600 # Запасной вариант

# Оригинальные размеры нашего лабиринта
WIDTH, HEIGHT = 1440, 600

# Настройка экрана с автоматическим масштабированием (важно для телефона!)
# SCALED растянет наши 1440x600 на весь экран телефона без искажения логики
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.FULLSCREEN)

# Исправляем проблему со шрифтами (на телефонах часто нет "Consolas")
try:
    font = pygame.font.SysFont("Arial", 20, bold=True)
except:
    font = pygame.font.SysFont(None, 24) # Стандартный системный шрифт
# --- НАСТРОЙКИ ЭКРАНА ---
info = pygame.display.Info()
if info.current_w < WIDTH:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
POP_SIZE = 50
LIFESPAN = 900  # Оптимально для такой длины
mutation_rate = 0.15
game_speed = 120
dot_velocity = 5

WHITE, BLACK, RED, BLUE, GREEN = (255, 255, 255), (20, 20, 20), (255, 50, 50), (0, 100, 255), (50, 255, 50)

# --- ПАНОРАМНЫЙ ЛАБИРИНТ ---


WALLS = [
    # Внешний контур
    pygame.Rect(0, 0, 1440, 15), pygame.Rect(0, 585, 1440, 15),
    pygame.Rect(0, 0, 15, 600), pygame.Rect(1425, 0, 15, 600),

    # === СТАРТОВАЯ ЗОНА (теперь открыта!) ===
    # Старт находится в кармане внизу слева
    pygame.Rect(15, 380, 120, 15),  # Потолок СЛЕВА над стартом
    pygame.Rect(230, 380, 15, 220),  # Вертикальная стена СПРАВА от старта
    # Выход наверх между x=135 и x=230 СВОБОДЕН!

    # === ПЕРВЫЙ КОРИДОР И ПОВОРОТ ===
    pygame.Rect(135, 150, 15, 230),  # Левая стенка шахты наверх
    pygame.Rect(230, 150, 15, 120),  # Правая стенка шахты наверх
    pygame.Rect(135, 150, 200, 15),  # Потолок, который заставляет повернуть направо

    # === ЦЕНТРАЛЬНЫЕ ЗИГЗАГИ ===
    pygame.Rect(335, 150, 15, 250),  # Спуск вниз
    pygame.Rect(335, 400, 200, 15),  # Полка снизу
    pygame.Rect(535, 0, 15, 300),  # Стена с потолка
    pygame.Rect(535, 300, 150, 15),  # Т-образный перекресток

    # === ПУТЬ К СИНЕМУ КРУГУ ===
    pygame.Rect(750, 150, 15, 450),  # Вертикальная стена, разделяющая зоны
    pygame.Rect(750, 150, 300, 15),  # Потолок длинного коридора
    pygame.Rect(950, 150, 15, 250),  # Стена прямо перед финишем
    pygame.Rect(950, 400, 300, 15),  # Пол под синим кругом
    pygame.Rect(1250, 200, 175, 15),  # Полка за финишем
]

START_POS = [80, 500]
GOAL = pygame.Rect(815, 250, 90, 90)  # Синий финиш


class Dot:
    def __init__(self, weights=None):
        self.reset()
        # Теперь 6 весов: 5 для стен + 1 для направления к цели
        self.weights = weights if weights else [random.uniform(-1, 1) for _ in range(6)]
        self.path_history = []

    def reset(self):
        self.pos = list(START_POS)
        self.angle = -math.pi / 2
        self.dead = False
        self.reached_goal = False
        self.fitness = 0
        self.distance_traveled = 0
        self.path_history = []

    def get_inputs(self):
        # 1-5: Датчики стен
        sensor_angles = [-math.pi / 2, -math.pi / 4, 0, math.pi / 4, math.pi / 2]
        inputs = []
        for a in sensor_angles:
            ray_angle = self.angle + a
            dist = 0
            while dist < 150:
                dist += 6
                tx, ty = self.pos[0] + math.cos(ray_angle) * dist, self.pos[1] + math.sin(ray_angle) * dist
                hit = any(w.collidepoint(tx, ty) for w in WALLS)
                if hit or tx < 0 or tx > WIDTH or ty < 0 or ty > HEIGHT: break
            inputs.append(dist / 150.0)

        # 6: Датчик направления на цель (Компас)
        angle_to_goal = math.atan2(GOAL.centery - self.pos[1], GOAL.centerx - self.pos[0])
        # Разница между тем, куда смотрим и где цель (нормализуем от -1 до 1)
        diff = (angle_to_goal - self.angle + math.pi) % (2 * math.pi) - math.pi
        inputs.append(diff / math.pi)

        return inputs

    def update(self, vel):
        if self.dead or self.reached_goal: return

        inputs = self.get_inputs()
        # Нейронная сеть: сумма (сигнал * вес)
        decision = sum(inputs[i] * self.weights[i] for i in range(6))

        self.angle += decision * 0.25  # Чуть более резкие повороты
        self.pos[0] += math.cos(self.angle) * vel
        self.pos[1] += math.sin(self.angle) * vel
        self.distance_traveled += vel
        self.path_history.append(list(self.pos))

        if any(w.collidepoint(self.pos) for w in WALLS): self.dead = True
        if GOAL.collidepoint(self.pos): self.reached_goal = True

    def calculate_fitness(self):
        dist_to_goal = math.sqrt((self.pos[0] - GOAL.centerx) ** 2 + (self.pos[1] - GOAL.centery) ** 2)
        # Если нашли путь — фитнес огромный, если нет — тянемся к финишу
        self.fitness = (1000.0 / (dist_to_goal + 1)) ** 2
        if self.reached_goal: self.fitness *= 5
        if self.dead: self.fitness *= 0.4


def mutate(weights, rate):
    # Теперь мутация может быть сильнее (отклонение от пути)
    return [w if random.random() > rate else w + random.uniform(-0.6, 0.6) for w in weights]


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont("Consolas", 18, bold=True)
clock = pygame.time.Clock()

dots = [Dot() for _ in range(POP_SIZE)]
best_path = []
gen = 1
step = 0

running = True
while running:
    screen.fill(WHITE)

    # 1. ОБЯЗАТЕЛЬНАЯ ОБРАБОТКА СОБЫТИЙ (чтобы не было серого экрана)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS]: game_speed += 100
            if event.key in [pygame.K_MINUS, pygame.K_KP_MINUS]: game_speed = max(10, game_speed - 100)

    # 2. РИСУЕМ МИР
    for wall in WALLS:
        pygame.draw.rect(screen, BLACK, wall)
    pygame.draw.rect(screen, BLUE, GOAL)

    if best_path:
        if len(best_path) > 1:
            pygame.draw.lines(screen, (220, 240, 255), False, best_path, 2)

    # 3. ОБНОВЛЯЕМ ТОЧКИ
    alive = sum(1 for d in dots if not d.dead and not d.reached_goal)
    for dot in dots:
        dot.update(dot_velocity)
        color = RED if not dot.dead else (230, 230, 230)
        if dot.reached_goal: color = GREEN
        pygame.draw.circle(screen, color, (int(dot.pos[0]), int(dot.pos[1])), 4)

    # 4. ИНФО-ПАНЕЛЬ
    pygame.draw.rect(screen, (240, 240, 240), (10, 10, 480, 40))
    info_text = f"GEN: {gen} | ALIVE: {alive} | FPS: {game_speed}"
    info = font.render(info_text, True, BLACK)
    screen.blit(info, (20, 20))

    # 5. НОВОЕ ПОКОЛЕНИЕ
    step += 1
    if alive == 0 or step >= LIFESPAN:
        for d in dots: d.calculate_fitness()
        dots.sort(key=lambda d: d.fitness, reverse=True)
        best_path = dots[0].path_history

        new_dots = []
        for i in range(5): new_dots.append(Dot(weights=dots[i].weights))
        while len(new_dots) < int(POP_SIZE * 0.9):
            parent = random.choice(dots[:15])
            new_dots.append(Dot(weights=mutate(parent.weights, mutation_rate)))
        while len(new_dots) < POP_SIZE:
            new_dots.append(Dot())

        dots = new_dots
        gen += 1
        step = 0

    # 6. ФИНАЛЬНЫЙ ВЫВОД (БЕЗ SLEEP!)
    pygame.display.flip()
    clock.tick(game_speed)

pygame.quit()
time.sleep(9999)


