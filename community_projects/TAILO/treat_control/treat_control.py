import RPi.GPIO as GPIO
import time

# Set the GPIO mode
GPIO.setmode(GPIO.BOARD)

# Define the GPIO pin for the motor
MOTOR_PIN = 12

# Set up the GPIO pin as an output
GPIO.setup(MOTOR_PIN, GPIO.OUT)

# Set up PWM on the motor pin at 50Hz
pwm = GPIO.PWM(MOTOR_PIN, 50)

def init_treat_control():
    # Start PWM with a duty cycle of 0 (motor off)
    pwm.start(0.1)

def perform_treat_throw():
    print("Throwing")
    pwm.ChangeDutyCycle(10)
    time.sleep(0.3)
    pwm.ChangeDutyCycle(0.1)

def stop_treat_control():
    pwm.ChangeDutyCycle(0.1)
    pwm.stop()
    # Clean up the GPIO pins and stop PWM
    GPIO.cleanup()