from server.external import McLumk_Wheel_Sports as bot

DEFAULT_SPEED = 5

def is_known_move(move_direction_request: str) -> bool:
    return move_direction_request in ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]

def move(command_received: dict) -> None:
    command_received_keys = list(command_received.keys())
    if len(command_received_keys) == 0:
        return

    command_key = command_received_keys[0] 
    if command_key == "released":
        bot.stop_robot()
        return

    if command_key != "pressed":
        return

    pressed_key = command_received[command_key]
    if not is_known_move(pressed_key):
        return

    bot.stop_robot()
    if pressed_key == "ArrowUp":
        bot.move_forward(DEFAULT_SPEED)
    
    elif pressed_key == "ArrowDown":
        bot.move_backward(DEFAULT_SPEED)

    elif pressed_key == "ArrowLeft":
        bot.rotate_left(DEFAULT_SPEED)

    else:
        bot.rotate_right(DEFAULT_SPEED)
