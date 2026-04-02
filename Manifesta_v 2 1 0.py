# Extração - Manifestão de compra v 3 0 0
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from PyPDF2 import PdfReader
import re

pdf_path = "/home/leonardomeneghini/PyCharmMiscProject/pdf_unido.pdf"
saida_csv = "saida.csv"
log_path = "log_problemas.txt"

dados_finais = []
logs = []

reader = PdfReader(pdf_path)

# 🔹 LISTA FIXA DE ÓRGÃOS
orgaos_validos = [
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA CIVIL","DCPA"
]

# 🔹 Regex
regex_processo = r'\b\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]\b'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

# 🔹 Correção OCR (0↔O, 1↔I)
def corrigir_ocr(texto):
    texto = texto.replace("O", "0").replace("I", "1")
    return texto

# 🔹 Normalização
def normalizar_linha(linha):
    linha = re.sub(r'\s*\.\s*', '.', linha)
    linha = re.sub(r'\s*-\s*', '-', linha)
    linha = re.sub(r'\s+', ' ', linha)
    return linha.strip()

for i in range(1, len(reader.pages) + 1):
    pages = convert_from_path(pdf_path, first_page=i, last_page=i)
    page = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 4",
        output_type=pytesseract.Output.DATAFRAME
    )

    df = df.dropna(subset=["text"])

    # 🔥 FILTRO DE CONFIANÇA OCR
    df = df[df["conf"] > 60]

    # 🔥 AGRUPAMENTO POR LINHA
    df["top_round"] = (df["top"] // 10) * 10
    linhas = df.groupby("top_round")

    linhas_texto = []

    for _, grupo in linhas:
        palavras = grupo.sort_values("left")["text"].tolist()
        linha = " ".join(palavras)
        linhas_texto.append(linha)

    # 🔥 CONTEXTO
    orgao_atual = None
    processo_atual = None
    buffer_linha = ""

    for linha in linhas_texto:

        linha = corrigir_ocr(linha)
        linha = normalizar_linha(linha)

        linha_completa = buffer_linha + " " + linha

        # 🔹 PROCESSO SEI
        processo_match = re.search(regex_processo, linha_completa)

        if processo_match:
            processo_atual = processo_match.group()
            buffer_linha = ""
        else:
            # tenta detectar algo parecido (para log)
            possivel = re.search(r'\d{2}.*-.*\d', linha_completa)
            if possivel:
                logs.append(f"[PAG {i}] Possível processo inválido: {linha_completa}")
            buffer_linha = linha

        # 🔹 ÓRGÃO
        linha_upper = linha.upper()

        for org in orgaos_validos:
            if org in linha_upper:
                orgao_atual = org
                break

        # 🔹 TOTAL
        totais = re.findall(regex_total, linha)

        if totais and orgao_atual:
            for total in totais:
                if not processo_atual:
                    logs.append(f"[PAG {i}] TOTAL sem processo: {linha}")

                dados_finais.append({
                    "ÓRGÃO": orgao_atual,
                    "PROCESSO SEI": processo_atual,
                    "TOTAL": total.strip()
                })

    del page
    del pages

# 🔹 DataFrame final
df_final = pd.DataFrame(dados_finais, columns=["ÓRGÃO", "PROCESSO SEI", "TOTAL"])

print(f"Registros encontrados: {len(df_final)}")

if not df_final.empty:
    df_final = df_final.drop_duplicates()

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

# 🔹 SALVAR LOG
with open(log_path, "w", encoding="utf-8") as f:
    for log in logs:
        f.write(log + "\n")

print("Processamento concluído com sucesso!")
print(f"Log salvo em: {log_path}")


