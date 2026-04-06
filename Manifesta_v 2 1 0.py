# Extração - Manifestão de compra v 4 2 0 
import fitz
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import re

pdf_path = "/mnt/data/manifesta_2026.pdf"
saida_csv = "saida.csv"

dados_finais = []

regex_processo = r'\d{2}\.\d\.\d{7,}-\d'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

# =========================================
# 🔥 DETECTA COLUNAS PELO CABEÇALHO
# =========================================

def detectar_colunas(df):

    x_proc = x_org = x_total = None

    for _, row in df.iterrows():
        texto = str(row["text"]).upper()

        if "PROCESSO" in texto:
            x_proc = row["x0"]

        elif "ÓRGÃO" in texto or "ORGAO" in texto:
            x_org = row["x0"]

        elif "TOTAL" in texto:
            x_total = row["x0"]

    return x_proc, x_org, x_total


# =========================================
# 🔥 PROCESSAMENTO
# =========================================

def processar(df, x_proc, x_org, x_total):

    df["linha"] = df["y0"].round(-1)

    for _, grupo in df.groupby("linha"):

        grupo = grupo.sort_values(by="x0")

        processo = None
        orgao = None
        total = None

        for _, row in grupo.iterrows():

            texto = str(row["text"]).strip()
            x = row["x0"]

            # PROCESSO
            if x < x_org:
                if re.fullmatch(regex_processo, texto):
                    processo = texto

            # ÓRGÃO
            elif x_org <= x < x_total:
                txt = texto.upper()

                if 3 <= len(txt) <= 8 and txt.isalpha():
                    orgao = txt

            # TOTAL
            elif x >= x_total:
                if re.fullmatch(regex_total, texto):
                    total = texto

        if processo and orgao and total:
            dados_finais.append({
                "ÓRGÃO": orgao,
                "PROCESSO SEI": processo,
                "TOTAL": total
            })


# =========================================
# 🔥 EXECUÇÃO
# =========================================

doc = fitz.open(pdf_path)

for page in doc:

    words = page.get_text("words")

    if not words:
        continue

    df = pd.DataFrame(words, columns=[
        "x0","y0","x1","y1","text","block","line","word"
    ])

    # 🔥 Detecta colunas dinamicamente
    x_proc, x_org, x_total = detectar_colunas(df)

    if not x_org or not x_total:
        continue

    print(f"DEBUG COLUNAS: PROC={x_proc}, ORG={x_org}, TOTAL={x_total}")

    processar(df, x_proc, x_org, x_total)

# =========================================
# 🔥 FINAL
# =========================================

df_final = pd.DataFrame(dados_finais).drop_duplicates()

print(f"✔ Registros: {len(df_final)}")

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")
