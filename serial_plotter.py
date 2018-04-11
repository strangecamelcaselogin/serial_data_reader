import csv
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from threading import Thread

import numpy as np

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QHBoxLayout, QDialog, \
    QVBoxLayout, QCheckBox

from serial import Serial

import pyqtgraph as pg

from helpers import configure_serial


EXPORT_TO = './exports'
DEFAULT_DT = 0.05


class Communicator(QObject):
    update_ui = pyqtSignal(list)
    update_filtered_curves = pyqtSignal(int, bool)


class SerialReader:
    def __init__(self, communicator: Communicator, ):
        self._communicator = communicator
        self._ser = Serial()
        self._columns = None
        self._dt = None
        self._run = False
        self._serial_task = Thread(target=self.serial_task)

    def start(self, port, baudrate, columns: int, dt: float):
        self._columns = columns
        self._dt = dt
        self._ser.port = port.device
        self._ser.baudrate = baudrate
        self._ser.open()
        self._run = True
        self._serial_task.start()

    def stop(self):
        self._run = False
        if self._serial_task.is_alive():
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


class ViewSettingsWindow(QDialog):
    """
    Окно редактирования видимости линий
    """
    def __init__(self, communicator, invisible_curves, curves_names, parent=None):
        super().__init__(parent)

        self.communicator = communicator
        self.invisible_curves = invisible_curves
        self.curves_names = curves_names

        # создадим чекбоксы на каждую линию
        self.buttons_group = []
        for i, (c_name, c_active) in enumerate(zip(self.curves_names, self.invisible_curves)):
            cb = QCheckBox(c_name)
            cb.setChecked(not c_active)  # активный чекбокс показывает False в invisible_curves

            # не знаю как иначе передать номер чек бокса внутрь обработчика, только лямбда и замыкание...
            #  причем пробросим i внутрь лямбды через kwargs, иначе у каждой лямбды будет последнее i счетчитка
            cb.toggled.connect(lambda value, i=i: self.update_checkbox(i, value))
            self.buttons_group.append(cb)

        self.setWindowTitle('View Settings')
        self.setMinimumWidth(150)

        l = QVBoxLayout()
        for b in self.buttons_group:
            l.addWidget(b)

        self.setLayout(l)

    def update_checkbox(self, curve_number, value):
        self.communicator.update_filtered_curves.emit(curve_number, not value)  # значения чекбокса с флагами инверировано


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.communicator = Communicator()

        self.data_pw = pg.PlotWidget(background='#fff')
        self.export_button = QPushButton('Export')
        self.view_settings_button = QPushButton('View Settings')

        self.serial_reader = SerialReader(self.communicator)
        self.data = None
        self.curves = None
        self.curves_names = None
        self.invisible_curves = None

        self.setup_ui()

    def start(self, port, bd, columns, dt):
        self.init_plot(columns)
        self.serial_reader.start(port, bd, columns, dt)

    def stop(self):
        self.serial_reader.stop()

    def init_plot(self, columns_count):
        """ Инициализируем матрицу данных и объекты линий по количеству колонок в данных """
        self.data_pw.addLegend()
        self.data = [[] for _ in range(columns_count)]
        self.curves_names = [f'column {i+1}' for i in range(columns_count - 1)]
        self.curves = [self.data_pw.plot(pen=pg.intColor(i), name=self.curves_names[i]) for i in range(columns_count - 1)]
        self.invisible_curves = [False for _ in range(columns_count - 1)]  # флаги показа/скрытия линии

    def setup_ui(self):
        """ Инициализация интерфейса """
        cw = QWidget(self)
        self.setCentralWidget(cw)
        grid_layout = QGridLayout()
        cw.setLayout(grid_layout)

        h_layout = QHBoxLayout()
        top_bar = QWidget(self)
        top_bar.setLayout(h_layout)

        h_layout.addWidget(self.export_button)
        h_layout.addWidget(self.view_settings_button)
        h_layout.addStretch(1)

        grid_layout.addWidget(top_bar)
        grid_layout.addWidget(self.data_pw)

        self.setMinimumSize(1280, 800)

        # self.data_pw.enableAutoRange()
        self.data_pw.setYRange(0, 100)
        self.data_pw.showGrid(True, True, .5)

        self.export_button.clicked.connect(self.export)
        self.view_settings_button.clicked.connect(self.show_view_settings)
        self.communicator.update_ui.connect(self.update_ui)
        self.communicator.update_filtered_curves.connect(self.update_filtered_curves)

    @pyqtSlot()
    def export(self):
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = Path(EXPORT_TO).joinpath(f'export_{date}.csv')
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            data = np.array(self.data).transpose(1, 0)
            writer.writerows(data)

            QMessageBox.about(self, 'Success', f'export file name: "{filename}"')

    @pyqtSlot()
    def show_view_settings(self):
        vsw = ViewSettingsWindow(self.communicator, self.invisible_curves, self.curves_names, parent=self)
        vsw.show()

    @pyqtSlot(int, bool)
    def update_filtered_curves(self, curve_number: int, set_invisible: bool):
        """ Слот на изменении чекбокса в ViewSettingsWindow """
        self.invisible_curves[curve_number] = set_invisible
        if set_invisible:
            self.curves[curve_number].clear()

    @pyqtSlot(list)
    def update_ui(self, batch_values):
        """ Коллбек, вызывается из SerialReader по пришествию данных """
        # обновим данные
        for values in batch_values:
            for i, v in enumerate(values):
                self.data[i].append(v)

        # выведем данные
        t, *others = self.data  # разделим на временную шкалу и остальное
        for i, o in enumerate(others):
            if not self.invisible_curves[i]:  # если линия не отмечена как невидимая
                self.curves[i].setData(t, o)  # обновим данные у объекта линии


def configure_self():
    columns_count = int(input('Количество колонок: '))
    dt = input(f'Период обновления (секунды) ({DEFAULT_DT} по умлоч.): ')
    dt = DEFAULT_DT if dt == '' else float(dt)

    return columns_count, dt


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    port, bd = configure_serial()
    columns, dt = configure_self()

    main_window = MainWindow()
    try:
        main_window.start(port, bd, columns, dt)
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception(e)
        sys.exit(1)
    finally:
        main_window.stop()
