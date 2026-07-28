---
name: tchau-bg
description: Remove o fundo de fotos e devolve PNG com transparência, em lote e localmente. Use sempre que o usuário pedir para tirar/remover o fundo de uma foto, recortar uma pessoa ou objeto, "deixar o fundo transparente", gerar PNG sem fundo, fazer cutout/recorte para colar em outro layout, isolar alguém de uma foto de time/elenco, ou preparar retratos para deck/site. Também quando mencionar "remove background", "rembg", "tchau bg", "sem fundo". Aceita jpg, png, webp, bmp e tiff — HEIC precisa ser convertido antes.
compatibility: Requer python3 (3.9+) com rembg, onnxruntime e Pillow (pip install -r requirements.txt). Roda offline em CPU depois de baixar o modelo (~1 GB, uma vez). Não lê HEIC.
---

# TCHAU.BG

Recorta fundo com [rembg](https://github.com/danielgatis/rembg) + modelo
**birefnet-portrait**. O script `scripts/tchaubg.py` faz o trabalho pesado; o
seu papel é **escolher o modelo certo**, **verificar o recorte com os próprios
olhos** e iterar quando a borda sair suja.

Versão CLI do app web [TCHAU.BG](https://github.com/drudif/tchaubg).

## Passo 1 — Checar o ambiente

```bash
python3 scripts/tchaubg.py --check
```

Devolve JSON com versões, providers do onnxruntime e os modelos já baixados.
Se `rembg` não importar, instale antes:

```bash
pip install -r requirements.txt
```

Prefira um venv se o usuário tiver um por perto — o `onnxruntime` é pesado e
não vale poluir o Python do sistema. Se o projeto do usuário já tem `.venv`,
use o Python de lá.

## Passo 2 — Rodar

```bash
python3 scripts/tchaubg.py FOTOS/ --out RECORTES/
```

Aceita arquivos soltos e pastas na mesma chamada. **Passe tudo de uma vez**: o
modelo carrega uma só vez e é reaproveitado; chamar o script por imagem
multiplica o tempo à toa.

Sem `--out`, a saída vai para `<pasta de entrada>/recortados`. O script nunca
sobrescreve o original e pula o que já existe (use `--force` para refazer).

Flags que importam:

| Flag | Quando usar |
|---|---|
| `--trim` (+ `--pad N`) | o usuário vai colar o recorte em outro layout — corta o vazio em volta |
| `--matting` | cabelo solto, pelo, tule, fumaça. ~3x mais lento, borda bem melhor |
| `--smooth` | sobraram pontinhos soltos de fundo pela imagem |
| `--max-side 2000` | fotos gigantes (câmera profissional) e a máquina está apertada de RAM |
| `--recursive` | a pasta tem subpastas |
| `--json` | você vai processar o relatório programaticamente |
| `--model X` | ver Passo 3 |

Tempo de referência: ~5s por imagem num Apple Silicon (CoreML), ~12s numa CPU
de servidor. O primeiro uso baixa o modelo (~1 GB).

## Passo 3 — Escolher o modelo

O padrão `birefnet-portrait` é o melhor para **gente** — foi treinado em
retrato e é o único que resolve fio de cabelo decentemente. Troque quando:

- **objeto, produto, comida, animal** → `birefnet-general`
- **máquina fraca ou lote enorme** → `birefnet-general-lite` ou `silueta`
- **corpo inteiro em cena movimentada** → `u2net_human_seg`
- **o portrait comeu parte do corpo** (pessoa distante, de costas, muito pequena
  no quadro) → tente `birefnet-general`; é sintoma clássico do modelo de retrato

`--check` lista todos com uma linha de descrição.

## Passo 4 — Verificar (obrigatório)

**Abra pelo menos um PNG de saída com a ferramenta Read e OLHE.** O PNG
transparente aparece sobre fundo escuro no viewer, o que já denuncia halo
claro. Cheque nesta ordem:

1. **Sobrou fundo?** halo/franja da cor do fundo antigo em volta do contorno →
   `--matting`.
2. **Comeu parte da pessoa?** braço, mão, cabelo, alça de bolsa faltando →
   outro modelo (Passo 3). Recorrente em foto com pouco contraste
   pessoa/fundo.
3. **Cabelo virou capacete?** silhueta dura no topo da cabeça → `--matting`.
4. **Ilhas soltas** de fundo espalhadas → `--smooth`.
5. **Vieram duas pessoas quando o usuário queria uma?** o modelo não separa
   indivíduos — avise e ofereça cortar manualmente antes de processar.

Em lote, olhe a primeira, uma do meio e a última. Se uma delas estiver ruim,
rode o lote inteiro de novo com o ajuste (`--force`), não conserte uma só.

## Passo 5 — Entregar

- Nunca sobrescreva os originais (o script já protege, mas não force `--out`
  para a pasta de origem).
- Relate: quantas saíram, quais deram erro e por quê, modelo e flags usados,
  onde ficaram os arquivos.
- Se o usuário for usar em web, ofereça converter para WebP com alpha —
  costuma cair 60–80% do peso:
  `python3 -c "from PIL import Image; im=Image.open('x.png'); im.save('x.webp', quality=90)"`

## Limitações que valem avisar

- **HEIC/HEIF do iPhone não é lido** — a única biblioteca prática para isso
  (`pillow-heif`) tem wheel GPLv2 e ficou de fora de propósito. Se o usuário
  trouxer HEIC, converta antes e siga:
  `sips -s format jpeg foto.heic --out foto.jpg` (macOS) ou
  `ffmpeg -i foto.heic foto.jpg`. Um `.heic` na pasta é simplesmente ignorado
  pelo script, com aviso no stderr.
- Fundo da cor da roupa, vidro, reflexo e sombra projetada são os casos em que
  qualquer um desses modelos erra. Não insista em flag: avise o usuário.
- O modelo devolve a máscara do assunto principal — não separa duas pessoas
  coladas nem escolhe "a da esquerda".
- Roda 100% local, nada sai da máquina. Vale dizer isso quando as fotos forem
  de terceiros (RH, elenco, clientes).

## Créditos

| Projeto | Licença |
|---|---|
| [BiRefNet](https://github.com/ZhengPeng7/BiRefNet) — pesos `BiRefNet-portrait` | MIT |
| [rembg](https://github.com/danielgatis/rembg) | MIT |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT |
| [Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU (HPND) |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause |
