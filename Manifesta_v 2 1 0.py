# Extração - Manifestão de compra v 4 4 0 
import fitz  # PyMuPDF
import pandas as pd
import re

# =========================================
# 🔗 ETAPA 1: UNIR PDFs
# =========================================

pdf_1 = "/mnt/data/manifesta_2026.pdf"
pdf_2 = "/mnt/data/man-16-2026.pdf"
pdf_unido = "/mnt/data/pdf_unido.pdf"

def unir_pdfs(pdf1, pdf2, output):
    doc_final = fitz.open()

    for pdf in [pdf1, pdf2]:
        doc = fitz.open(pdf)
        doc_final.insert_pdf(doc)

    doc_final.save(output)
    print("📎 PDFs unidos com sucesso!")

unir_pdfs(pdf_1, pdf_2, pdf_unido)

# =========================================
# 🔧 CONFIGURAÇÕES
# =========================================

saida_csv = "saida.csv"
dados_finais = []

regex_processo_parcial = r'\d{2}\.\d\.\d{7,}-?'
regex_processo_final = r'\d{2}\.\d\.\d{7,}-\d'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

orgaos_validos = {
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA","CIVIL","DCPA"
}

TOL = 20

# =========================================
# 🔍 DETECTA COLUNAS
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
# 🔧 RECONSTRUIR PROCESSO
# =========================================

def reconstruir_processo(textos):
    buffer = ""

    for t in textos:
        t = t.strip()

        if re.match(regex_processo_parcial, t):
            buffer += t

            if re.fullmatch(regex_processo_final, buffer):
                return buffer

        elif buffer:
            buffer += t

            if re.fullmatch(regex_processo_final, buffer):
                return buffer

    return None

# =========================================
# 🔍 PROCESSAMENTO
# =========================================

def processar(df, x_org, x_total):

    df["linha"] = df["y0"].round(-1)

    for _, grupo in df.groupby("linha"):

        grupo = grupo.sort_values(by="x0")

        textos = grupo["text"].tolist()

        processo = reconstruir_processo(textos)

        if not processo:
            continue

        orgao = None
        total = None

        for _, row in grupo.iterrows():

            texto = str(row["text"]).strip()
            x = row["x0"]

            # ÓRGÃO
            if (x_org - TOL) <= x <= (x_org + 150):
                txt = texto.upper()
                if txt in orgaos_validos:
                    orgao = txt

            # TOTAL
            if x >= (x_total - TOL):
                if re.fullmatch(regex_total, texto):
                    total = texto

        if processo and orgao and total:
            dados_finais.append({
                "ÓRGÃO": orgao,
                "PROCESSO SEI": processo,
                "TOTAL": total
            })

# =========================================
# 🚀 EXECUÇÃO
# =========================================

doc = fitz.open(pdf_unido)

for page in doc:

    words = page.get_text("words")

    if not words:
        continue

    df = pd.DataFrame(words, columns=[
        "x0","y0","x1","y1","text","block","line","word"
    ])

    x_proc, x_org, x_total = detectar_colunas(df)

    if not x_org or not x_total:
        continue

    print(f"[DEBUG] ORG={x_org} TOTAL={x_total}")

    processar(df, x_org, x_total)

# =========================================
# 📊 FINAL
# =========================================

df_final = pd.DataFrame(dados_finais)

antes = len(df_final)
df_final = df_final.drop_duplicates()
depois = len(df_final)

print(f"✔ Registros extraídos: {depois}")
print(f"🧹 Duplicados removidos: {antes - depois}")

if df_final.empty:
    print("❌ Nenhum registro encontrado — revisar OCR/layout")

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

print("🚀 Pipeline finalizado com sucesso!")
