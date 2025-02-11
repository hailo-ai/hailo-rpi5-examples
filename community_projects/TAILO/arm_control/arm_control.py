#!/usr/bin/env python
# -*- coding: utf-8 -*-

# *******************************************************************************
# Copyright 2017 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# *******************************************************************************


# *******************************************************************************
# ***********************     Read and Write Example      ***********************
#  Required Environment to run this example :
#    - Protocol 2.0 supported DYNAMIXEL(X, P, PRO/PRO(A), MX 2.0 series)
#    - DYNAMIXEL Starter Set (U2D2, U2D2 PHB, 12V SMPS)
#  How to use the example :
#    - Select the DYNAMIXEL in use at the MY_DXL in the example code.
#    - Build and Run from proper architecture subdirectory.
#    - For ARM based SBCs such as Raspberry Pi, use linux_sbc subdirectory to build and run.
#    - https://emanual.robotis.com/docs/en/software/dynamixel/dynamixel_sdk/overview/
#  Author: Ryu Woon Jung (Leon)
#  Maintainer : Zerom, Will Son
# *******************************************************************************

import os
import time

if os.name == 'nt':
    import msvcrt

    def getch():
        return msvcrt.getch().decode()
else:
    import sys
    import tty
    import termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

from dynamixel_sdk import *  # Uses Dynamixel SDK library

# ********* DYNAMIXEL Model definition *********
# ***** (Use only one definition at a time) *****
# MY_DXL = 'X_SERIES'       # X330 (5.0 V recommended), X430, X540, 2X430
# MY_DXL = 'MX_SERIES'    # MX series with 2.0 firmware update.
# MY_DXL = 'PRO_SERIES'   # H54, H42, M54, M42, L54, L42
# MY_DXL = 'PRO_A_SERIES' # PRO series with (A) firmware update.
# MY_DXL = 'P_SERIES'     # PH54, PH42, PM54
MY_DXL = 'XL320'        # [WARNING] Operating Voltage : 7.4V
DXL_ANGLE_TO_REG_VAL = 1023/180
DXL_REG_VAL_TO_ANGLE = 180/1023

# Control table address
if MY_DXL == 'X_SERIES' or MY_DXL == 'MX_SERIES':
    ADDR_TORQUE_ENABLE = 64
    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132
    # Refer to the Minimum Position Limit of product eManual
    DXL_MINIMUM_POSITION_VALUE = 0
    # Refer to the Maximum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 4095
    BAUDRATE = 57600
elif MY_DXL == 'PRO_SERIES':
    ADDR_TORQUE_ENABLE = 562       # Control table address is different in DYNAMIXEL model
    ADDR_GOAL_POSITION = 596
    ADDR_PRESENT_POSITION = 611
    # Refer to the Minimum Position Limit of product eManual
    DXL_MINIMUM_POSITION_VALUE = -150000
    # Refer to the Maximum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 150000
    BAUDRATE = 57600
elif MY_DXL == 'P_SERIES' or MY_DXL == 'PRO_A_SERIES':
    # Control table address is different in DYNAMIXEL model
    ADDR_TORQUE_ENABLE = 512
    ADDR_GOAL_POSITION = 564
    ADDR_PRESENT_POSITION = 580
    # Refer to the Minimum Position Limit of product eManual
    DXL_MINIMUM_POSITION_VALUE = -150000
    # Refer to the Maximum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 150000
    BAUDRATE = 57600
elif MY_DXL == 'XL320':
    ADDR_TORQUE_ENABLE = 24
    ADDR_GOAL_POSITION = 30
    ADDR_PRESENT_POSITION = 37
    # Refer to the CW Angle Limit of product eManual
    DXL_MINIMUM_POSITION_VALUE = 0
    # Refer to the CCW Angle Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 1023
    BAUDRATE = 115200   # Default Baudrate of XL-320 is 1Mbps

# DYNAMIXEL Protocol Version (1.0 / 2.0)
# https://emanual.robotis.com/docs/en/dxl/protocol2/
PROTOCOL_VERSION = 2.0

# Factory default ID of all DYNAMIXEL is 1
HORIZ_DXL_ID = 2
VERT_DXL_ID = 3

# Use the actual port assigned to the U2D2.
# ex) Windows: "COM*", Linux: "/dev/ttyUSB*", Mac: "/dev/tty.usbserial-*"
DEVICENAME = '/dev/ttyAMA0'

TORQUE_ENABLE = 1     # Value for enabling the torque
TORQUE_DISABLE = 0     # Value for disabling the torque
DXL_MOVING_STATUS_THRESHOLD = 20 * DXL_REG_VAL_TO_ANGLE    # Dynamixel moving status threshold

# Initialize PortHandler instance
# Set the port path
# Get methods and members of PortHandlerLinux or PortHandlerWindows
portHandler = PortHandler(DEVICENAME)

# Initialize PacketHandler instance
# Set the protocol version
# Get methods and members of Protocol1PacketHandler or Protocol2PacketHandler
packetHandler = PacketHandler(PROTOCOL_VERSION)

# Open port
if portHandler.openPort():
    print("Succeeded to open the port")
else:
    print("Failed to open the port")
    print("Press any key to terminate...")
    getch()
    quit()

# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    print("Press any key to terminate...")
    getch()
    quit()


def enable_arm():
    # Enable Dynamixel Torque
    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, HORIZ_DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_ENABLE)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
    else:
        print("Dynamixel has been successfully connected")

    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, VERT_DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_ENABLE)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
    else:
        print("Dynamixel has been successfully connected")


def disable_arm():
    # Disable Dynamixel Torque
    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, HORIZ_DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(portHandler, VERT_DXL_ID, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    # Close port
    portHandler.closePort()


def move_arm_horizontal_step(step):
    arm_present_angle = read_arm_horizontal_angle()
    step *= 5
    if (arm_present_angle + step > 180):
        print("Cannot move arm to angle greater than 180")
        return False
    elif (arm_present_angle + step < 0):
        print("Cannot move arm to angle less than 0")
        return False
    set_arm_horizontal_angle(arm_present_angle + step)
    return True


def move_arm_vertical_step(step):
    arm_present_angle = read_arm_vertical_angle()
    step *= 5
    if (arm_present_angle + step > 180):
        print("Cannot move arm to angle greater than 180")
        return False
    elif (arm_present_angle + step < 0):
        print("Cannot move arm to angle less than 0")
        return False
    set_arm_vertical_angle(arm_present_angle + step)


def set_arm_horizontal_angle(angle):
    return set_arm_angle(angle, HORIZ_DXL_ID)


def set_arm_vertical_angle(angle):
    return set_arm_angle(angle, VERT_DXL_ID)


def read_arm_horizontal_angle():
    # Read present position
    dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, HORIZ_DXL_ID, ADDR_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    angle = dxl_present_position * DXL_REG_VAL_TO_ANGLE
    # print("[ID:%03d] Angle:%03d  PresPos:%03d" %(HORIZ_DXL_ID, angle, dxl_present_position))
    return angle


def read_arm_vertical_angle():
    # Read present position
    dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read2ByteTxRx(portHandler, VERT_DXL_ID, ADDR_PRESENT_POSITION)
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))

    angle = dxl_present_position * DXL_REG_VAL_TO_ANGLE
    # print("[ID:%03d] Angle:%03d  PresPos:%03d" %(HORIZ_DXL_ID, angle, dxl_present_position))
    return angle


def set_arm_angle(angle, motor_id):
    goal_pos = int(angle * DXL_ANGLE_TO_REG_VAL)
    # Write goal position
    dxl_comm_result, dxl_error = packetHandler.write2ByteTxRx(portHandler, motor_id, ADDR_GOAL_POSITION, goal_pos)
    print("Setting angle to %d. goal_pos %d" % (angle, goal_pos))
    if dxl_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
        return False
    elif dxl_error != 0:
        print("%s" % packetHandler.getRxPacketError(dxl_error))
        return False

    while 1:
        arm_present_angle = read_arm_horizontal_angle()
        print("[ID:%03d] GoalPos:%03d  PresPos:%03d" % (motor_id, goal_pos, arm_present_angle))
        if not abs(angle - arm_present_angle) > DXL_MOVING_STATUS_THRESHOLD:
            print("success! [ID:%03d] GoalAngle:%03d  PresentAngle:%03d" % (motor_id, angle, arm_present_angle))
            break
        time.sleep(0.1)
    return True


# if enable_arm() is False:
#     quit()
# move_arm_horizontal_step(1)
# move_arm_vertical_step(1)
# if set_arm_horizontal_angle(10) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_horizontal_angle(50) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_horizontal_angle(170) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_horizontal_angle(10) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_vertical_angle(10) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_vertical_angle(50) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_vertical_angle(170) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# if set_arm_vertical_angle(10) is False:
#     disable_arm()
#     quit()
# time.sleep(0.1)
# disable_arm()
# quit()
