import csv
from datetime import datetime

from serial import Serial

from helpers import configure_serial


def bytes_to_data(raw_msg: bytes):
    result = []

    lines = raw_msg.split(b'\r\n')
    for l in lines:
        try:
            values = list(map(float, l.split(b';')))
            result.append(values)
        except (UnicodeDecodeError, ValueError) as e:
            pass

    return result


if __name__ == '__main__':
    port, bd = configure_serial()

    ser = Serial(port.device, bd)

    raw_data = b""
    try:
        print('Чтобы остановить сбор данных нажмите Ctrl + C')
        while True:
            msg = ser.read_all()
            if msg:
                print(msg)
                raw_data += msg

    except KeyboardInterrupt:
        print('Остановка')

    serial_data = bytes_to_data(raw_data)

    date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = input('Введите имя файла: ') + f'_{date}.csv'
    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerows(serial_data)

    print('Готово.')
