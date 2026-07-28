# TCHAU.BG — skill

Skill para [Claude Code](https://claude.com/claude-code) que remove o fundo de
fotos e devolve **PNG com transparência**, em lote e 100% local. É a versão
linha de comando do app web [TCHAU.BG](https://github.com/drudif/tchaubg).

Peça em português mesmo — "tira o fundo dessas fotos", "recorta essa galera",
"quero em PNG transparente" — e o agente escolhe o modelo, roda o lote,
**olha o resultado** e refaz se a borda sair suja.

## Instalar

```bash
git clone git@github.com:drudif/tchaubgSKILL.git ~/.claude/skills/tchau-bg
pip install -r ~/.claude/skills/tchau-bg/requirements.txt
```

O primeiro uso baixa o modelo (~1 GB, uma vez, fica em `~/.u2net`). Depois
disso funciona offline.

## Usar direto, sem agente

```bash
python3 scripts/tchaubg.py --check              # checa o ambiente
python3 scripts/tchaubg.py FOTOS/ --out SAIDA/  # lote inteiro
python3 scripts/tchaubg.py a.jpg --trim --matting
```

| Flag | Efeito |
|---|---|
| `--out DIR` | pasta de saída (padrão: `<entrada>/recortados`) |
| `--model X` | troca o modelo — `--check` lista os 7 disponíveis |
| `--trim` / `--pad N` | corta no limite do recorte, com margem opcional |
| `--matting` | bordas suaves (cabelo, pelo). ~3x mais lento |
| `--smooth` | limpa pontinhos soltos de fundo |
| `--max-side N` | reduz o lado maior antes de processar |
| `--recursive` | varre subpastas |
| `--force` | reprocessa o que já existe |
| `--json` | relatório em JSON no stdout |

Aceita jpg, png, webp, bmp, tiff e heic. Nunca sobrescreve os originais.
Referência de velocidade: ~5s por imagem em Apple Silicon, ~12s em CPU de
servidor.

## Ferramentas usadas

O recorte é trabalho de projetos de código aberto de outras pessoas:

| Projeto | Licença | Papel |
|---|---|---|
| [BiRefNet](https://github.com/ZhengPeng7/BiRefNet) (ZhengPeng7) — pesos `BiRefNet-portrait` | MIT | separa a pessoa do fundo |
| [rembg](https://github.com/danielgatis/rembg) (Daniel Gatis) | MIT | baixa o modelo, roda a inferência, devolve o alpha |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) (Microsoft) | MIT | executa o modelo em CPU |
| [Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU (HPND) | leitura e escrita das imagens |
| [pillow-heif](https://github.com/bigcat88/pillow_heif) | BSD-3-Clause | HEIC/HEIF do iPhone |
| [NumPy](https://github.com/numpy/numpy) / [SciPy](https://github.com/scipy/scipy) / [pymatting](https://github.com/pymatting/pymatting) | BSD-3-Clause / BSD-3-Clause / MIT | array, filtros e alpha matting |

Skill escrita com [Claude Code](https://claude.com/claude-code).

> **Ressalva de licença:** as wheels binárias do `pillow-heif` embutem libheif e
> libde265 (LGPLv3), x265 (**GPLv2**) e libaom (BSD-3) — por causa do x265 a
> wheel é GPLv2. O código deste repositório é MIT; a obrigação copyleft só
> aparece se você redistribuir um binário com o `pillow-heif` embutido. Sem
> essa dependência, tudo segue funcionando exceto HEIC.

## Licença

[MIT](LICENSE) — © 2026 Fernando Drudi.
