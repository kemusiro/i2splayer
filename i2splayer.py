from machine import I2S
from machine import Pin
import os
import re
import time
import _thread

## 大域変数の設定
# 演奏する曲の番号
songnum = 0
# 演奏中を示すフラグ
in_play = False

## GPIOの設定
ledR = Pin(10, Pin.OUT)
ledG = Pin(11, Pin.OUT)
ledB = Pin(12, Pin.OUT)
swA = Pin(13, Pin.IN)
swB = Pin(14, Pin.IN)
rotA = Pin(17, Pin.IN)
rotB = Pin(16, Pin.IN)

## ロータリーエンコーダーの設定
count = 0
previous = 0x11
def irq_encoder(pin):
    """ ロータリーエンコーダーの操作にしたがって曲番号を増減する。
    """
    global previous
    global count
    global songnum
    global in_play

    # 演奏中は無視する。
    if in_play:
        return
    
    current = rotA.value() + (rotB.value() << 1)
    if current != previous:
        state = ((previous << 1) ^ current) & 3
        count += 1 if state < 2 else -1
        previous = current
        if count >= 3:
            songnum += 1
            print(songnum)
            count = 0
        elif count <= -3:
            songnum -= 1
            print(songnum)
            count = 0

rotA.irq(irq_encoder, trigger=Pin.IRQ_FALLING|Pin.IRQ_RISING)
rotB.irq(irq_encoder, trigger=Pin.IRQ_FALLING|Pin.IRQ_RISING)

## ボタンの設定
start_requested = False
stop_requested = False
def irq_button(pin):
    """ 再生、終了ボタンの処理を行う。
    """
    global start_requested
    global stop_requested
    if pin == Pin(13):
        start_requested = True
    elif pin == Pin(14):
        stop_requested = True

swA.irq(irq_button, trigger=Pin.IRQ_FALLING)
swB.irq(irq_button, trigger=Pin.IRQ_FALLING)


def init_i2s(sck, ws, sd, bits=16, rate=8000, format=I2S.STEREO, buflen=5000):
    """ I2Sを初期化する。
    """
    return I2S(
        0, # I2S ID
        sck=sck,
        ws=ws,
        sd=sd,
        mode=I2S.TX,
        bits=bits,
        format=format,
        rate=rate,
        ibuf=buflen, # buffer長(バイト)
    )

def player(i2s, files):
    """ 音楽ファイルを再生する。
    """
    global start_requested
    global stop_requested
    global songnum
    global in_play

    buffer = bytearray(1000)
    buffer_mv = memoryview(buffer)
    wav = None

    try:
        print('player start')
        while True:
            while not start_requested:
                time.sleep_ms(100)
            start_requested = False
            print(songnum % len(files), files[songnum % len(files)])
            wav = open(files[songnum % len(files)], "rb")
            pos = wav.seek(44)
            in_play = True
            while not stop_requested:
                num_read = wav.readinto(buffer_mv)
                if num_read == 0:
                    #  曲の最後に達したら先頭に戻る。
                    wav.seek(44)
                else:
                    i2s.write(buffer_mv[:num_read])
            stop_requested = False
            wav.close()
            in_play = False
    except (KeyboardInterrupt, Exception) as e:
        print(e)
        if wav is not None:
            wav.close()
        i2s.deinit()
        return
    
def get_wave_files():
    """ フラッシュメモリ中に格納されているwavファイル一覧を取得する。
    """
    return [f for f in os.listdir()
            if re.search('\.wav$', f) is not None]

def display(arg):
    """ 再生中にLEDを明滅させる。
    """
    global ledR, ledG, ledB
    global in_play

    def clear():
        ledR.off()
        ledG.off()
        ledB.off()
        
    while True:
        p = 0
        clear()
        while in_play:
            ledR.value(1 if p % 4 == 0 else 0)
            ledG.value(1 if p % 2 == 1 else 0)
            ledB.value(1 if p % 4 == 2 else 0)
            p += 1
            time.sleep_ms(500)
        time.sleep_ms(10)

i2s = init_i2s(Pin(18, Pin.OUT),  # sck
               Pin(19, Pin.OUT),  # ws
               Pin(20, Pin.OUT))  # sd
_thread.start_new_thread(display, (None,))
player(i2s, get_wave_files())
