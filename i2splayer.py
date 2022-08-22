from machine import I2S, Pin
import os, re, sys, time, _thread

# 再生する音声ファイルのサンプリングレート(Hz)
SRATE = const(8000)
# 再生する音声ファイルのチャンネル数
# モノラルの場合はI2S.MONOとする。
FORMAT = I2S.STEREO

# LEDを点滅させる処理を行うクラス
class Flasher:
    def __init__(self):
        # LED用のGPIOを出力モードで初期化
        self.ledR = Pin(10, Pin.OUT)
        self.ledG = Pin(11, Pin.OUT)
        self.ledB = Pin(12, Pin.OUT)
 
    # 点滅を開始する。
    def start(self):
        self.req_stop = False
        # 点滅用のスレッドを作成し、実行を開始する。
        _thread.start_new_thread(self._flasher, (200,))
        
    # 点滅を終了する。
    def stop(self):
        self.req_stop = True

    # 点滅のメイン処理
    def _flasher(self, period):
        t = 0
        while not self.req_stop:
            self.ledR.value(1 if t % 4 == 0 else 0)
            self.ledG.value(1 if t % 2 == 1 else 0)
            self.ledB.value(1 if t % 4 == 2 else 0)
            t = (t + 1) % 4
            time.sleep_ms(period)
        self.ledR.off()
        self.ledG.off()
        self.ledB.off()

# 複数の要素から一つの要素を選択するクラス。
class Selector:
    def __init__(self, elements):
        if elements is None or len(elements) == 0:
            raise ValueError("1個以上の要素を持つリストを指定してください。")
        self._elements = elements
        self.index = 0
        # ロータリーエンコーダー用のGPIOを入力モードで初期化する。
        self.rotA = Pin(17, Pin.IN)
        self.rotB = Pin(16, Pin.IN)
        # 立ち上がり・立ち下がりエッジで割り込みを発生させる。
        self.rotA.irq(self._isr, trigger=Pin.IRQ_FALLING|Pin.IRQ_RISING)
        self.rotB.irq(self._isr, trigger=Pin.IRQ_FALLING|Pin.IRQ_RISING)
        self.count = 0
        self.previous = 0x00
        
    # ロータリーエンコーダーで発生するGPIO¥割り込みのハンドラ
    def _isr(self, pin):
        current = self.rotA.value() + (self.rotB.value() << 1)
        if current != self.previous:
            state = ((self.previous >> 1) ^ current) & 3
            self.count += 1 if state % 2 == 1 else -1
            self.previous = current
            if self.count == 4 or self.count == -4:
                direction = self.count // 4
                self.index = (self.index + direction) % len(self._elements)
                print(self.index, self._elements[self.index])
                self.count = 0

    # 現在選択されている要素を返す。
    def get_current(self):
        return self.index, self._elements[self.index]

# 音声ファイルを再生するクラス
class Player:
    def __init__(self):
        # I2Sモジュールを初期化する。
        self.i2s = I2S(
            0,
            sck=Pin(18, Pin.OUT), ws=Pin(19, Pin.OUT), sd=Pin(20, Pin.OUT),
            mode=I2S.TX, bits=16, format=FORMAT, rate=SRATE, ibuf=5000)
        self.flasher = Flasher()
        # フラッシュメモリ中で拡張子が.wavのファイルを抽出する。
        self.file_list = [file for file in os.listdir()
                          if re.search('\.wav$', file) is not None]
        self.selector = Selector(self.file_list)
        self.start_requested = False
        self.stop_requested = False

        # ボタンの割り込み設定
        self.swA = Pin(13, Pin.IN)
        self.swB = Pin(14, Pin.IN)
        self.swA.irq(self._start_isr, trigger=Pin.IRQ_FALLING)
        self.swB.irq(None)

    def main_loop(self):
        # I2S再生データを格納するバッファメモリを確保する。
        buffer = bytearray(1000)
        buffer_mv = memoryview(buffer)
        try:
            print('player start')
            while True:
                # 開始ボタンが押されたかを10ミリ秒ごとに監視する。
                while not self.start_requested:
                    time.sleep_ms(10)
                self.start_requested = False
                index, file_name = self.selector.get_current()
                with open(file_name, "rb") as f:
                    # wavファイルのヘッダ部(44バイト)を読み飛ばす。
                    f.seek(44)
                    # 終了ボタンが押されるまで再生を繰り返す。
                    while not self.stop_requested:
                        num_read = f.readinto(buffer_mv)
                        if num_read == 0:
                            #  曲の最後に達したら先頭に戻る。
                            f.seek(44)
                        else:
                            # 確保したバッファメモリ分のデータをI2Sモジュールに送信する。
                            self.i2s.write(buffer_mv[:num_read])
                    self.stop_requested = False
        except (KeyboardInterrupt, Exception):
            # キーボード割り込み(Ctrl-C)または例外が発生したら終了する。
            self.i2s.deinit()

    # 開始ボタンが押されたときの割り込みハンドラ
    def _start_isr(self, arg):
        self.swA.irq(None)
        self.start_requested = True
        self.swB.irq(self._stop_isr, trigger=Pin.IRQ_FALLING)
        self.flasher.start()

    # 終了ボタンが押されたときの割り込みハンドラ
    def _stop_isr(self, arg):
        self.swB.irq(None)
        self.stop_requested = True
        self.swA.irq(self._start_isr, trigger=Pin.IRQ_FALLING)
        self.flasher.stop()

# 実行スクリプトとして読み出されたときはプレイヤーを開始する。
if __name__ == '__main__':
    Player().main_loop()
    # 実行中のスレッドがあれば実行終了させてプレイヤーを終了させる。
    sys.exit()
    
