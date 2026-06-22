# Diagrama de Fiação

## RC522 → Pico 2W (SPI0)

```
RC522 Pin   Pico 2W Pin   GPIO    Cor sugerida
─────────────────────────────────────────────
SDA (SS)    Pino 22       GP17    Amarelo
SCK         Pino 24       GP18    Laranja
MOSI        Pino 25       GP19    Verde
MISO        Pino 21       GP16    Azul
GND         Pino 38       GND     Preto
RST         Pino 26       GP20    Branco
3.3V        Pino 36       3V3     Vermelho
```

> ⚠️ O RC522 opera a 3.3V. Não conecte ao 5V ou ao VBUS.

## LCD 16×2 (PCF8574 I2C) → Pico 2W (I2C1)

```
LCD Pin     Pico 2W Pin   GPIO    Cor sugerida
─────────────────────────────────────────────
SDA         Pino 11       GP8     Azul
SCL         Pino 12       GP9     Laranja
VCC         Pino 40       VBUS    Vermelho
GND         Pino 38       GND     Preto
```

> O LCD precisa de **5V (VBUS)** para o backlight funcionar.
> Endereço I2C padrão do PCF8574: `0x27`
> Para confirmar: `i2c.scan()` no REPL deve retornar `[39]` (= 0x27).

## LEDs, Buzzer e Botão

```
Componente  Pico 2W Pin   GPIO    Obs
────────────────────────────────────────────────────
LED verde   Pino 4        GP2     + resistor 220Ω
LED amarelo Pino 5        GP3     + resistor 220Ω
LED vermelho Pino 6       GP4     + resistor 220Ω
Buzzer (+)  Pino 7        GP5     buzzer ativo 3.3V
Botão       Pino 20       GP15    pull-up interno
```

Todos os cátodos de LED e GND do buzzer → trilho GND da breadboard.

## Vista geral da breadboard

```
  VBUS ─── VCC_LCD
  3V3  ─── VCC_RC522
  GND  ─── trilho GND ──┬── RC522 GND
                        ├── LCD GND
                        ├── cátodos LEDs
                        └── buzzer GND
  GP2  ─── R220Ω ── LED verde  (anodo)
  GP3  ─── R220Ω ── LED amarelo (anodo)
  GP4  ─── R220Ω ── LED vermelho (anodo)
  GP5  ─── buzzer (+)
  GP15 ─── botão ── GND  (pull-up interno, ativo em LOW)
  GP6  ─── LCD SDA
  GP7  ─── LCD SCL
  GP16 ─── RC522 MISO
  GP17 ─── RC522 SDA/SS
  GP18 ─── RC522 SCK
  GP19 ─── RC522 MOSI
  GP20 ─── RC522 RST
```
