# src/hardware/main.py
# ────────────────────────────────────────────────────────────
# Sistema RFID + Deep Learning — Raspberry Pi Pico W
#
# Hardware:
#   RC522 → SPI0 (GP16 MISO, GP17 CS, GP18 SCK, GP19 MOSI, GP20 RST)
#
# Upload:
#   mpremote cp src/hardware/main.py       :main.py
#   mpremote cp src/hardware/rfid_rc522.py :rfid_rc522.py
#   mpremote cp src/model/model.py         :model.py
# ────────────────────────────────────────────────────────────

from machine import Pin, SPI
import time, json, network, ntptime

from rfid_rc522 import MFRC522
from model      import classify, LABELS

# ── Wi-Fi + NTP ───────────────────────────────────────────────
WIFI_SSID  = "brisa-3481072"
WIFI_SENHA = "lzvsqyms"
UTC_OFFSET = -3  # Brasília (UTC-3)

def sync_ntp():
    print("Conectando ao Wi-Fi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_SENHA)

    for _ in range(20):
        if wlan.isconnected():
            break
        time.sleep(0.5)
        print(".", end="")
    print()

    if not wlan.isconnected():
        print("AVISO: Wi-Fi falhou — horario sera o tempo de execucao")
        return

    print(f"Wi-Fi conectado: {wlan.ifconfig()[0]}")
    try:
        ntptime.settime()
        # Ajusta fuso horário (NTP retorna UTC)
        t = time.time() + UTC_OFFSET * 3600
        tm = time.localtime(t)
        # MicroPython RTC: (ano, mes, dia, dia_semana, hora, min, seg, subseg)
        from machine import RTC
        RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
        print(f"Horario sincronizado: {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}")
    except Exception as e:
        print(f"AVISO: NTP falhou — {e}")

sync_ntp()

# ── RC522 via SPI0 ───────────────────────────────────────────
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
rfid = MFRC522(spi=spi, gpioRst=Pin(20), gpioCs=Pin(17))

# ── Banco de UIDs + histórico persistido ──────────────────────
DB_FILE = "rfid_db.json"

def db_load():
    try:
        with open(DB_FILE) as f:
            return json.load(f)
    except:
        return {}

def db_save(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = db_load()

# ── Helpers ───────────────────────────────────────────────────
def uid_to_hex(uid_bytes):
    return "".join(f"{b:02X}" for b in uid_bytes)

def cadastrar(uid_hex, uid_hash):
    if uid_hex not in db:
        db[uid_hex] = {"nome": f"User_{uid_hex[:4]}", "hash": uid_hash, "historico": []}
        db_save(db)
        print(f"  >> CADASTRADO: {uid_hex}")
    else:
        print(f"  >> JA EXISTE:  {uid_hex} ({db[uid_hex]['nome']})")

# ── Histórico temporal persistido ─────────────────────────────
WINDOW = 8

def update_history(uid_hex, uid_hash):
    now  = time.localtime()
    hora = now[3] * 3600 + now[4] * 60 + now[5]
    dia  = now[6]

    hist = db[uid_hex].get("historico", [])

    delta = (hora - hist[-1][2] * 86400) / 86400 if hist else 0.5
    delta = max(0, delta)

    feat = [hora / 86400, dia / 7, delta, uid_hash / 255]
    hist.append(feat)
    if len(hist) > WINDOW:
        hist.pop(0)

    db[uid_hex]["historico"] = hist
    db_save(db)

    padded = hist[:]
    while len(padded) < WINDOW:
        padded.insert(0, feat)

    return padded[-WINDOW:]

# ── Inicialização ─────────────────────────────────────────────
print("=" * 45)
print("  RFID + Deep Learning — Pico W")
print("=" * 45)
print("Comandos no REPL:")
print("  cadastrar('<UID_HEX>', <uid_hash>)")
print("Aguardando cartao...\n")

# ── Loop principal ─────────────────────────────────────────────
while True:
    stat, tag_type = rfid.request(rfid.REQIDL)
    if stat != rfid.OK:
        time.sleep_ms(100)
        continue

    stat, raw_uid = rfid.anticoll()
    if stat != rfid.OK:
        continue

    uid_hex  = uid_to_hex(raw_uid)
    uid_hash = sum(raw_uid) % 256
    t_start  = time.ticks_ms()

    if uid_hex not in db:
        print(f"[NEGADO]    UID={uid_hex}  (nao cadastrado)")
        print(f"            Para cadastrar: cadastrar('{uid_hex}', {uid_hash})")
        time.sleep_ms(1500)
        continue

    features    = update_history(uid_hex, uid_hash)
    label, conf = classify(features)
    t_ms        = time.ticks_diff(time.ticks_ms(), t_start)

    lt   = time.localtime()
    ts   = f"{lt[3]:02d}:{lt[4]:02d}:{lt[5]:02d}"
    nome = db[uid_hex]["nome"]
    n_hist = len(db[uid_hex]["historico"])

    print(f"[{label:10s}] UID={uid_hex}  {nome}  conf={conf}%  T={t_ms}ms  {ts}  hist={n_hist}/8")

    time.sleep_ms(1500)