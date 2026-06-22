# src/hardware/lcd_i2c.py
# Driver LCD 16x2 via adaptador I2C PCF8574
# Compatível com o display do kit Freenove
# Baseado na especificação HD44780 + PCF8574

from machine import I2C
import time

_RS = 0x01   # Register Select
_EN = 0x04   # Enable
_BL = 0x08   # Backlight


class LCD:
    """Driver I2C para LCD 16×2 com PCF8574."""

    def __init__(self, i2c: I2C, addr: int = 0x27, cols: int = 16, rows: int = 2):
        self.i2c  = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self._bl  = _BL
        self._init_display()

    def _write_byte(self, data: int):
        self.i2c.writeto(self.addr, bytes([data | self._bl]))

    def _pulse_enable(self, data: int):
        self._write_byte(data | _EN)
        time.sleep_us(1)
        self._write_byte(data & ~_EN)
        time.sleep_us(50)

    def _write4(self, data: int):
        self._write_byte(data)
        self._pulse_enable(data)

    def _send(self, data: int, mode: int = 0):
        """Envia byte em modo 4-bit."""
        high = (data & 0xF0) | mode
        low  = ((data << 4) & 0xF0) | mode
        self._write4(high)
        self._write4(low)

    def _cmd(self, cmd: int):
        self._send(cmd, 0)
        time.sleep_us(100)

    def _char(self, char: int):
        self._send(char, _RS)

    def _init_display(self):
        time.sleep_ms(50)
        self._write4(0x30); time.sleep_ms(5)
        self._write4(0x30); time.sleep_us(100)
        self._write4(0x30); time.sleep_us(100)
        self._write4(0x20)   # modo 4 bits
        self._cmd(0x28)      # 4-bit, 2 linhas, 5x8
        self._cmd(0x0C)      # display on, cursor off
        self._cmd(0x06)      # entrada da esquerda para direita
        self.clear()

    def clear(self):
        self._cmd(0x01)
        time.sleep_ms(2)

    def write(self, col: int, row: int, text: str):
        """Escreve texto na posição (col, row)."""
        row_offsets = [0x00, 0x40]
        addr = 0x80 | (row_offsets[row % 2] + col)
        self._cmd(addr)
        for ch in text[:self.cols - col]:
            self._char(ord(ch))

    def backlight(self, on: bool = True):
        self._bl = _BL if on else 0
        self._write_byte(0)

    def scroll_left(self):
        self._cmd(0x18)

    def scroll_right(self):
        self._cmd(0x1C)
