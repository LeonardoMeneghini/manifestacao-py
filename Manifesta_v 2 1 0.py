# Extração - Manifestão de compra v 4 5 0 
import fitz
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import re

# =========================================
# 🔗 UNIR PDFs
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
    print("📎 PDFs unidos!")

unir_pdfs(pdf_1, pdf_2, pdf_unido)

# =========================================
# 🔧 CONFIG
# =========================================

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
# 🔍 DETECTAR COLUNAS
# =========================================

def detectar_colunas(df):
    x_org = x_total = None

    for _, row in df.iterrows():
        texto = str(row["text"]).upper()

        if "ÓRGÃO" in texto or "ORGAO" in texto:
            x_org = row["x0"]

        elif "TOTAL" in texto:
            x_total = row["x0"]

    return x_org, x_total

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
# 🔍 PROCESSAR LINHAS
# =========================================

def processar(df, x_org, x_total, pagina):

    encontrados = 0

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

            if (x_org - TOL) <= x <= (x_org + 150):
                txt = texto.upper()
                if txt in orgaos_validos:
                    orgao = txt

            if x >= (x_total - TOL):
                if re.fullmatch(regex_total, texto):
                    total = texto

        if processo and orgao and total:
            encontrados += 1
            dados_finais.append({
                "ÓRGÃO": orgao,
                "PROCESSO SEI": processo,
                "TOTAL": total,
                "PAGINA": pagina
            })

    return encontrados

# =========================================
# 🚀 EXECUÇÃO COM FALLBACK
# =========================================

doc = fitz.open(pdf_unido)

for i, page in enumerate(doc):

    print(f"\n📄 Página {i+1}")

    words = page.get_text("words")

    # 🔥 Critério de falha
    if not words or len(words) < 50:
        usar_ocr = True
        print("⚠️ Pouco texto → OCR ativado")
    else:
        usar_ocr = False

    if not usar_ocr:
        df = pd.DataFrame(words, columns=[
            "x0","y0","x1","y1","text","block","line","word"
        ])

        x_org, x_total = detectar_colunas(df)

        if not x_org or not x_total:
            usar_ocr = True
            print("⚠️ Colunas não detectadas → OCR ativado")

    # =========================================
    # 🔥 OCR FALLBACK
    # =========================================
    if usar_ocr:

        images = convert_from_path(pdf_unido, first_page=i+1, last_page=i+1)

        df = pytesseract.image_to_data(
            images[0],
            lang="por",
            config="--psm 6",
            output_type=pytesseract.Output.DATAFRAME
        )

        df = df.dropna(subset=["text"])
        df = df[df["conf"] > 50]

        # normaliza nomes
        df = df.rename(columns={"left": "x0", "top": "y0"})

        print(f"🔎 OCR palavras: {len(df)}")

        x_org, x_total = detectar_colunas(df)

        if not x_org or not x_total:
            print("❌ Falha total na página (nem OCR resolveu)")
            continue

    print(f"📍 Colunas → ORG={x_org} TOTAL={x_total}")

    encontrados = processar(df, x_org, x_total, i+1)

    print(f"✅ Registros encontrados na página: {encontrados}")

# =========================================
# 📊 FINAL
# =========================================

df_final = pd.DataFrame(dados_finais)

antes = len(df_final)
df_final = df_final.drop_duplicates()
depois = len(df_final)

print("\n==============================")
print(f"✔ TOTAL FINAL: {depois}")
print(f"🧹 Duplicados removidos: {antes - depois}")

df_final.to_csv("saida.csv", index=False, encoding="utf-8-sig")

print("🚀 FINALIZADO COM SUCESSO")
