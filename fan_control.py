#!/usr/bin/env python3
import time
from hailo_platform import Device
from gpiozero import PWMOutputDevice

# Configuration du GPIO 18 pour le contrÃ´le PWM
fan = PWMOutputDevice(18)

# Fonction pour obtenir la tempÃ©rature du module Hailo
def get_hailo_temperature():
    target = Device()
    temp = target.control.get_chip_temperature().ts0_temperature
    return temp

# Fonction pour ajuster la vitesse du ventilateur en fonction de la tempÃ©rature
def adjust_fan_speed(temp):
    if temp < 35:
        speed = 0.0  # Ventilateur Ã©teint
    elif 35 <= temp < 45:
        speed = 0.4
    elif 45 <= temp < 55:
        speed = 0.5
    elif 55 <= temp < 60:
        speed = 0.6
    elif 60 <= temp < 65:
        speed = 0.75
    else:
        speed = 1.0

    fan.value = speed
    print(f"Température Hailo : {temp:.2f}°C, Vitesse ventilateur : {speed*100:.0f}%")

try:
    while True:
        temperature = get_hailo_temperature()
        adjust_fan_speed(temperature)
        time.sleep(5)  # VÃ©rifie la tempÃ©rature toutes les 5 secondes
except KeyboardInterrupt:
    print("Arrêt du script par l'utilisateur.")
finally:
    fan.close()
