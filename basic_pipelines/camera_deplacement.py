#!/usr/bin/env python3
# camera_deplacement.py
# -*- coding: utf-8 -*-

import time
import board
import busio
from adafruit_pca9685 import PCA9685

TRACK_OBJECTS = ["person", "cat"]  # Ajoutez les objets que vous souhaitez suivre

# ---------------------------------------------------------------------------
# 1) Classe : ServoController
# ---------------------------------------------------------------------------
class ServoController:
    """
    Pilotage d'un servo via PCA9685.
    - channel : canal PCA9685 (0..15)
    - freq : frÃ©quence PWM (50Hz pour servos)
    - i2c_address : adresse I2C PCA9685 (0x40 par dÃ©faut)
    - servo_min_us / servo_max_us : impulsion min et max (Âµs)
    - max_angle : amplitude max (par ex. 180Â° ou 270Â°)
    """
    def __init__(
        self, 
        channel=0, 
        freq=50, 
        i2c_address=0x40, 
        servo_min_us=500, 
        servo_max_us=2500, 
        max_angle=180
    ):
        # Initialisation du bus I2C + PCA9685
        i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(i2c, address=i2c_address)
        self.pca.frequency = freq

        self.channel = channel
        self.servo_min_us = servo_min_us
        self.servo_max_us = servo_max_us
        self.max_angle = max_angle

        # Angle actuel (on suppose qu'on dÃ©marre "au milieu")
        self.current_angle = max_angle / 2.0
        self.set_servo_angle(self.current_angle)

    def _us_to_duty_cycle(self, pulse_us):
        """Convertit une impulsion en Âµs vers le duty cycle 16 bits (0..65535)."""
        period_us = 1_000_000 // self.pca.frequency  # ex: 20_000 Âµs @ 50Hz
        duty_cycle = int((pulse_us / period_us) * 65535)
        return max(0, min(65535, duty_cycle))

    def set_servo_angle(self, angle_deg):
        """
        Fixe l'angle du servo. On le borne entre [0, max_angle].
        """
        angle_clamped = max(0, min(self.max_angle, angle_deg))
        self.current_angle = angle_clamped

        span_us = self.servo_max_us - self.servo_min_us
        pulse_us = self.servo_min_us + (span_us * (angle_clamped / float(self.max_angle)))

        self.pca.channels[self.channel].duty_cycle = self._us_to_duty_cycle(pulse_us)

    def cleanup(self):
        """Coupe la PWM et libÃ¨re le PCA."""
        self.pca.channels[self.channel].duty_cycle = 0
        self.pca.deinit()

# ---------------------------------------------------------------------------
# 2) Classe : PID
# ---------------------------------------------------------------------------
class PID:
    """
    ImplÃ©mentation simple d'un PID.
    - kp, ki, kd : gains proportionnel, intÃ©gral, dÃ©rivÃ©
    - setpoint : la consigne (0.5 pour centrer x ou y sur 0.5)
    - output_limits : borne la sortie (ex: (-50, 50))
    """
    def __init__(self, kp=1.0, ki=0.0, kd=0.0, setpoint=0.5, output_limits=(-999, 999)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits

        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = time.time()

    def reset(self):
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = time.time()

    def update(self, measurement):
        """
        Calcule la correction PID pour la mesure donnÃ©e.
        measurement : la valeur actuelle (ex: x_center ou y_center).
        """
        now = time.time()
        dt = now - self._last_time
        if dt <= 0.0:
            dt = 1e-16  # Ã©vite division par 0

        error = self.setpoint - measurement
        # Proportionnel
        p_out = self.kp * error
        # IntÃ©gral
        self._integral += error * dt
        i_out = self.ki * self._integral
        # DÃ©rivÃ©
        derivative = (error - self._last_error) / dt
        d_out = self.kd * derivative

        output = p_out + i_out + d_out
        # Borne la sortie
        min_out, max_out = self.output_limits
        output = max(min_out, min(output, max_out))

        # MÃ©morise pour la prochaine itÃ©ration
        self._last_error = error
        self._last_time = now

        return output

# ---------------------------------------------------------------------------
# 3) Classe : CameraDeplacement
# ---------------------------------------------------------------------------
class CameraDeplacement:
    """
    GÃ¨re deux servos :
      - servo horizontal = channel=0, max_angle=270
      - servo vertical   = channel=1, max_angle=180 (limitÃ© 45..135)
    + 2 PID (un pour x, un pour y) + zone morte + limites d'angle.
    """
    def __init__(
        self,
        # PID horizontal
        p_horizontal=1.0, i_horizontal=0.0, d_horizontal=0.0,
        # PID vertical
        p_vertical=1.0, i_vertical=0.0, d_vertical=0.0,
        # zone morte (autour de 0.5)
        dead_zone=0.05,
        # Limites d'angle (Â°) pour le servo vertical
        vertical_min_angle=45,
        vertical_max_angle=135,
        # Limites d'angle (Â°) pour le servo horizontal (facultatif, on peut tout autoriser 0..270)
        horizontal_min_angle=0,
        horizontal_max_angle=270
    ):
        # 1) Servos
        # canal 0 => horizontal => 0..270Â°
        self.servo_horizontal = ServoController(channel=0, max_angle=270)
        # canal 1 => vertical => 0..180Â°, mais on le limitera 45..135
        self.servo_vertical = ServoController(channel=1, max_angle=180)

        # 2) PID horizontal (pour x)
        self.pid_x = PID(
            kp=p_horizontal,
            ki=i_horizontal,
            kd=d_horizontal,
            setpoint=0.5,
            output_limits=(-150, 150)
        )
        # 3) PID vertical (pour y)
        self.pid_y = PID(
            kp=p_vertical,
            ki=i_vertical,
            kd=d_vertical,
            setpoint=0.5,
            output_limits=(-50, 50)
        )

        self.dead_zone = dead_zone

        # 4) Limites d'angle
        self.horizontal_min_angle = horizontal_min_angle
        self.horizontal_max_angle = horizontal_max_angle
        self.vertical_min_angle = vertical_min_angle
        self.vertical_max_angle = vertical_max_angle

    def select_best_detection(self, detections):
        best_confidence = 0.0
        best_det = None
        cat_detected = False

        if detections:
            for det in detections:
                label = det.get_label()
                confidence = det.get_confidence()

                # PrioritÃ© pour les chats
                if label == "cat":
                    best_confidence = confidence
                    best_det = det
                    cat_detected = True
                    break  # On arrÃªte la boucle dÃ¨s qu'on trouve un chat

                if label not in TRACK_OBJECTS:
                    continue

                # SÃ©lectionner la dÃ©tection avec la meilleure confiance si aucun chat n'est dÃ©tectÃ©
                if confidence > best_confidence and not cat_detected:
                    best_confidence = confidence
                    best_det = det

        return best_det

    def update_position(self, detections, user_data):
        """
        AppelÃ©e Ã  chaque dÃ©tection.
        (x_center, y_center) : coord. normalisÃ©es [0..1].
        But : amener x_center -> 0.5 et y_center -> 0.5
        """
        best_det = self.select_best_detection(detections)

        if best_det and user_data.barycentre_x is not None and user_data.barycentre_y is not None:
            x_center = user_data.barycentre_x
            y_center = user_data.barycentre_y

            # distance (absolue) par rapport au centre
            dx = abs(x_center - 0.5)
            dy = abs(y_center - 0.5)

            # -------------------
            # 1) Axe horizontal
            # -------------------
            if dx < self.dead_zone:
                # si dans zone morte, pas de correction
                correction_x = 0
            else:
                correction_x = self.pid_x.update(x_center)

            current_angle_h = self.servo_horizontal.current_angle
            new_angle_h = current_angle_h + correction_x

            # on borne [horizontal_min_angle, horizontal_max_angle]
            new_angle_h = max(self.horizontal_min_angle, 
                              min(self.horizontal_max_angle, new_angle_h))

            self.servo_horizontal.set_servo_angle(new_angle_h)

            # -------------------
            # 2) Axe vertical
            # -------------------
            if dy < self.dead_zone:
                correction_y = 0
            else:
                correction_y = self.pid_y.update(y_center)

            current_angle_v = self.servo_vertical.current_angle
            new_angle_v = current_angle_v + correction_y

            # borne dans [45..135] (pour votre contrainte)
            new_angle_v = max(self.vertical_min_angle, 
                              min(self.vertical_max_angle, new_angle_v))

            self.servo_vertical.set_servo_angle(new_angle_v)

    def cleanup(self):
        """Coupe la PWM sur les servos et reset les PID."""
                # Remettre les servomoteurs Ã  leur place d'origine
        self.servo_horizontal.set_servo_angle(135)  # 135Â° pour horizontal
        self.servo_vertical.set_servo_angle(90)     # 90Â° pour vertical

        # Attendre un court instant pour s'assurer que les servos atteignent leur position
        time.sleep(1)
        
        self.servo_horizontal.cleanup()
        self.servo_vertical.cleanup()
        self.pid_x.reset()
        self.pid_y.reset()
