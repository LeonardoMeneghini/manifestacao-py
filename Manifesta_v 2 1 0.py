# Extração - Manifestão de compra v 4 6 0 
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from PyPDF2 import PdfReader
import re
from difflib import get_close_matches

pdf_path = "/home/leonardomeneghini/PyCharmMiscProject/pdf_unido.pdf"
saida_csv = "saida.csv"
log_path = "log_problemas.txt"
dados_finais = []
logs = []
reader = PdfReader(pdf_path)

orgaos_validos = [
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA CIVIL","DCPA"
]

# 🔹 Aliases heurísticos para erros típicos de OCR CID TrueType
# Foco em SMMU, mas cobre os demais também
aliases_ocr = {
    # SMMU — confusões mais comuns: M→N, M→RN, U→O, U→V, espaço inserido
    "SNMU":     "SMMU",
    "SMMV":     "SMMU",
    "SMMO":     "SMMU",
    "SM MU":    "SMMU",
    "SNMV":     "SMMU",
    "SRNMU":    "SMMU",
    "SMRNU":    "SMMU",
    "SNIMU":    "SMMU",
    # SMOI — O↔0 já tratado; I↔1 pode gerar SM01
    "SM0I":     "SMOI",
    "SM01":     "SMOI",
    # SMED
    "SNIED":    "SMED",
    "SNIIED":   "SMED",
    # SMAS
    "SNIAS":    "SMAS",
    # genéricos SM_ com N no lugar de M
    "SNGG":     "SMGG",
    "SNIDH":    "SMIDH",
    "SNDETE":   "SMDETE",
}

regex_processo = r'\b\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]\b'
regex_total    = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'


# 🔹 Correção OCR — aplicada SOMENTE ao número do processo
def corrigir_ocr_processo(texto):
    """Converte confusões O↔0 e I↔1 apenas para extrair o nº SEI."""
    return texto.replace("O", "0").replace("I", "1")


def normalizar_linha(linha):
    linha = re.sub(r'\s*\.\s*', '.', linha)
    linha = re.sub(r'\s*-\s*', '-', linha)
    linha = re.sub(r'\s+', ' ', linha)
    return linha.strip()


# 🔹 Detecção heurística de órgão com múltiplas camadas
def detectar_orgao(linha):
    """
    Tenta identificar o órgão na linha usando 3 estratégias em cascata:
      1. Match exato (maiúsculas)
      2. Lookup na tabela de aliases OCR
      3. Fuzzy match via difflib (fallback tolerante)
    Retorna (orgao_str | None, estrategia_usada)
    """
    linha_up = linha.upper()

    # --- Camada 1: match exato ---
    for org in orgaos_validos:
        if org in linha_up:
            return org, "exato"

    # --- Camada 2: aliases OCR ---
    for alias, orgao_correto in aliases_ocr.items():
        if alias in linha_up:
            return orgao_correto, f"alias({alias})"

    # --- Camada 3: fuzzy por token ---
    # Quebra a linha em tokens e testa cada um contra a lista de órgãos
    tokens = re.findall(r'[A-Z]{2,}', linha_up)
    for token in tokens:
        matches = get_close_matches(token, orgaos_validos, n=1, cutoff=0.75)
        if matches:
            return matches[0], f"fuzzy({token}→{matches[0]})"

    return None, None


for i in range(1, len(reader.pages) + 1):
    pages = convert_from_path(pdf_path, first_page=i, last_page=i, dpi=300)
    page  = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 4",
        output_type=pytesseract.Output.DATAFRAME
    )
    df = df.dropna(subset=["text"])
    df = df[df["conf"] > 60]

    df["top_round"] = (df["top"] // 10) * 10
    linhas_texto = []
    for _, grupo in df.groupby("top_round"):
        palavras = grupo.sort_values("left")["text"].tolist()
        linhas_texto.append(" ".join(palavras))

    orgao_atual   = None
    processo_atual = None
    buffer_linha   = ""

    for linha in linhas_texto:
        linha = normalizar_linha(linha)       # normaliza sem tocar letras
        linha_completa = (buffer_linha + " " + linha).strip()

        # 🔹 Processo SEI — aplica correção OCR só aqui
        linha_corrigida = corrigir_ocr_processo(linha_completa)
        processo_match  = re.search(regex_processo, linha_corrigida)
        if processo_match:
            processo_atual = processo_match.group()
            buffer_linha   = ""
        else:
            possivel = re.search(r'\d{2}.*-.*\d', linha_corrigida)
            if possivel:
                logs.append(f"[PAG {i}] Possível processo inválido: {linha_completa}")
            buffer_linha = linha

        # 🔹 Órgão — usa detecção heurística multicamada
        orgao_encontrado, estrategia = detectar_orgao(linha)
        if orgao_encontrado:
            if orgao_encontrado != orgao_atual:
                logs.append(
                    f"[PAG {i}] Órgão detectado via {estrategia}: "
                    f"'{linha.strip()}' → {orgao_encontrado}"
                )
            orgao_atual = orgao_encontrado

        # 🔹 Total
        totais = re.findall(regex_total, linha)
        if totais and orgao_atual:
            for total in totais:
                if not processo_atual:
                    logs.append(f"[PAG {i}] TOTAL sem processo: {linha}")
                dados_finais.append({
                    "ÓRGÃO":       orgao_atual,
                    "PROCESSO SEI": processo_atual,
                    "TOTAL":        total.strip()
                })

    del page, pages

df_final = pd.DataFrame(dados_finais, columns=["ÓRGÃO", "PROCESSO SEI", "TOTAL"])
print(f"Registros encontrados: {len(df_final)}")
if not df_final.empty:
    df_final = df_final.drop_duplicates()
df_final.to_csv(saida_csv, index=False, encoding="utf-8-sig")

with open(log_path, "w", encoding="utf-8") as f:
    for log in logs:
        f.write(log + "\n")

print("Processamento concluído!")
print(f"Log salvo em: {log_path}")
