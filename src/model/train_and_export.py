"""
src/model/train_and_export.py
─────────────────────────────
Pipeline Deep Learning para sistema RFID:
  1. Gera dataset sintético de acessos temporais
  2. Treina MLP com backprop completo
  3. Poda por magnitude (|w| < 0.05)
  4. Quantiza float32 → int8
  5. Exporta model.py para a Raspberry Pi Pico 2W
 
Executar no PC:  python src/model/train_and_export.py
Requer:          pip install numpy
"""
 
import numpy as np
import random, math
from pathlib import Path
 
random.seed(42)
np.random.seed(42)
 
SEQ_LEN    = 8
INPUT_DIM  = 4
FLAT_DIM   = SEQ_LEN * INPUT_DIM   # 32
HIDDEN1    = 32
HIDDEN2    = 16
N_CLASSES  = 3
EPOCHS     = 3000
LR         = 0.01
PRUNE_TH   = 0.05
OUTPUT_DIR = Path(__file__).parent
 
 
# ════════════════════════════════════════════════════════
# 1. GERAÇÃO DO DATASET
#    Alinhado com os padrões do test_model.py:
#    NORMAL:    hora 0.3-0.7, dt 0.04-0.9,  uid variado
#    SUSPEITO:  primeiros 4 normais (hora 0.3-0.7),
#               últimos 4 noturnos (hora 0.0-0.1),
#               dt 0.04-0.9
#    BLOQUEADO: dt << 0.001 (rajada), hora qualquer
# ════════════════════════════════════════════════════════
 
def gen_sequence(uid_hash, label):
    seq = []
    if label == 0:                          # NORMAL
        for _ in range(SEQ_LEN):
            h  = random.uniform(0.3, 0.7)
            d  = random.randint(1, 5) / 7
            dt = random.uniform(0.04, 0.9)
            seq.append([h, d, dt, uid_hash / 255])
 
    elif label == 1:                        # SUSPEITO: transição dia→noite
        for i in range(SEQ_LEN):
            if i < SEQ_LEN // 2:
                h  = random.uniform(0.3, 0.7)
                d  = random.randint(1, 5) / 7
            else:
                h  = random.uniform(0.0, 0.25)   # noturno/madrugada
                d  = random.randint(0, 6) / 7
            dt = random.uniform(0.04, 0.9)
            seq.append([h, d, dt, uid_hash / 255])
 
    else:                                   # BLOQUEADO: rajada rápida
        h_base = random.uniform(0.0, 1.0)
        for _ in range(SEQ_LEN):
            h  = float(np.clip(h_base + random.gauss(0, 0.01), 0, 1))
            d  = random.randint(0, 6) / 7
            dt = random.uniform(0.00001, 0.0004)
            seq.append([h, d, dt, uid_hash / 255])
 
    return np.array(seq, dtype=np.float32)
 
 
def make_dataset(n_per_class=200):
    uids = [random.randint(0, 255) for _ in range(10)]
    X, y = [], []
    for _ in range(n_per_class):
        for label in range(N_CLASSES):
            X.append(gen_sequence(random.choice(uids), label))
            y.append(label)
    return np.array(X).reshape(len(X), -1), np.array(y)
 
 
print("=" * 55)
print("  RFID Deep Learning — Pico 2W + Freenove")
print("=" * 55)
X_train, y_train = make_dataset(200)
X_val,   y_val   = make_dataset(50)
print(f"\n[1/4] Dataset: {len(X_train)} treino / {len(y_val)} validação")
 
 
# ════════════════════════════════════════════════════════
# 2. MLP com backprop completo
# ════════════════════════════════════════════════════════
 
def _softmax(z):
    e = np.exp(z - z.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)
 
def _relu(z):   return np.maximum(0, z)
def _relu_d(z): return (z > 0).astype(np.float32)
 
def _w(r, c):
    return (np.random.randn(r, c) * np.sqrt(2.0 / c)).astype(np.float32)
 
W1 = _w(FLAT_DIM, HIDDEN1);  b1 = np.zeros(HIDDEN1, np.float32)
W2 = _w(HIDDEN1,  HIDDEN2);  b2 = np.zeros(HIDDEN2, np.float32)
Wo = _w(HIDDEN2,  N_CLASSES); bo = np.zeros(N_CLASSES, np.float32)
 
def forward(X):
    z1 = X  @ W1 + b1;  a1 = _relu(z1)
    z2 = a1 @ W2 + b2;  a2 = _relu(z2)
    zo = a2 @ Wo + bo
    return _softmax(zo), a1, a2, z1, z2
 
def accuracy(X, y):
    probs, *_ = forward(X)
    return (probs.argmax(1) == y).mean()
 
print("\n[2/4] Treinamento...")
BATCH = 32
for ep in range(1, EPOCHS + 1):
    perm = np.random.permutation(len(X_train))
    for s in range(0, len(X_train), BATCH):
        idx = perm[s:s+BATCH]
        xb, yb = X_train[idx], y_train[idx]
        n = len(yb)
 
        probs, a1, a2, z1, z2 = forward(xb)
        oh = np.zeros_like(probs); oh[np.arange(n), yb] = 1
        dzo = (probs - oh) / n
 
        dWo = np.clip(a2.T @ dzo, -1, 1);  dbo = np.clip(dzo.sum(0), -1, 1)
        da2 = dzo @ Wo.T
        dz2 = da2 * _relu_d(z2)
        dW2 = np.clip(a1.T @ dz2, -1, 1);  db2 = np.clip(dz2.sum(0), -1, 1)
        da1 = dz2 @ W2.T
        dz1 = da1 * _relu_d(z1)
        dW1 = np.clip(xb.T @ dz1, -1, 1);  db1 = np.clip(dz1.sum(0), -1, 1)
 
        Wo -= LR * dWo;  bo -= LR * dbo
        W2 -= LR * dW2;  b2 -= LR * db2
        W1 -= LR * dW1;  b1 -= LR * db1
 
    if ep % 500 == 0:
        print(f"  Época {ep:4d}  treino={accuracy(X_train,y_train):.1%}  val={accuracy(X_val,y_val):.1%}")
 
print(f"  Acurácia final (val): {accuracy(X_val, y_val):.1%}")
 
 
# ════════════════════════════════════════════════════════
# 3. PODA
# ════════════════════════════════════════════════════════
print(f"\n[3/4] Poda (|w| < {PRUNE_TH})...")
all_W = [W1, b1, W2, b2, Wo, bo]
total = sum(w.size for w in all_W)
for w in all_W:
    w *= (np.abs(w) >= PRUNE_TH)
zerados = sum((w == 0).sum() for w in all_W)
print(f"  Pesos zerados: {zerados}/{total} ({zerados/total:.1%})")
print(f"  Acurácia pós-poda (val): {accuracy(X_val, y_val):.1%}")
 
 
# ════════════════════════════════════════════════════════
# 4. QUANTIZAÇÃO E EXPORT
# ════════════════════════════════════════════════════════
print("\n[4/4] Quantização float32 → int8 + export...")
 
def quant(W):
    mv = float(np.max(np.abs(W)))
    if mv == 0:
        return np.zeros_like(W, dtype=np.int8), 1.0
    sc = mv / 127.0
    return np.clip(np.round(W / sc), -128, 127).astype(np.int8), sc
 
W1q, sW1 = quant(W1);  b1q, sb1 = quant(b1)
W2q, sW2 = quant(W2);  b2q, sb2 = quant(b2)
Woq, sWo = quant(Wo);  boq, sbo = quant(bo)
 
print(f"  Memória: {total*4} B (float32) → {total} B (int8)  (4× menor)")
 
def fl(a): return a.flatten().tolist()
 
model_py = f'''# model.py — AUTO-GERADO — NAO EDITAR
# RFID Deep Learning: MLP Dense({HIDDEN1},ReLU)→Dense({HIDDEN2},ReLU)→Dense({N_CLASSES},Softmax) int8
# Upload: mpremote cp src/model/model.py :model.py
import math
 
SW1={sW1:.10f}; SB1={sb1:.10f}
SW2={sW2:.10f}; SB2={sb2:.10f}
SWO={sWo:.10f}; SBO={sbo:.10f}
 
W1={fl(W1q)}
B1={fl(b1q)}
W2={fl(W2q)}
B2={fl(b2q)}
WO={fl(Woq)}
BO={fl(boq)}
 
FLAT={FLAT_DIM}; H1={HIDDEN1}; H2={HIDDEN2}; NC={N_CLASSES}; SL={SEQ_LEN}; IN=4
 
def _relu(x): return x if x > 0 else 0.0
 
def predict(features):
    """
    features: lista de SL timesteps, cada um com IN floats
              Ex: [[hora/24, dia/7, delta_t, uid_hash/255], ...]
    Retorna:  [prob_normal, prob_suspeito, prob_bloqueado]
    """
    x = [v for step in features for v in step]
    a1 = [_relu(sum(W1[i*H1+j]*x[i] for i in range(FLAT))*SW1 + B1[j]*SB1)
          for j in range(H1)]
    a2 = [_relu(sum(W2[i*H2+j]*a1[i] for i in range(H1))*SW2 + B2[j]*SB2)
          for j in range(H2)]
    z  = [sum(WO[i*NC+k]*a2[i] for i in range(H2))*SWO + BO[k]*SBO
          for k in range(NC)]
    zm = max(z); ex = [math.exp(v - zm) for v in z]; s = sum(ex)
    return [e/s for e in ex]
 
LABELS = ["NORMAL", "SUSPEITO", "BLOQUEADO"]
 
def classify(features):
    p = predict(features); i = p.index(max(p))
    return LABELS[i], round(p[i]*100)
'''
 
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "model.py").write_text(model_py)
 
print(f"  Salvo: {OUTPUT_DIR}/model.py ({len(model_py):,} bytes)")
print("\n" + "="*55)
print("  CONCLUIDO!")
print("  mpremote cp src/model/model.py :model.py")
print("="*55)
