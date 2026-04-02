# Extração - Manifestão de compra v 2 1 0

import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from PyPDF2 import PdfReader
import re

pdf_path = "/home/leonardomeneghini/PyCharmMiscProject/pdf_unido.pdf"
saida_csv = "saida.csv"

dados_finais = []

def normalizar_valor(valor):
    valor = valor.replace("R$", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return float(valor)
    except:
        return None

reader = PdfReader(pdf_path)

for i in range(1, len(reader.pages) + 1):
    pages = convert_from_path(pdf_path, first_page=i, last_page=i)
    page = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 6",
        output_type=pytesseract.Output.DATAFRAME
    )

    df = df.dropna(subset=["text"])

    # 🔥 AGRUPAMENTO POR POSIÇÃO (ESSENCIAL)
    df["top_round"] = (df["top"] // 10) * 10

    linhas = df.groupby("top_round")

    linhas_texto = []

    for _, grupo in linhas:
        palavras = grupo.sort_values("left")["text"].tolist()
        linha = " ".join(palavras)
        linhas_texto.append(linha)

    # 🔥 DEBUG (veja isso rodando!)
    # for l in linhas_texto:
    #     print(l)

    # 🔥 EXTRAÇÃO INTELIGENTE
    for linha in linhas_texto:

        # procura código
        codigo_match = re.search(r'\b\d{5,}\b', linha)
        if not codigo_match:
            continue

        codigo = codigo_match.group()

        # procura quantidade (último número pequeno)
        qt_match = re.findall(r'\b\d+\b', linha)
        qt = None
        if len(qt_match) >= 2:
            qt = qt_match[-1]

        # procura valor
        valor_match = re.search(r'R?\$?\s?\d[\d\.,]+', linha)
        if not valor_match:
            continue

        valor_raw = valor_match.group()
        valor = normalizar_valor(valor_raw)

        if valor is None:
            continue

        # 🔥 órgão = primeira palavra válida
        partes = linha.split()
        orgao = None

        for p in partes:
            if re.match(r'^[A-Za-z]{3,12}$', p):
                orgao = p
                break

        if not orgao:
            continue

        dados_finais.append({
            "ÓRGÃO": orgao,
            "CÓDIGO": codigo,
            "QT": int(qt) if qt else None,
            "VALOR": valor
        })

    del page
    del pages

# 🔹 DataFrame garantido
df_final = pd.DataFrame(dados_finais, columns=["ÓRGÃO", "CÓDIGO", "QT", "VALOR"])

print(f"Registros encontrados: {len(df_final)}")

if not df_final.empty:
    df_final = df_final.drop_duplicates()
    df_final = df_final.sort_values(by="VALOR", ascending=False)

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

print("Processamento concluído com sucesso!")