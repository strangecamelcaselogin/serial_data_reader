from serial.tools.list_ports import comports


DEFAULT_BD = 9600


def configure_serial():
    ports = comports()
    if not ports:
        print('Не найдено ни одного последовательного порта')
        exit()

    for i, p in enumerate(ports):
        print(f'{i}: {p.device}')

    port_number = int(input('Какой порт использовать (номер)? ')) if len(ports) > 1 else 0
    bd = input('Скорость соединения (9600 по умолч.): ')
    bd = DEFAULT_BD if bd == '' else int(bd)
    selected_port = ports[port_number]

    return selected_port, bd