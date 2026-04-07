import os
import re
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfMerger, PdfReader

# =========================================================
# CONFIG
# =========================================================

PASTA_BASE = "/home/leonardomeneghini/PyCharmMiscProject"

PDF_1 = os.path.join(PASTA_BASE, "manifesta_2026.pdf")
PDF_2 = os.path.join(PASTA_BASE, "man-16-2026.pdf")
PDF_UNIDO = os.path.join(PASTA_BASE, "pdf_unido.pdf")

SAIDA_CSV = "saida.csv"
LOG_PATH = "log_problemas.txt"

DPI = 300
MARGEM = 20

# =========================================================
# UNIR PDFs
# =========================================================

print("Unindo PDFs...")

merger = PdfMerger()
merger.append(PDF_1)
merger.append(PDF_2)
merger.write(PDF_UNIDO)
merger.close()

# =========================================================
# CONFIG OCR
# =========================================================

regex_processo = r'\b\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]\b'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

orgaos_validos = [
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA CIVIL","DCPA"
]

def normalizar_ocr(texto):
    texto = texto.upper()
    texto = re.sub(r'[^A-Z0-9]', '', texto)
    return (texto.replace("0", "O")
                 .replace("1", "I")
                 .replace("5", "S")
                 .replace("8", "B"))

def normalizar_linha(linha):
    linha = re.sub(r'\s*\.\s*', '.', linha)
    linha = re.sub(r'\s*-\s*', '-', linha)
    linha = re.sub(r'\s+', ' ', linha)
    return linha.strip()

def corrigir_ocr(texto):
    return texto.replace("O", "0").replace("I", "1")

# =========================================================
# PROCESSAMENTO
# =========================================================

reader = PdfReader(PDF_UNIDO)

dados_finais = []
logs = []

X_ORGAO_MIN = None
X_ORGAO_MAX = None

print("Iniciando OCR...\n")

for i in range(1, len(reader.pages) + 1):

    print(f"Processando página {i}...")

    pages = convert_from_path(PDF_UNIDO, first_page=i, last_page=i, dpi=DPI)
    page = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 6",
        output_type=pytesseract.Output.DATAFRAME
    )

    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip() != ""]
    df["right"] = df["left"] + df["width"]

    # fallback OCR
    if len(df) < 50:
        logs.append(f"[PAG {i}] fallback OCR ativado")
        df = pytesseract.image_to_data(
            page,
            lang="por",
            config="--psm 11",
            output_type=pytesseract.Output.DATAFRAME
        )
        df = df.dropna(subset=["text"])
        df["right"] = df["left"] + df["width"]

    # =====================================================
    # AUTO-CALIBRAÇÃO DA COLUNA ÓRGÃO (primeiras páginas)
    # =====================================================

    if X_ORGAO_MIN is None:

        possiveis = []

        for _, row in df.iterrows():
            t = normalizar_ocr(str(row["text"]))

            if t in [normalizar_ocr(o) for o in orgaos_validos]:
                possiveis.append(row["left"])

        if possiveis:
            X_ORGAO_MIN = max(0, int(min(possiveis)) - MARGEM)
            X_ORGAO_MAX = int(max(possiveis)) + 150

            print(f"[AUTO] Coluna ÓRGÃO detectada: {X_ORGAO_MIN} → {X_ORGAO_MAX}")

    # =====================================================
    # LINHAS REAIS (ROBUSTO)
    # =====================================================

    linhas = df.groupby(["block_num", "par_num", "line_num"])

    linhas_info = []

    for linha_id, grupo in linhas:
        palavras = grupo.sort_values("left")["text"].tolist()
        linha = " ".join(palavras)

        linhas_info.append({
            "id": linha_id,
            "texto": linha
        })

    # =====================================================
    # CONTEXTO
    # =====================================================

    orgao_atual = None
    processo_atual = None
    buffer_processo = ""

    for item in linhas_info:

        linha_id = item["id"]
        linha = normalizar_linha(item["texto"])
        linha_corr = corrigir_ocr(linha)

        # ---------------- PROCESSO ----------------
        linha_proc = buffer_processo + linha_corr

        if linha_proc.endswith("-"):
            buffer_processo = linha_proc
            continue

        match_proc = re.search(regex_processo, linha_proc)

        if match_proc:
            processo_atual = match_proc.group()
            buffer_processo = ""
        else:
            buffer_processo = linha_corr

        # ---------------- ÓRGÃO VIA COORDENADA ----------------
        if X_ORGAO_MIN is not None:
            tokens_linha = df[
                (df["block_num"] == linha_id[0]) &
                (df["par_num"] == linha_id[1]) &
                (df["line_num"] == linha_id[2])
            ]

            tokens_orgao = tokens_linha[
                (tokens_linha["left"] >= X_ORGAO_MIN) &
                (tokens_linha["right"] <= X_ORGAO_MAX)
            ]

            for _, row in tokens_orgao.iterrows():
                t = normalizar_ocr(str(row["text"]))

                for org in orgaos_validos:
                    if normalizar_ocr(org) == t:
                        orgao_atual = org
                        break

        # ---------------- TOTAL ----------------
        totais = re.findall(regex_total, linha)

        if totais:
            for total in totais:

                if not orgao_atual:
                    logs.append(f"[PAG {i}] TOTAL sem órgão: {linha}")
                    continue

                dados_finais.append({
                    "ÓRGÃO": orgao_atual,
                    "PROCESSO SEI": processo_atual,
                    "TOTAL": total.strip()
                })

# =========================================================
# SAÍDA
# =========================================================

df_final = pd.DataFrame(dados_finais)

if not df_final.empty:
    df_final = df_final.drop_duplicates()

df_final.to_csv(SAIDA_CSV, index=False, encoding="utf-8-sig")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    for log in logs:
        f.write(log + "\n")

print("\nProcessamento finalizado!")
print(f"Registros encontrados: {len(df_final)}")
print(f"CSV: {SAIDA_CSV}")
print(f"LOG: {LOG_PATH}")
