import sys
import logging
import time
from threading import Thread

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

from serial import Serial
from serial.tools.list_ports import comports

import pyqtgraph as pg


class Config:
    boudrate = 9600
    columns = 4
    dt = 0.05

config = Config()


def connect_to_serial(boudrate):
    ports = comports()
    if not ports:
        raise Exception('no connection')

    return Serial(ports[0].device, boudrate)


class Communicator(QObject):
    update_ui = pyqtSignal(list)


class SerialReader:
    def __init__(self, communicator: Communicator, columns: int, boudrate: int, dt: float):
        self._communicator = communicator
        self._ser = connect_to_serial(boudrate)
        self._columns = columns
        self._dt = dt

        self._run = False
        self._serial_task = Thread(target=self.serial_task)

    def start(self):
        self._run = True
        self._serial_task.start()

    def stop(self):
        self._run = False
        self._serial_task.join()

    def serial_task(self):
        """
        Задача для потока. Читаем все что есть, делим на строки, делим каждую на значения.
        Значения накапливаем и отправляем в поток интерфейса
        """
        while self._run:
            time.sleep(self._dt)  # не лучший способ установить частоту событий для интерфейса, но работает

            batch_data = []

            byte_data = self._ser.read_all().split(b'\r\n')
            for line in byte_data:
                try:
                    values = line.split(b';')
                    values = list(map(float, values))  # преобразуем во float

                    # пропустим строку, в которой меньше данных, чем ожидается (да, такое бывает при чтении порциями)
                    #   и это не страшно
                    if len(values) == self._columns:
                        batch_data.append(values)

                except ValueError:
                    pass

            if batch_data:
                self._communicator.update_ui.emit(batch_data)  # отправим данные


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.communicator = Communicator()
        self.columns_count = config.columns
        self.serial_reader = SerialReader(self.communicator, self.columns_count, config.boudrate, config.dt)

        self.data_pw = pg.PlotWidget(background='#fff')

        self.data = None
        self.curves = None
        self.init_plot()

        self.setup_ui()

    def start(self):
        self.serial_reader.start()

    def stop(self):
        self.serial_reader.stop()

    def setup_ui(self):
        """ Инициализация интерфейса """
        self.layout().addWidget(self.data_pw)
        self.setFixedSize(1280, 800)
        self.data_pw.resize(1280, 800)

        # self.data_pw.enableAutoRange()
        self.data_pw.setYRange(0, 100)
        self.data_pw.showGrid(True, True, .5)

        self.communicator.update_ui.connect(self.update_ui)

    def init_plot(self):
        """ Инициализируем матрицу данных и объекты линий по количеству колонок в данных """
        self.data = [[] for _ in range(self.columns_count)]
        self.curves = [self.data_pw.plot(pen=pg.intColor(i)) for i in range(self.columns_count - 1)]

    def update_ui(self, batch_values):
        """ Коллбек, вызывается из SerialReader по пришествию данных """
        # обновим данные
        for values in batch_values:
            for i, v in enumerate(values):
                self.data[i].append(v)

        # выведем данные
        t, *others = self.data  # разделим на временную шкалу и остальное
        for i, o in enumerate(others):
            self.curves[i].setData(t, o)  # обновим данные у объекта линии


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    mainWindow = MainWindow()
    try:
        mainWindow.start()
        mainWindow.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception(e)
        sys.exit(1)
    finally:
        mainWindow.stop()
