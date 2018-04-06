import csv
from datetime import datetime

from serial import Serial
from serial.tools.list_ports import comports


def bytes_to_data(raw_msg: bytes):
    result = []

    lines = raw_msg.split(b'\r\n')
    for l in lines:
        try:
            l = l.decode()
            t, v = l.split(';')
            result.append((int(t), (int(v))))
        except (UnicodeDecodeError, ValueError) as e:
            pass

    return result


if __name__ == '__main__':
    ports = comports()
    if not ports:
        print('Не найдено ни ожного последовательного порта')
        exit()

    for i, p in enumerate(ports):
        print(f'{i}: {p.device}')

    port_number = int(input('Какой порт использовать (номер)? ')) if len(ports) > 1 else 0
    bd = int(input('Скорость соединения: '))

    ser = Serial(ports[port_number].device, bd)

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
