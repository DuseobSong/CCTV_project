import numpy as np
import paho.mqtt.client as mqtt
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QPoint, QPointF, QLineF, QRectF
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont
from PyQt5.QtWidgets import QWidget
from enum import Enum
import time


class Direction(Enum):
    Left = 0
    Right = 1
    Up = 2
    Down = 3
    LeftUp = 4
    LeftDown = 5
    RightUp = 6
    RightDown = 7
    Neutral = -1


class Joystick(QWidget):
    signal_request_joystick_param = pyqtSignal()
    signal_send_test_msg = pyqtSignal()

    send_cmd = pyqtSignal(int, int, int)

    def __init__(self, parent):
        super(Joystick, self).__init__(parent)
        self.setMinimumSize(150, 150)
        self.moving_offset=(QPoint(0, 0))
        self.grab_center = False
        self.__max_distance = 55
        self.init_pwm_x = 993
        self.init_pwm_y = 813
        self.cur_pwm_x = self.init_pwm_x
        self.cur_pwm_y = self.init_pwm_y
        self.prev_pwm_x = self.init_pwm_x
        self.prev_pwm_y = self.init_pwm_y
        self.min_x = 570
        self.max_x = 1410
        self.min_y = 525
        self.max_y = 960
        self.setGeometry(0, 0, 150, 150)
        self.pressed = False
        self.target_cam = -1
        self.param_loaded = False

    @pyqtSlot()
    def test_msg_received(self):
        print('[JOYSTICK] Test msg received')
        time.sleep(1)
        self.signal_send_test_msg.emit()

    @pyqtSlot(object)
    def set_param(self, param):
        self.grab_center = param['grab_center']
        self.__max_distance = param['__max_distance']
        self.init_pwm_x = param['init_pwm_x']
        self.init_pwm_y = param['init_pwm_y']
        self.cur_pwm_x = param['cur_pwm_x']
        self.cur_pwm_y = param['cur_pwm_y']
        self.prev_pwm_x = param['prev_pwm_x']
        self.prev_pwm_y = param['prev_pwm_y']
        self.min_x = param['min_x']
        self.max_x = param['max_x']
        self.min_y = param['min_y']
        self.max_y = param['max_y']
        self.param_loaded = True
        print('[JOYSTICK]')
        print(param)

    @pyqtSlot(int)
    def set_target_idx(self, target_idx):
        self.target_cam = target_idx
        print('[JOYSTICK] Target camera idx: ', self.target_cam)

    def paintEvent(self, event):
        painter = QPainter(self)
        bounds = QRectF(-self.__max_distance, -self.__max_distance, self.__max_distance*2, self.__max_distance*2).translated(self._center())
        bounds2 = QRectF(-30, -30, 60, 60).translated(self._center())
        painter.drawEllipse(bounds)
        painter.drawEllipse(bounds2)
        painter.setBrush(Qt.black)
        painter.drawEllipse(self._center_ellipse())

    def _center_ellipse(self):
        if self.grab_center:
            return QRectF(-20, -20, 40, 40).translated(self.moving_offset)
        return QRectF(-20, -20, 40, 40).translated(self._center())

    def _center(self):
        return QPointF(self.width()/2, self.height()/2)

    def _bound_joystick(self, point):
        limit_line = QLineF(self._center(), point)
        if limit_line.length() > self.__max_distance:
            limit_line.setLength(self.__max_distance)
        return limit_line.p2()

    def joystick_direction(self):
        if not self.grab_center:
            return 0
        norm_vector = QLineF(self._center(), self.moving_offset)
        current_distance = norm_vector.length()
        angle = norm_vector.angle()

        distance = min(current_distance / self.__max_distance, 1.0)
        if current_distance > 30:
            if 22.5 <= angle < 67.5:
                self.calc_pwm(-1, -1)
                return Direction.RightUp, distance
            elif 67.5 <= angle < 112.5:
                self.calc_pwm(0, -1)
                return Direction.Up, distance
            elif 112.5 <= angle < 157.5:
                self.calc_pwm(1, -1)
                return Direction.LeftUp, distance
            elif 157.5 <= angle < 202.5:
                self.calc_pwm(1, 0)
                return Direction.Left, distance
            elif 202.5 <= angle < 247.5:
                self.calc_pwm(1, 1)
                return Direction.LeftDown, distance
            elif 247.5 <= angle < 292.5:
                self.calc_pwm(0, 1)
                return Direction.Down, distance
            elif 292.5 <= angle < 337.5:
                self.calc_pwm(-1, 1)
                return Direction.RightDown, distance
            else:
                self.calc_pwm(-1, 0)
                return Direction.Right, distance
        else: return Direction.Neutral, 0

    def mousePressEvent(self, event):
        self.grab_center = self._center_ellipse().contains(event.pos())
        self.pressed = True
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.grab_center = False
        self.moving_offset = QPointF(0, 0)
        self.update()
        self.pressed = False

    def mouseMoveEvent(self, event):
        if self.grab_center:
            self.moving_offset = self._bound_joystick(event.pos())
            self.update()

    def calc_pwm(self, xdiff, ydiff):
        if self.cur_pwm_x + xdiff <= self.min_x:
            new_x = self.min_x
        elif self.min_x <= self.cur_pwm_x + xdiff <= self.max_x:
            new_x = self.cur_pwm_x + xdiff
        else:
            new_x = self.max_x

        if self.cur_pwm_y + ydiff <= self.min_y:
            new_y = self.min_y
        elif self.min_y <= self.cur_pwm_y + ydiff <= self.max_y:
            new_y = self.cur_pwm_y + ydiff
        else:
            new_y = self.max_y

        #print(new_x, new_y)
        self.cur_pwm_x = new_x
        self.cur_pwm_y = new_y
        self.send_cmd.emit(self.target_cam+1, new_x, new_y)


class Control(QThread):
    def __init__(self, parent=None):
        super().__init__()
        self.joystick = Joystick(parent)

    def run(self):
        while not self.joystick.param_loaded:
            self.joystick.signal_request_joystick_param.emit()
            time.sleep(0.3)

        self.joystick.show()

        # controller loaded
        while True:
            #print(self.joystick.cur_pwm_x, self.joystick.cur_pwm_y)
            if self.joystick.pressed:
                self.joystick.joystick_direction()
            time.sleep(0.1)