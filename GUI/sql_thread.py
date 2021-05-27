from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import numpy as np
import pandas as pd
import pymysql
import time


class Database(QThread):
    signal_request_sql_param = pyqtSignal()
    signal_sql_param_received = pyqtSignal()

    signal_send_camera_info = pyqtSignal(object)
    signal_send_sensor_data = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.HOST = None
        self.USER = None
        self.PSWD = None
        self.DB = None
        self.CHST = None
        self.sensor_data = None
        self.camera_info_sent = False

    @pyqtSlot(object)
    def set_param(self, param):
        print('[SQL] Parameter-set received')
        print(param)
        self.HOST = param['host']
        self.USER = param['user']
        self.PSWD = param['pswd']
        self.DB = param['db']
        self.CHST = param['chst']

    @pyqtSlot()
    def camera_info_chk(self):
        self.camera_info_sent = True

    @pyqtSlot()
    def send_sensor_data(self):
        self.signal_send_sensor_data.emit(self.sensor_data)

    def insert_dummy(self):
        sql = 'INSERT INTO sensor_data VALUES (0, 1, curdate(), curtime(), {:.5f}, {:.5f}, {:.5f});'.format(25+np.random.normal(0, 1, 1)[0]*5, 50 + np.random.normal(0, 1, 1)[0]*10, 500 + np.random.normal(0, 20, 1)[0]*10)
        self.cur.execute(sql)
        self.connect.commit()

    def get_camera_info(self):
        sql = 'SELECT * FROM camera_info'
        self.cur.execute(sql)
        data = self.cur.fetchall()
        self.camera_info = pd.DataFrame(data, columns=['no', 'ip_addr', 'mode'])
        self.signal_send_camera_info.emit(self.camera_info)

    def get_sensor_data(self):
        #self.insert_dummy()
        sql_max_check = 'SELECT max(no) from sensor_data;'
        self.cur.execute(sql_max_check)
        max_no = self.cur.fetchone()
        max_no = int(max_no[0])
        if max_no <= 25:
            min_no = 0
        else:
            min_no = max_no - 25

        sql_retrieve = 'SELECT * FROM sensor_data WHERE (date = (select curdate()) and no >= {} and no <= {});'.format(
            min_no, max_no)
        self.cur.execute(sql_retrieve)
        data = pd.DataFrame(self.cur.fetchall(),
                            columns=['no', 'controller_no', 'date', 'times', 'temperature', 'humidity', 'illuminance'])

        if len(data) > 0:
            date = data['date']
            times = data.times
            temp = np.array(data.temperature)
            humi = np.array(data.humidity)
            illu = np.array(data.illuminance)
            date_list = pd.unique(date)

            times_ = []
            for t in times:
                times_.append(t.split(':'))
            times_ = np.array(times_, dtype=np.int)
            m_t = np.mean(temp)
            s_t = np.std(temp)
            m_h = np.mean(humi)
            s_h = np.std(humi)
            m_i = np.mean(illu)
            s_i = np.std(illu)

            temp[temp > m_t + s_t * 0.5] = m_t
            temp[temp < m_t - s_t * 0.5] = m_t
            humi[humi > m_h + s_h * 0.5] = m_h
            humi[humi < m_h - s_h * 0.5] = m_h
            illu[illu > m_i + s_i * 0.5] = m_i
            illu[illu < m_i - s_i * 0.5] = m_i

            # xtick
            seconds = []
            for i in range(len(times_)):
                second = (-1 if times_[i, 0] == 23 else 0) * 3600 + times_[i, 1] * 60 + times_[i, 2]
                seconds.append(second)

            n_ticks = 7
            tick_interval = 20
            tmp_seconds_end = seconds[-1]
            tmp_seconds_start = seconds[-1] - (n_ticks - 2) * tick_interval
            new_seconds = np.linspace(tmp_seconds_start, tmp_seconds_end, n_ticks, True).astype(np.int)
            seconds -= min(seconds)
            ticks = [tick_interval * i for i in range(0, n_ticks + 1)]
            tick_labels = ['{}:{}'.format(tmp_seconds // 60 % 60, tmp_seconds % 60) for tmp_seconds in new_seconds]
            tick_labels.append(
                '{}:{}'.format((new_seconds[-1] + tick_interval) // 60 % 60, (new_seconds[-1] + tick_interval) % 60))

            sensor_data = dict({'date': date_list[-1],
                                 'timestamp': seconds,
                                 'xtick': ticks,
                                 'tick_labels': tick_labels,
                                 'temperature': temp.tolist(),
                                 'humidity': humi.tolist(),
                                 'illuminance': illu.tolist()
                                 })

            self.sensor_data = sensor_data

    def run(self):
        print('[SQL] Request parameter-set')
        self.signal_request_sql_param.emit()
        while self.HOST is None:
            time.sleep(0.1)
            '''
            self.signal_request_sql_param.emit()
            '''
            continue

        self.signal_sql_param_received.emit()
        print('[SQL] Parameter-set received')

        self.connect = pymysql.connect(host = self.HOST, user=self.USER, password=self.PSWD, db=self.DB, charset=self.CHST)
        self.cur = self.connect.cursor()
        self.get_camera_info()

        while not self.camera_info_chk:
            self.get_camera_info()
            time.sleep(0.1)

        while True:
            self.get_sensor_data()
            time.sleep(5)

