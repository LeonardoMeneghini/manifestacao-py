# Extração - Manifestão de compra v 4 1 0 
import fitz
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import re

pdf_path = "pdf_unido.pdf"
saida_csv = "saida.csv"

dados_finais = []

# 🔹 Regex
regex_processo = r'\d{2}\.\d\.\d{7,}-\d'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

# 🔹 Correção OCR
def corrigir_texto(texto):
    texto = texto.upper().strip()
    texto = texto.replace("0", "O")
    texto = texto.replace("1", "I")
    return texto

# 🔹 Faixas de coluna (AJUSTADAS PELO PRINT)
COL_PROCESSO_MAX_X = 200
COL_ORGAO_MIN_X = 200
COL_ORGAO_MAX_X = 350
COL_TOTAL_MIN_X = 900

# =========================================
# 🔥 PROCESSAMENTO POR COORDENADA
# =========================================

def processar(df):

    # Normaliza eixo Y (linha)
    df["linha"] = (df["top"] // 10) * 10 if "top" in df else df["y0"].round(-1)

    for _, grupo in df.groupby("linha"):

        grupo = grupo.sort_values(by=["left"] if "left" in df else ["x0"])

        processo = None
        orgao = None
        total = None

        for _, row in grupo.iterrows():

            texto = str(row["text"]).strip()
            x = row["left"] if "left" in df else row["x0"]

            # 🔹 PROCESSO
            if x < COL_PROCESSO_MAX_X:
                if re.fullmatch(regex_processo, texto):
                    processo = texto

            # 🔹 ÓRGÃO (posição fixa)
            if COL_ORGAO_MIN_X < x < COL_ORGAO_MAX_X:
                texto_corrigido = corrigir_texto(texto)

                if 3 <= len(texto_corrigido) <= 6:
                    orgao = texto_corrigido

            # 🔹 TOTAL
            if x > COL_TOTAL_MIN_X:
                if re.fullmatch(regex_total, texto):
                    total = texto

        # 🔹 Validação forte
        if processo and orgao and total:

            dados_finais.append({
                "ÓRGÃO": orgao,
                "PROCESSO SEI": processo,
                "TOTAL": total
            })

# =========================================
# 🔥 DETECÇÃO AUTOMÁTICA (OCR / NÃO OCR)
# =========================================

doc = fitz.open(pdf_path)

usou_ocr = False

for page in doc:

    words = page.get_text("words")

    if not words:
        usou_ocr = True
        break

    df = pd.DataFrame(words, columns=[
        "x0","y0","x1","y1","text","block","line","word"
    ])

    if df.empty:
        usou_ocr = True
        break

    processar(df)

# =========================================
# 🔥 FALLBACK OCR
# =========================================

if usou_ocr or len(dados_finais) == 0:

    print("⚠️ Ativando OCR...")

    dados_finais.clear()

    pages = convert_from_path(pdf_path)

    for page in pages:

        df = pytesseract.image_to_data(
            page,
            lang="por",
            config="--psm 6",
            output_type=pytesseract.Output.DATAFRAME
        )

        df = df.dropna(subset=["text"])

        # 🔥 SCORE DE CONFIANÇA
        df = df[df["conf"] > 50]

        processar(df)

# =========================================
# 🔥 LOG PROFISSIONAL
# =========================================

df_final = pd.DataFrame(dados_finais)

print(f"✔ Registros extraídos: {len(df_final)}")

# Remover duplicados
df_final = df_final.drop_duplicates()

# Log de inconsistências
if df_final.empty:
    print("❌ Nenhum dado extraído — verificar OCR/layout")

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

print("🚀 Finalizado com sucesso")
