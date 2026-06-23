# 🔐 RFID Deep Learning Access Control
### Raspberry Pi Pico W + Wi-Fi NTP + JSON DB

> Sistema de controle de acesso inteligente com **reconhecimento comportamental por rede neural profunda**. Utiliza o Wi-Fi do Pico W para sincronização precisa de horário via NTP, aprende o padrão de uso de cada cartão RFID e detecta anomalias em tempo real, persistindo o histórico em formato JSON.

[![MicroPython](https://img.shields.io/badge/MicroPython-1.23-blue?logo=python)](https://micropython.org)
[![RP2040](https://img.shields.io/badge/RP2040-Pico%20W-red)](https://www.raspberrypi.com/products/raspberry-pi-pico-w/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 Índice

- [Visão geral](#-visão-geral)
- [Hardware necessário](#-hardware-necessário)
- [Arquitetura da rede neural](#-arquitetura-da-rede-neural)
- [Estrutura do repositório](#-estrutura-do-repositório)
- [Instalação e Configuração](#-instalação-e-configuração)
- [Fiação (Wiring)](#-fiação-wiring)
- [Como usar (REPL)](#-como-usar-repl)
- [Extensões sugeridas](#-extensões-sugeridas)
- [Licença](#-licença)

---

## 🎯 Visão geral

Diferente de sistemas tradicionais de RFID que apenas validam UIDs estáticos, este projeto embarca uma **rede neural LSTM** para aprender o *comportamento temporal* de cada cartão. Para garantir precisão na coleta temporal, o sistema se conecta ao Wi-Fi local e sincroniza o relógio interno (RTC) via servidor NTP.

O modelo identifica automaticamente:
* **Cartão clonado:** UID válido, mas padrão de horário anômalo.
* **Cartão emprestado:** Uso fora do perfil temporal do dono.
* **Acesso normal:** Perfil consistente com o histórico persistido no banco de dados.

```text
Leitor RC522  ──►  Pico W (RP2040)  ──►  LSTM int8  ──►  Console/REPL
                         │
                    Wi-Fi (NTP) + rfid_db.json

---

## 🔧 Hardware necessário

Todos os componentes abaixo fazem parte do **Freenove Ultimate Starter Kit (fnk0058)**:

| Componente | Qtd | Pino(s) Pico 2W |
|---|---|---|
| Raspberry Pi Pico W | 1 | — |
| Módulo RFID RC522 | 1 | SPI0: GP16/17/18/19 + GP20 |
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

**Por que NTP?** A rede neural depende fortemente da precisão do horário (hora/86400). O sincronismo NTP via Wi-Fi garante que o histórico alimentado na LSTM seja real e preciso, armazenando a janela dos últimos 8 acessos diretamente na memória flash (rfid_db.json).
---

## 📁 Estrutura do repositório

```
rfid-deeplearning-picow/
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
│       ├── main.py              ← código principal da Pico 2W
│       └── rfid_rc522.py        ← driver RC522 MicroPython
└── rfid_db.json                 ← (Gerado na placa) Banco de UIDs e histórico
```

---

## ⚡ Instalação rápida

### 1. Configurar credenciais Wi-Fi
Antes de fazer o upload, abra o arquivo src/hardware/main.py e insira suas credenciais de rede:

WIFI_SSID  = "SUA_REDE_WIFI"
WIFI_SENHA = "SUA_SENHA"
UTC_OFFSET = -3  # Ajuste seu fuso horário
```

### 2. Instale dependências Pico W

```bash
import mip
mip.install("mfrc522")
```

### 3. Upload dos arquivos

Utilize o mpremote para enviar o código para a placa:

```bash
pip install mpremote

mpremote cp src/model/model.py         :model.py
mpremote cp src/hardware/main.py       :main.py
mpremote cp src/hardware/rfid_rc522.py :rfid_rc522.py
```

## 🔌 Fiação

Veja [`docs/wiring.md`](docs/wiring.md) para o diagrama completo. Resumo:

```
RC522 (SPI)                    Pico W
─────────────────────────────────────
SDA  (SS)   ──────────────►  GP17
SCK         ──────────────►  GP18
MOSI        ──────────────►  GP19
MISO        ──────────────►  GP16
GND         ──────────────►  GND
RST         ──────────────►  GP20
3.3V        ──────────────►  3.3V (pino 36)

---
```

## 💻 Como usar (REPL)

Todo o controle do sistema é feito através da porta serial. Monitore a placa utilizando:

```bash
mpremote connect auto repl

```

## 📖 INICIALIZAÇÃO
```

Conectando ao Wi-Fi...
.....
Wi-Fi conectado: 192.168.0.100
Horario sincronizado: 14:30:00
=============================================
  RFID + Deep Learning — Pico W
=============================================
Comandos no REPL:
  cadastrar('<UID_HEX>', <uid_hash>)
Aguardando cartao...
```

### Cadastrar novo cartão
Quando você encosta um cartão não cadastrado, o log informará os dados necessários para o cadastro. No terminal do REPL, digite o comando sugerido:

```python
>>> cadastrar('A3F2B1C0', 145)
  >> CADASTRADO: A3F2B1C0

O usuário será salvo automaticamente no rfid_db.json.

```

### Leitura normal
Encoste um cartão cadastrado para disparar a inferência LSTM:

[NORMAL    ] UID=A3F2B1C0  User_A3F2  conf=97%  T=2ms  14:32:15  hist=1/8
[NORMAL    ] UID=A3F2B1C0  User_A3F2  conf=95%  T=2ms  14:45:10  hist=2/8
[SUSPEITO  ] UID=A3F2B1C0  User_A3F2  conf=88%  T=2ms  03:17:11  hist=3/8


```
```

## 📄 Licença
```

Distribuído sob licença MIT. Veja [LICENSE](LICENSE) para detalhes.


```

<div align="center">
<strong>Freenove Ultimate Starter Kit + Raspberry Pi Pico 2W</strong><br>
Feito com MicroPython · RP2350 · LSTM int8
</div>
