"""
inspecionar_coordenadas.py
--------------------------
Mostra as coordenadas exatas (left, top, width, conf) de cada token OCR
em páginas selecionadas do pdf_unido.pdf.

Use para calibrar X_ORGAO_MIN e X_ORGAO_MAX no extrator_sei.py.

Saídas geradas:
  - coordenadas_tokens.csv   → todos os tokens com posição e confiança
  - coordenadas_orgaos.csv   → apenas tokens que batem com siglas conhecidas
  - pagina_N_grade.png       → imagem da página com grade de coordenadas desenhada
"""

import os
import re

import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÕES — ajuste aqui
# ═══════════════════════════════════════════════════════════════

PASTA_BASE  = "/home/leonardomeneghini/PyCharmMiscProject"
PDF_UNIDO   = os.path.join(PASTA_BASE, "pdf_unido.pdf")

# Páginas a inspecionar (lista de inteiros). None = todas as páginas.
PAGINAS     = None   # ex.: [1, 2, 5]  ou  None

DPI         = 300

# Siglas a destacar nas imagens e no CSV de órgãos
ORGAOS_ALVO = [
    "PGM", "SMGG", "SMIDH", "SMAS", "SMDETE", "SMPG", "SMGOV", "SMEL",
    "SMC", "SMF", "SMAMUS", "SMSURB", "SMOI", "SMP", "SMTC", "SMAP",
    "SMMU", "SMED", "SMS", "SMSEG", "DMAE", "DEMHAB", "DMLU",
    "PREVIMPA", "EPTC", "DEFESA CIVIL", "DCPA",
]

# Diretório de saída para as imagens com grade
DIR_SAIDA   = "inspecao"
os.makedirs(DIR_SAIDA, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# FUNÇÕES
# ═══════════════════════════════════════════════════════════════

def is_orgao(token: str) -> bool:
    """Verifica se o token é igual ou muito próximo a alguma sigla alvo."""
    t = token.strip().upper()
    if t in ORGAOS_ALVO:
        return True
    # variações OCR simples: N no lugar de M, V no lugar de U
    variantes = [
        t,
        t.replace("N", "M"),
        t.replace("V", "U"),
        t.replace("N", "M").replace("V", "U"),
    ]
    return any(v in ORGAOS_ALVO for v in variantes)


def desenhar_grade(imagem: Image.Image, df_tokens: pd.DataFrame, pagina: int) -> Image.Image:
    """
    Desenha sobre a imagem:
      - retângulo AZUL para tokens comuns (conf > 60)
      - retângulo VERMELHO + label para tokens de órgão
      - linhas de grade verticais a cada 50px para leitura de coordenadas X
    """
    img   = imagem.copy().convert("RGB")
    draw  = ImageDraw.Draw(img, "RGBA")
    w, h  = img.size

    # Grade vertical a cada 50px
    for x in range(0, w, 50):
        draw.line([(x, 0), (x, h)], fill=(180, 180, 180, 80), width=1)
        draw.text((x + 2, 4), str(x), fill=(100, 100, 100))

    # Grade horizontal a cada 50px
    for y in range(0, h, 50):
        draw.line([(0, y), (w, y)], fill=(180, 180, 180, 60), width=1)
        draw.text((2, y + 2), str(y), fill=(100, 100, 100))

    try:
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        font_label = ImageFont.load_default()
        font_small = font_label

    for _, row in df_tokens.iterrows():
        x, y, bw, bh = int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"])
        token = str(row["text"]).strip()
        conf  = float(row["conf"])

        if conf < 20:
            continue

        if is_orgao(token):
            # Destaque vermelho para órgãos
            draw.rectangle([x, y, x + bw, y + bh], outline=(220, 30, 30), width=2,
                           fill=(220, 30, 30, 40))
            label = f"{token} ({int(conf)}%) x={x} y={y}"
            draw.text((x, y - 16 if y > 20 else y + bh + 2), label,
                      fill=(180, 0, 0), font=font_label)
        else:
            # Azul leve para demais tokens com boa confiança
            if conf >= 60:
                draw.rectangle([x, y, x + bw, y + bh], outline=(60, 100, 200, 120), width=1)

    return img


# ═══════════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════════

from pypdf import PdfReader
total_paginas = len(PdfReader(PDF_UNIDO).pages)
paginas_alvo  = PAGINAS if PAGINAS else list(range(1, total_paginas + 1))

todos_tokens  = []
todos_orgaos  = []

print(f"Inspecionando {len(paginas_alvo)} página(s) do PDF...\n")

for i in paginas_alvo:
    print(f"  → Página {i}/{total_paginas}", end="\r")

    pages = convert_from_path(PDF_UNIDO, first_page=i, last_page=i, dpi=DPI)
    page  = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 4",
        output_type=pytesseract.Output.DATAFRAME,
    )
    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip() != ""]
    df["pagina"] = i

    todos_tokens.append(df)

    # Filtra tokens que são órgãos
    mask_orgao = df["text"].apply(is_orgao)
    orgaos_df  = df[mask_orgao].copy()
    if not orgaos_df.empty:
        todos_orgaos.append(orgaos_df)
        print(f"\n  [PAG {i}] Órgãos detectados:")
        for _, row in orgaos_df.iterrows():
            print(f"           '{row['text']}' → left={int(row['left'])}  "
                  f"top={int(row['top'])}  width={int(row['width'])}  "
                  f"conf={row['conf']:.0f}%")

    # Gera imagem com grade
    img_grade = desenhar_grade(page, df, i)
    caminho_img = os.path.join(DIR_SAIDA, f"pagina_{i:03d}_grade.png")
    img_grade.save(caminho_img)

    del page, pages

print("\n")

# ── CSV completo de todos os tokens
df_todos = pd.concat(todos_tokens, ignore_index=True)
cols_saida = ["pagina", "text", "left", "top", "width", "height", "conf",
              "line_num", "block_num", "par_num", "word_num"]
cols_saida = [c for c in cols_saida if c in df_todos.columns]
df_todos[cols_saida].to_csv("coordenadas_tokens.csv", index=False, encoding="utf-8-sig")

# ── CSV apenas dos órgãos
if todos_orgaos:
    df_orgaos = pd.concat(todos_orgaos, ignore_index=True)
    df_orgaos[cols_saida].to_csv("coordenadas_orgaos.csv", index=False, encoding="utf-8-sig")
    print("═" * 60)
    print("RESUMO — coordenadas da coluna ÓRGÃO detectadas:")
    print("═" * 60)
    resumo = (
        df_orgaos.groupby("text")
        .agg(
            ocorrencias=("left", "count"),
            left_min=("left", "min"),
            left_max=("left", "max"),
            left_medio=("left", "mean"),
            conf_medio=("conf", "mean"),
        )
        .reset_index()
        .sort_values("left_medio")
    )
    print(resumo.to_string(index=False))
    print()

    left_min_global = int(df_orgaos["left"].min())
    left_max_global = int((df_orgaos["left"] + df_orgaos["width"]).max())
    margem = 20
    print(f"► Sugestão para extrator_sei.py:")
    print(f"  X_ORGAO_MIN = {max(0, left_min_global - margem)}")
    print(f"  X_ORGAO_MAX = {left_max_global + margem}")
else:
    print("Nenhum token de órgão encontrado nas páginas inspecionadas.")

print()
print(f"Arquivos gerados:")
print(f"  coordenadas_tokens.csv          → todos os tokens OCR")
print(f"  coordenadas_orgaos.csv          → apenas tokens de órgão")
print(f"  {DIR_SAIDA}/pagina_NNN_grade.png  → imagem com grade de coordenadas")
