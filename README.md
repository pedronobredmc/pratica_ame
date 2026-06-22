# 🔐 RFID Deep Learning Access Control
### Raspberry Pi Pico 2W + Freenove Ultimate Starter Kit

> Sistema de controle de acesso inteligente com **reconhecimento comportamental por rede neural profunda** — aprende o padrão de uso de cada cartão RFID e detecta anomalias em tempo real, exibindo o status no **display LCD 16×2** do kit.

[![MicroPython](https://img.shields.io/badge/MicroPython-1.23-blue?logo=python)](https://micropython.org)
[![RP2350](https://img.shields.io/badge/RP2350-Pico%202W-red)](https://www.raspberrypi.com/products/raspberry-pi-pico-2/)
[![Freenove](https://img.shields.io/badge/Kit-Freenove%20Ultimate-orange)](https://store.freenove.com/products/fnk0058)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Índice

- [Visão geral](#-visão-geral)
- [Hardware necessário](#-hardware-necessário)
- [Arquitetura da rede neural](#-arquitetura-da-rede-neural)
- [Estrutura do repositório](#-estrutura-do-repositório)
- [Instalação rápida](#-instalação-rápida)
- [Fiação](#-fiação)
- [Pipeline de deep learning](#-pipeline-de-deep-learning)
- [Como usar](#-como-usar)
- [Resultados esperados](#-resultados-esperados)
- [Extensões sugeridas](#-extensões-sugeridas)
- [Licença](#-licença)

---

## 🎯 Visão geral

A maioria dos sistemas RFID faz apenas uma coisa: verifica se o UID do cartão está numa lista autorizada. Este projeto vai além — uma **rede neural LSTM compacta** aprende o *comportamento temporal* de cada cartão (horários de acesso, frequência, padrão de uso) e detecta automaticamente:

| Situação | O que o sistema detecta |
|---|---|
| Cartão clonado | UID válido, mas padrão de horário anômalo |
| Cartão emprestado | Uso fora do perfil temporal do dono |
| Ataque de força bruta | Múltiplas leituras em sequência rápida |
| Acesso normal | Confirmado, LED verde + mensagem LCD |

O modelo é treinado no PC com Python puro, podado, quantizado em int8 e embarcado diretamente no Pico 2W — **sem SO, sem framework de ML, sem dependências externas**.

```
Leitor RC522  ──►  Pico 2W (RP2350)  ──►  LSTM int8  ──►  LCD 16×2
                        │                                      │
                    LED RGB                               Buzzer ativo
                    (status)                             (alerta sonoro)
```

---

## 🔧 Hardware necessário

Todos os componentes abaixo fazem parte do **Freenove Ultimate Starter Kit (fnk0058)**:

| Componente | Qtd | Pino(s) Pico 2W |
|---|---|---|
| Raspberry Pi Pico 2W | 1 | — |
| Módulo RFID RC522 | 1 | SPI0: GP18/19/16/17 + GP20 |
| Display LCD 16×2 (I2C PCF8574) | 1 | I2C1: GP6 (SDA) / GP7 (SCL) |
| LED verde | 1 | GP2 |
| LED amarelo | 1 | GP3 |
| LED vermelho | 1 | GP4 |
| Buzzer ativo | 1 | GP5 |
| Botão de cadastro | 1 | GP15 |
| Resistores 220 Ω | 3 | (série com LEDs) |
| Breadboard + jumpers | 1 | — |

> **Nota:** O RC522 do kit Freenove opera via **SPI a 3.3 V** — não conecte ao pino 5 V.

---

## 🧠 Arquitetura da rede neural

```
Entrada (janela temporal de 8 acessos):
  [hora_normalizada, dia_semana, intervalo_desde_ultimo, uid_embedding]
          │
    ┌─────▼──────┐
    │  LSTM  ×2  │  16 unidades ocultas por camada
    │  (temporal)│  aprende padrões de sequência
    └─────┬──────┘
          │
    ┌─────▼──────┐
    │  Dense 8   │  ReLU — extrai features de alto nível
    └─────┬──────┘
          │
    ┌─────▼──────┐
    │  Dense 3   │  Softmax
    └─────┬──────┘
          │
    NORMAL / SUSPEITO / BLOQUEADO
```

**Por que LSTM?** Diferente de um classificador estático, a LSTM mantém estado entre timesteps — captura que um acesso às 3h num cartão que sempre acessa às 9h é anômalo, mesmo que o UID seja válido.

**Complexidade embarcada:**
- Parâmetros totais: ~1.800
- Após poda (40%): ~1.080 pesos ativos
- Após quantização int8: **~1.1 KB** de memória de modelo
- Latência de inferência no RP2350: < 2 ms

---

## 📁 Estrutura do repositório

```
rfid-deeplearning-pico2w/
│
├── README.md                    ← este arquivo
├── LICENSE
├── requirements.txt             ← dependências Python (PC)
│
├── src/
│   ├── model/
│   │   ├── train_and_export.py  ← treino LSTM + poda + quantização
│   │   └── model.py             ← gerado automaticamente (upload Pico)
│   │
│   ├── hardware/
│   │   ├── main.py              ← código principal da Pico 2W
│   │   ├── lcd_i2c.py           ← driver LCD 16×2 via PCF8574
│   │   └── rfid_rc522.py        ← driver RC522 MicroPython
│   │
│   └── utils/
│       ├── data_logger.py       ← coleta e salva logs de acesso (PC)
│       └── visualize.py         ← plota histórico e anomalias (PC)
│
├── tests/
│   ├── test_model.py            ← valida acurácia pós-quantização
│   └── test_hardware.py         ← testa cada periférico isolado
│
├── notebooks/
│   └── exploratory_analysis.ipynb  ← análise do dataset de acessos
│
└── docs/
    ├── wiring.md                ← diagrama de fiação detalhado
    ├── deep_learning.md         ← explicação do pipeline ML
    └── lcd_commands.md          ← referência de comandos LCD
```

---

## ⚡ Instalação rápida

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/rfid-deeplearning-pico2w.git
cd rfid-deeplearning-pico2w
```

### 2. Instale dependências Python (PC)

```bash
pip install -r requirements.txt
```

### 3. Flash do MicroPython na Pico 2W

Segure **BOOTSEL** ao conectar USB. A Pico aparece como pendrive.
Baixe o firmware em [micropython.org/download/RPI_PICO2_W](https://micropython.org/download/RPI_PICO2_W/) e arraste o `.uf2`.

### 4. Instale drivers na Pico (via REPL)

```python
import mip
mip.install("mfrc522")      # driver RFID RC522
```

### 5. Treine e exporte o modelo

```bash
python src/model/train_and_export.py
# gera: src/model/model.py
```

### 6. Faça upload para a Pico 2W

```bash
pip install mpremote

mpremote cp src/model/model.py         :model.py
mpremote cp src/hardware/main.py       :main.py
mpremote cp src/hardware/lcd_i2c.py    :lcd_i2c.py
mpremote cp src/hardware/rfid_rc522.py :rfid_rc522.py
```

### 7. Monitore o serial

```bash
mpremote connect auto repl
```

---

## 🔌 Fiação

Veja [`docs/wiring.md`](docs/wiring.md) para o diagrama completo. Resumo:

```
RC522 (SPI)                    Pico 2W
─────────────────────────────────────
SDA  (SS)   ──────────────►  GP17
SCK         ──────────────►  GP18
MOSI        ──────────────►  GP19
MISO        ──────────────►  GP16
GND         ──────────────►  GND
RST         ──────────────►  GP20
3.3V        ──────────────►  3.3V (pino 36)

LCD 16×2 via PCF8574 (I2C)     Pico 2W
─────────────────────────────────────
SDA         ──────────────►  GP6
SCL         ──────────────►  GP7
VCC         ──────────────►  5V  (VBUS pino 40)
GND         ──────────────►  GND

LEDs (com resistor 220Ω)       Pico 2W
─────────────────────────────────────
LED verde   ──────────────►  GP2
LED amarelo ──────────────►  GP3
LED vermelho──────────────►  GP4
Buzzer (+)  ──────────────►  GP5
Botão       ──────────────►  GP15
```

> ⚠️ O LCD 16×2 com adaptador I2C (PCF8574) **precisa de 5 V** para o backlight. Use o pino VBUS (pino 40), não o 3.3 V.

---

## 🔬 Pipeline de deep learning

Veja [`docs/deep_learning.md`](docs/deep_learning.md) para detalhes completos.

```
1. COLETA        Logs de acesso (uid, timestamp, resultado)
      │
2. FEATURES      Janela deslizante de 8 acessos
      │          [hora/24, dia/7, Δt_normalizado, uid_hash/255]
      │
3. TREINO        LSTM(16) → LSTM(16) → Dense(8,ReLU) → Dense(3,Softmax)
      │          2.000 épocas · lr=0.001 · Adam
      │
4. PODA          Zera pesos com |w| < 0.05  (~40% esparsidade)
      │
5. QUANTIZAÇÃO   float32 → int8  (escala simétrica por camada)
      │
6. EXPORT        model.py com literais int8 + predict() puro MicroPython
      │
7. INFERÊNCIA    Pico 2W: < 2 ms por leitura RFID
```

---

## 📖 Como usar

### Modo cadastro (novo cartão)

Pressione e segure o **botão GP15** por 3 segundos → LCD exibe `CADASTRO ATIVO` → aproxime o cartão → sistema registra UID e cria perfil temporal inicial.

### Modo verificação (operação normal)

Aproxime qualquer cartão. O sistema executa:

1. Verifica se o UID existe na lista autorizada
2. Extrai features temporais da janela histórica
3. Executa inferência LSTM (< 2 ms)
4. Exibe resultado no LCD e aciona LED correspondente

### Saída esperada no LCD

```
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ ACESSO LIBERADO│    │ PADRAO ATIPICO │    │ ACESSO NEGADO  │
│ Joao  09:14    │    │ Cartao: A3F2   │    │ UID desconhec. │
└────────────────┘    └────────────────┘    └────────────────┘
   LED verde             LED amarelo           LED vermelho
```

### Log serial

```
[09:14:32] UID=A3F2B1C0  NORMAL     conf=97%  T=2ms
[09:14:45] UID=A3F2B1C0  NORMAL     conf=95%  T=2ms
[03:17:11] UID=A3F2B1C0  SUSPEITO   conf=88%  T=2ms  <- acesso noturno
[03:17:14] UID=A3F2B1C0  BLOQUEADO  conf=94%  T=2ms  <- multiplas tentativas
```

---

## 📊 Resultados esperados

| Métrica | Valor |
|---|---|
| Acurácia (validação) | ≥ 94% |
| Falsos positivos (bloqueio indevido) | < 3% |
| Latência de inferência (RP2350 150 MHz) | < 2 ms |
| Memória do modelo (flash) | ~1.1 KB |
| RAM em uso durante inferência | ~4 KB |

---

## 🚀 Extensões sugeridas

| Extensão | Complexidade | Descrição |
|---|---|---|
| Dashboard MQTT | ⭐⭐ | Publicar eventos via Wi-Fi para Node-RED/Grafana |
| Re-treino online | ⭐⭐⭐ | Atualizar pesos incrementalmente na própria Pico |
| Trava eletromagnética | ⭐ | Acionar relé no GP21 para controle físico de porta |
| Alerta Telegram | ⭐⭐ | Enviar UID + timestamp por bot Telegram via Wi-Fi |
| Múltiplos leitores | ⭐⭐⭐ | Usar segundo Pico como escravo via UART |

---

## 📄 Licença

Distribuído sob licença MIT. Veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">
<strong>Freenove Ultimate Starter Kit + Raspberry Pi Pico 2W</strong><br>
Feito com MicroPython · RP2350 · LSTM int8
</div>
