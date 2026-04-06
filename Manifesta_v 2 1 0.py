# Extração - Manifestão de compra v 4 3 0 
import fitz
import pandas as pd
import re

pdf_path = "/mnt/data/manifesta_2026.pdf"
saida_csv = "saida.csv"

dados_finais = []

# 🔹 Regex
regex_processo_parcial = r'\d{2}\.\d\.\d{7,}-?'
regex_processo_final = r'\d{2}\.\d\.\d{7,}-\d'
regex_total = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'

# 🔹 Lista oficial
orgaos_validos = {
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA","CIVIL","DCPA"
}

TOL = 20  # tolerância de coluna

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
# 🔥 RECONSTRÓI PROCESSO QUEBRADO
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
# 🔥 PROCESSAMENTO
# =========================================

def processar(df, x_proc, x_org, x_total):

    df["linha"] = df["y0"].round(-1)

    for _, grupo in df.groupby("linha"):

        grupo = grupo.sort_values(by="x0")

        textos = grupo["text"].tolist()

        # 🔹 PROCESSO (reconstruído)
        processo = reconstruir_processo(textos)

        if not processo:
            continue

        orgao = None
        total = None

        for _, row in grupo.iterrows():

            texto = str(row["text"]).strip()
            x = row["x0"]

            # 🔹 ÓRGÃO (com tolerância)
            if (x_org - TOL) <= x <= (x_org + 150):
                txt = texto.upper()

                if txt in orgaos_validos:
                    orgao = txt

            # 🔹 TOTAL (com tolerância)
            if x >= (x_total - TOL):
                if re.fullmatch(regex_total, texto):
                    total = texto

        # 🔹 Validação final
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

    x_proc, x_org, x_total = detectar_colunas(df)

    if not x_org or not x_total:
        continue

    print(f"[DEBUG] PROC={x_proc} ORG={x_org} TOTAL={x_total}")

    processar(df, x_proc, x_org, x_total)


# =========================================
# 🔥 FINAL + LOG PROFISSIONAL
# =========================================

df_final = pd.DataFrame(dados_finais)

antes = len(df_final)

df_final = df_final.drop_duplicates()

depois = len(df_final)

print(f"✔ Registros extraídos: {depois}")
print(f"🧹 Duplicados removidos: {antes - depois}")

if df_final.empty:
    print("❌ Nenhum registro encontrado — verificar estrutura do PDF")

df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

print("🚀 Finalizado com sucesso")
