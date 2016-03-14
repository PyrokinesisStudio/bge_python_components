from bge import logic, events
from component_system import update_scene
from time import clock

accumulator = 0.0
dt = 1 / logic.getLogicTicRate()
last_time = clock()


running = True
while running:
    now = clock()
    elapsed = now - last_time
    last_time = now

    accumulator += elapsed
    while accumulator > dt:
        accumulator -= dt
        logic.NextFrame()

        for scene in logic.getSceneList():
            update_scene(scene)

        if logic.getExitKey() in logic.keyboard.active_events:
            running = False
            break
