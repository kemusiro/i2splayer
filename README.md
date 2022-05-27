# i2splayer
Raspberry Pi Pico上のMicroPythonでI2Sにより音楽を再生します。

# 前提条件
* 共立電子 ラズパイピコ実験基板(PICO-BOARD-V1)
* MicroPython 1.18

# 初期設定
Raspberry Pi PicoにI2S DACを接続します。I2S信号線は以下のように接続します。
| Pico | I2S DAC |
| ---- | ------- |
|GPIO18|SCK (BCK)|
|GPIO19|WS (LRCK)|
|GPIO20|SD (DIN)|

参考回路図も参照してください。

i2spayer.pyをRaspberry Pi Pico内蔵フラッシュメモリのルートフォルダに書き込みます。
再生したい音声ファイル(wavフォーマット)を同じフォルダに置きます。

# 使い方
* スイッチA(GPIO13)を押すと再生開始、スイッチB(GPIO14)を押すと再生停止します。
* 再生停止中にロータリーエンコーダーで再生する音源を変えられます。

# ライセンス
i2splayer.pyはMITライセンスで使用できます。
同梱している音源は[OtoLogic](https://otologic.jp)からお借りしています。
