#!/usr/bin/env python3
"""
TCHAU.BG — remove o fundo de retratos em lote e salva PNG com transparência.

O modelo é carregado uma única vez e reaproveitado entre as imagens, então
processar 30 fotos numa chamada é muito mais rápido que 30 chamadas.

    python3 tchaubg.py FOTOS/ --out RECORTES/
    python3 tchaubg.py a.jpg b.png --trim --json
    python3 tchaubg.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
HEIC_EXTS = {".heic", ".heif"}  # não suportado: ver README (dependência GPLv2)

MODELS = {
    "birefnet-portrait": "retratos (padrão) — melhor recorte de cabelo",
    "birefnet-general": "objetos e cenas em geral",
    "birefnet-general-lite": "versão leve do general, mais rápida",
    "isnet-general-use": "alternativa leve, boa em objetos",
    "u2net": "clássico, rápido, bordas mais duras",
    "u2net_human_seg": "corpo humano inteiro, silhueta ampla",
    "silueta": "u2net reduzido (~43 MB), para máquinas apertadas",
}


def eprint(*a):
    print(*a, file=sys.stderr, flush=True)


def check() -> int:
    """Relata o ambiente em JSON, sem processar nada."""
    info = {"ok": True, "problemas": [], "modelos_disponiveis": MODELS}
    try:
        import rembg

        info["rembg"] = getattr(rembg, "__version__", "?")
    except Exception as e:
        info["ok"] = False
        info["rembg"] = None
        info["problemas"].append(f"rembg não importável: {e}. Rode: pip install -r requirements.txt")
    try:
        import onnxruntime

        info["onnxruntime"] = onnxruntime.__version__
        info["providers"] = onnxruntime.get_available_providers()
    except Exception as e:
        info["ok"] = False
        info["problemas"].append(f"onnxruntime não importável: {e}")
    try:
        import PIL

        info["pillow"] = PIL.__version__
    except Exception as e:
        info["ok"] = False
        info["problemas"].append(f"Pillow não importável: {e}")

    import os

    home = Path(os.environ.get("U2NET_HOME") or Path.home() / ".u2net")
    info["cache_modelos"] = str(home)
    info["modelos_baixados"] = sorted(p.name for p in home.glob("*.onnx")) if home.is_dir() else []
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["ok"] else 1


def collect(paths: list[str], recursive: bool) -> list[Path]:
    """Expande arquivos e diretórios numa lista ordenada e sem repetição."""
    out: list[Path] = []
    heic = 0
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            it = [f for f in (p.rglob("*") if recursive else p.iterdir()) if f.is_file()]
            out += [f for f in it if f.suffix.lower() in EXTS]
            heic += sum(1 for f in it if f.suffix.lower() in HEIC_EXTS)
        elif p.is_file():
            if p.suffix.lower() in HEIC_EXTS:
                heic += 1
                continue
            if p.suffix.lower() not in EXTS:
                eprint(f"! ignorado (extensão não suportada): {p}")
                continue
            out.append(p)
        else:
            eprint(f"! não encontrado: {p}")
    if heic:
        eprint(
            f"! {heic} arquivo(s) HEIC/HEIF ignorado(s) — formato não suportado.\n"
            "  Converta antes: sips -s format jpeg foto.heic --out foto.jpg (macOS)\n"
            "                  ffmpeg -i foto.heic foto.jpg"
        )
    seen, uniq = set(), []
    for f in sorted(out):
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            uniq.append(f)
    return uniq


def default_outdir(files: list[Path], first_arg: str) -> Path:
    base = Path(first_arg).expanduser()
    base = base if base.is_dir() else files[0].parent
    return base / "recortados"


def trim_alpha(img, pad: int):
    """Corta a imagem no retângulo mínimo que contém pixels não transparentes."""
    box = img.getchannel("A").getbbox()
    if not box:
        return img
    if pad:
        l, t, r, b = box
        box = (max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad))
    return img.crop(box)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="tchaubg",
        description="Remove o fundo de retratos e salva PNG transparente.",
    )
    ap.add_argument("paths", nargs="*", help="imagens e/ou pastas")
    ap.add_argument("--out", help="pasta de saída (padrão: <entrada>/recortados)")
    ap.add_argument("--model", default="birefnet-portrait", help="modelo rembg (--check lista todos)")
    ap.add_argument("--recursive", action="store_true", help="varre subpastas")
    ap.add_argument("--trim", action="store_true", help="corta no limite da pessoa")
    ap.add_argument("--pad", type=int, default=0, help="margem em px ao usar --trim")
    ap.add_argument("--max-side", type=int, default=0, help="reduz o lado maior antes de processar")
    ap.add_argument("--matting", action="store_true", help="alpha matting: bordas mais suaves, ~3x mais lento")
    ap.add_argument("--smooth", action="store_true", help="pós-processa a máscara (tira pontinhos soltos)")
    ap.add_argument("--suffix", default="", help="sufixo no nome do arquivo, ex: _sembg")
    ap.add_argument("--force", action="store_true", help="reprocessa mesmo se a saída já existir")
    ap.add_argument("--json", action="store_true", help="relatório final em JSON no stdout")
    ap.add_argument("--check", action="store_true", help="checa o ambiente e sai")
    args = ap.parse_args()

    if args.check:
        return check()
    if not args.paths:
        ap.error("informe ao menos uma imagem ou pasta (ou use --check)")
    if args.model not in MODELS:
        eprint(f"! modelo '{args.model}' fora da lista conhecida — seguindo mesmo assim")

    files = collect(args.paths, args.recursive)
    if not files:
        eprint("Nenhuma imagem encontrada.")
        return 1

    outdir = Path(args.out).expanduser() if args.out else default_outdir(files, args.paths[0])
    outdir.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    from rembg import new_session, remove

    eprint(f"Carregando modelo {args.model}… (primeira vez baixa ~1 GB)")
    t0 = time.time()
    session = new_session(args.model)
    eprint(f"Modelo pronto em {time.time() - t0:.1f}s. {len(files)} imagem(ns) na fila.\n")

    kwargs = {"session": session, "post_process_mask": args.smooth}
    if args.matting:
        kwargs.update(
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10,
        )

    resultados, erros = [], []
    for i, src in enumerate(files, 1):
        dst = outdir / f"{src.stem}{args.suffix}.png"
        if dst.resolve() == src.resolve():
            dst = outdir / f"{src.stem}{args.suffix or '_sembg'}.png"
        if dst.exists() and not args.force:
            eprint(f"[{i}/{len(files)}] {src.name} → já existe, pulando (use --force)")
            resultados.append({"entrada": str(src), "saida": str(dst), "pulado": True})
            continue

        t = time.time()
        try:
            img = Image.open(src)
            img.load()
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            if args.max_side and max(img.size) > args.max_side:
                r = args.max_side / max(img.size)
                img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)

            out = remove(img, **kwargs)
            if args.trim:
                out = trim_alpha(out, args.pad)
            out.save(dst, format="PNG")
        except Exception as e:
            eprint(f"[{i}/{len(files)}] {src.name} → ERRO: {type(e).__name__}: {e}")
            erros.append({"entrada": str(src), "erro": f"{type(e).__name__}: {e}"})
            continue

        dt = time.time() - t
        eprint(f"[{i}/{len(files)}] {src.name} → {dst.name}  {out.width}x{out.height}  {dt:.1f}s")
        resultados.append(
            {"entrada": str(src), "saida": str(dst), "px": list(out.size), "segundos": round(dt, 2)}
        )

    ok = [r for r in resultados if not r.get("pulado")]
    eprint(f"\n{len(ok)} recortada(s), {len(resultados) - len(ok)} pulada(s), {len(erros)} com erro.")
    eprint(f"Saída: {outdir}")
    if args.json:
        print(json.dumps({"saida": str(outdir), "resultados": resultados, "erros": erros}, ensure_ascii=False, indent=2))
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
