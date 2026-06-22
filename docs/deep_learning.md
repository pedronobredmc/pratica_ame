# Pipeline de Deep Learning

## Visão geral

```
Logs RFID  ─►  Features  ─►  LSTM × 2  ─►  Dense  ─►  Softmax
                   │                                       │
              Janela de               Detecção de    NORMAL / SUSPEITO
              8 acessos               anomalia       / BLOQUEADO
```

## Extração de features

Cada acesso é representado por 4 valores normalizados:

| Feature | Fórmula | Significado |
|---|---|---|
| `hora` | `hora_segundos / 86400` | Posição no dia (0–1) |
| `dia` | `dia_semana / 7` | Dia da semana (0=seg, 1=dom) |
| `delta_t` | `intervalo / 86400` | Tempo desde o acesso anterior |
| `uid_hash` | `(uid[0]^uid[1]^...) / 255` | Identidade do cartão |

A rede recebe uma **janela deslizante** dos últimos 8 acessos.

## Arquitetura LSTM

```
Input: (batch, 8, 4)
   │
LSTM Layer 1  — 16 unidades, retorna último estado h
   │           portas: input(i), forget(f), output(o), cell(g)
   │           h_t = o ⊙ tanh(c_t)
   │           c_t = f ⊙ c_{t-1} + i ⊙ g
   │
LSTM Layer 2  — 16 unidades, recebe h1 repetido
   │
Dense(8, ReLU)
   │
Dense(3, Softmax) ─► [P(NORMAL), P(SUSPEITO), P(BLOQUEADO)]
```

## Poda por magnitude

Remove pesos com `|w| < 0.05`. Justificativa:

- Pesos pequenos contribuem pouco para as ativações
- Reduz ~40% dos parâmetros sem perda perceptível de acurácia
- Pesos zerados são ignorados na inferência int8

## Quantização int8

Conversão simétrica por camada:

```
scale  = max(|W|) / 127
W_int8 = round(W / scale).clip(-128, 127)

# Na inferência:
ativacao = sum(W_int8[i] * x[i]) * scale + bias
```

Benefícios no Pico 2W:
- 4× menos memória flash
- Operações inteiras são mais rápidas no RP2350
- Sem dependência de bibliotecas de ponto flutuante pesadas

## Detecção de anomalia

O modelo aprende os padrões de acesso durante o treino:

| Padrão detectado | Classe |
|---|---|
| Acesso no horário habitual, intervalo normal | NORMAL |
| Acesso em horário incomum para aquele cartão | SUSPEITO |
| Múltiplos acessos em < 30s (clone/ataque) | BLOQUEADO |

## Retreinando com dados reais

1. Conecte a Pico ao Wi-Fi e ative o log para arquivo
2. Após 1–2 semanas de uso, exporte o JSON de histórico
3. Substitua `make_dataset()` por um loader do arquivo real
4. Reexecute `train_and_export.py` e re-faça o upload do `model.py`
