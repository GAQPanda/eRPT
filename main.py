import threading
import serial
import time
import configparser
import pyaudio
import numpy as np
import atexit


@atexit.register
def clean():
    global cat
    cat_closeport()


config = configparser.ConfigParser()
config.read('Config.cfg')

mode_a = 0
fre_a = 0
mode_b = 0
fre_b = 0
cat_port = ""
cat_rate = 0
read_status_ways = 0
sleep_time = 0
temp = 0


def choose_mic():
    p = pyaudio.PyAudio()
    devices = p.get_device_count()
    for i in range(devices):
        device_info = p.get_device_info_by_index(i)
        if device_info.get('maxInputChannels') > 0:
            print(f"音频输入设备: {device_info.get('name')} , 设备代码: {device_info.get('index')}")
    mic_code = input("请选择音频输入设备:")
    return mic_code


def read_cfg():
    global mode_a, mode_b, fre_a, fre_b, cat_port, cat_rate, read_status_ways, sleep_time
    mode_a = config.get('VFO_A', 'Mode_A')
    fre_a = config.get('VFO_A', 'Frequency_A')
    mode_b = config.get('VFO_B', 'Mode_B')
    fre_b = config.get('VFO_B', 'Frequency_B')
    cat_port = config.get('CAT', 'Port')
    cat_rate = config.get('CAT', 'Rate')
    read_status_ways = config.get('General', 'ReadStatusWays')
    sleep_time = config.get('General', 'SleepTime')
    return mode_a, mode_b, fre_a, fre_b, cat_port, cat_rate, read_status_ways, sleep_time


def read_mic():
    global mic_code, sleep_time
    # 初始化PyAudio
    p = pyaudio.PyAudio()
    # 打开麦克风
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=int(mic_code),
                    frames_per_buffer=1024)

    # 读取一帧音频数据
    while True:
        data = np.frombuffer(stream.read(1024), dtype=np.int16)

        # 计算音量
        volume = np.max(data)
        if volume == 0:
            # RX_Code:
            # No signal = 1
            # Have signal = 0
            rx_code = 1
        else:
            rx_code = 0
        return rx_code


def cat_openport():
    global cat_port, cat_rate
    cat_do = serial.Serial(cat_port, cat_rate, timeout=0.1)
    cat_do.setRTS(False)
    cat_do.setDTR(False)
    cat_do.write(bytes.fromhex("0000000000"))
    cat_do.write(bytes.fromhex("000000004E"))
    return cat_do


def cat_closeport():
    cat.write(bytes.fromhex("000000008E"))
    cat.write(bytes.fromhex("0000000080"))


def zfill_freq():
    global fre_a, fre_b, cat, sleep_time
    int_fre_a = fre_a
    int_fre_b = fre_b
    str_fre_a = str(int_fre_a)
    str_fre_b = str(int_fre_b)
    z_fre_a = str_fre_a.zfill(8)
    z_fre_b = str_fre_b.zfill(8)
    return z_fre_a, z_fre_b


def send_freq():
    global z_fre_a, z_fre_b, cat, sleep_time, temp
    if temp % 2 == 0:
        cat.write(bytes.fromhex(z_fre_a + "11"))
        cat.write(bytes.fromhex(z_fre_b + "21"))
    else:
        cat.write(bytes.fromhex(z_fre_a + "21"))
        cat.write(bytes.fromhex(z_fre_b + "11"))
    time.sleep(float(sleep_time))


def read_cat():
    global cat, sleep_time
    while True:
        cat_status = cat.read()
        try:
            rx_code = cat_status[0]
        except IndexError:
            rx_code = "Unknown"
            print("error")
        # RX_Code:
        # No signal = 1
        # Have signal = 0
        return rx_code


if __name__ == '__main__':

    cfg = read_cfg()
    mode_a, mode_b, fre_a, fre_b, cat_port, cat_rate, read_status_ways, sleep_time = read_cfg()
    cat = cat_openport()
    z_fre_a, z_fre_b = zfill_freq()
    t_cat = threading.Thread(target=read_cat)
    t_mic = threading.Thread(target=read_mic)

    if read_status_ways == '1':
        t_cat.start()
        while True:
            if read_cat() == "1":
                send_freq()
            elif read_cat() == "0":
                print("TX")
    elif read_status_ways == '2':
        mic_code = choose_mic()
        t_mic.start()
        while True:
            if read_mic() == "1":
                send_freq()
            elif read_mic() == "0":
                print("RX")
    else:
        print("Config.cfg ERROR")
