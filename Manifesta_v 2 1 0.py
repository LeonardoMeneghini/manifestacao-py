# Extração - Manifestão de compra v 4 0 0 
import fitz  # PyMuPDF
import pandas as pd
import re

pdf_path = "/home/leonardomeneghini/PyCharmMiscProject/pdf_unido.pdf"
saida_csv = "saida.csv"

dados_finais = []

# 🔹 Regex
regex_processo = r'\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

# 🔹 ÓRGÃOS válidos
orgaos_validos = [
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU", "SMMU ","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA CIVIL","DCPA"
]

doc = fitz.open(pdf_path)

for page_num, page in enumerate(doc, start=1):

    words = page.get_text("words")  
    # estrutura: [x0, y0, x1, y1, "texto", block_no, line_no, word_no]

    df = pd.DataFrame(words, columns=[
        "x0","y0","x1","y1","text","block","line","word"
    ])

    # 🔥 agrupa por linha (y)
    df["y_round"] = df["y0"].round(-1)

    linhas = df.groupby("y_round")

    for _, linha in linhas:

        linha = linha.sort_values("x0")

        processo = None
        orgao = None
        totais = []

        # 🔹 Detecta PROCESSO
        for _, row in linha.iterrows():
            texto = str(row["text"])
            if re.fullmatch(regex_processo, texto):
                processo = texto
                x_processo = row["x0"]
                break

        if not processo:
            continue

        # 🔹 Detecta ÓRGÃO (à direita do processo)
        candidatos = []

        for _, row in linha.iterrows():
            texto = str(row["text"]).upper()

            if row["x0"] > x_processo:
                if texto in orgaos_validos:
                    distancia = row["x0"] - x_processo
                    candidatos.append((texto, distancia))

        if candidatos:
            orgao = sorted(candidatos, key=lambda x: x[1])[0][0]

        # 🔹 Detecta TOTAL
        for _, row in linha.iterrows():
            texto = str(row["text"])
            if re.fullmatch(regex_total, texto):
                totais.append(texto)

        # 🔹 Salva (um registro por TOTAL)
        if orgao and totais:
            for total in totais:
                dados_finais.append({
                    "ÓRGÃO": orgao,
                    "PROCESSO SEI": processo,
                    "TOTAL": total
                })

df_final = pd.DataFrame(dados_finais)

print(f"Registros encontrados: {len(df_final)}")

df_final = df_final.drop_duplicates()

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

print("Processamento concluído com sucesso!")
