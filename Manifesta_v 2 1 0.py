# Extração - Manifestão de compra v 4 7 0 
"""
extrator_sei.py
---------------
Etapas:
  1. Une manifesta_2026.pdf + man-16-2026.pdf → pdf_unido.pdf
  2. OCR página a página (Tesseract) com DPI=300
  3. Detecta ÓRGÃO palavra a palavra (coluna X do PDF) — resolve o bug do SMMU
  4. Detecta PROCESSO SEI por regex com correção OCR (O↔0, I↔1)
  5. Detecta TOTAL (R$) por regex
  6. Exporta saida.csv e log_problemas.txt
"""

import os
import re
from difflib import get_close_matches

import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter


# ═══════════════════════════════════════════════════════════════
# 0. CAMINHOS
# ═══════════════════════════════════════════════════════════════

PASTA_BASE  = "/home/leonardomeneghini/PyCharmMiscProject"
PDF_A       = os.path.join(PASTA_BASE, "manifesta_2026.pdf")
PDF_B       = os.path.join(PASTA_BASE, "man-16-2026.pdf")
PDF_UNIDO   = os.path.join(PASTA_BASE, "pdf_unido.pdf")
SAIDA_CSV   = "saida.csv"
LOG_PATH    = "log_problemas.txt"

# Faixa horizontal (pixels a 300 DPI) da coluna ÓRGÃO no PDF.
# Ajuste rodando: print(df[df["text"]=="SMMU"][["left","width","top"]])
X_ORGAO_MIN = 80
X_ORGAO_MAX = 220


# ═══════════════════════════════════════════════════════════════
# 1. UNIR PDFs
# ═══════════════════════════════════════════════════════════════

def unir_pdfs(arquivo_a: str, arquivo_b: str, destino: str) -> None:
    """Concatena arquivo_a + arquivo_b e salva em destino."""
    writer = PdfWriter()
    for caminho in (arquivo_a, arquivo_b):
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        for page in PdfReader(caminho).pages:
            writer.add_page(page)
    with open(destino, "wb") as f:
        writer.write(f)
    total_pags = len(PdfReader(destino).pages)
    print(f"[ETAPA 1] PDFs unidos → {destino}  ({total_pags} páginas)")


unir_pdfs(PDF_A, PDF_B, PDF_UNIDO)


# ═══════════════════════════════════════════════════════════════
# 2. CONFIGURAÇÕES DE EXTRAÇÃO
# ═══════════════════════════════════════════════════════════════

ORGAOS_VALIDOS = [
    "PGM", "SMGG", "SMIDH", "SMAS", "SMDETE", "SMPG", "SMGOV", "SMEL",
    "SMC", "SMF", "SMAMUS", "SMSURB", "SMOI", "SMP", "SMTC", "SMAP",
    "SMMU", "SMED", "SMS", "SMSEG", "DMAE", "DEMHAB", "DMLU",
    "PREVIMPA", "EPTC", "DEFESA CIVIL", "DCPA",
]

# Aliases para erros típicos de OCR em fontes CID TrueType
# Chave = o que o Tesseract lê; Valor = sigla correta
ALIASES_OCR = {
    # ── SMMU (confusões mais frequentes: M→N, M→RN, U→O, U→V, espaço inserido)
    "SNMU":   "SMMU",
    "SMMV":   "SMMU",
    "SMMO":   "SMMU",
    "SM MU":  "SMMU",
    "SNMV":   "SMMU",
    "SRNMU":  "SMMU",
    "SMRNU":  "SMMU",
    "SNIMU":  "SMMU",
    "SNINU":  "SMMU",
    "SMMIJ":  "SMMU",
    # ── SMOI (O↔0, I↔1)
    "SM0I":   "SMOI",
    "SM01":   "SMOI",
    # ── SMED
    "SNIED":  "SMED",
    "SNIIED": "SMED",
    # ── SMAS
    "SNIAS":  "SMAS",
    # ── Demais SM_ com N no lugar de M
    "SNGG":   "SMGG",
    "SNIDH":  "SMIDH",
    "SNDETE": "SMDETE",
    "SNPG":   "SMPG",
    "SNGOV":  "SMGOV",
    "SNEL":   "SMEL",
    "SNAMUS": "SMAMUS",
    "SNSURB": "SMSURB",
    "SNP":    "SMP",
    "SNTC":   "SMTC",
    "SNAP":   "SMAP",
    "SNSEG":  "SMSEG",
    "SNS":    "SMS",
    "SNC":    "SMC",
    "SNF":    "SMF",
}

REGEX_PROCESSO = r'\b\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]\b'
REGEX_TOTAL    = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'


# ═══════════════════════════════════════════════════════════════
# 3. FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════

def corrigir_ocr_processo(texto: str) -> str:
    """Substitui O→0 e I→1 apenas para extrair o número SEI."""
    return texto.replace("O", "0").replace("I", "1")


def normalizar_linha(linha: str) -> str:
    linha = re.sub(r'\s*\.\s*', '.', linha)
    linha = re.sub(r'\s*-\s*', '-', linha)
    linha = re.sub(r'\s+', ' ', linha)
    return linha.strip()


def detectar_orgao(texto: str):
    """
    Identifica a sigla do órgão em 'texto' usando três camadas:
      1. Match exato (maiúsculas)
      2. Lookup na tabela de aliases OCR
      3. Fuzzy match via difflib (cutoff 0.75)
    Retorna (orgao | None, estrategia | None).
    """
    texto_up = texto.upper()

    # Camada 1 — exato
    for org in ORGAOS_VALIDOS:
        if org in texto_up:
            return org, "exato"

    # Camada 2 — aliases OCR
    for alias, orgao_correto in ALIASES_OCR.items():
        if alias in texto_up:
            return orgao_correto, f"alias({alias})"

    # Camada 3 — fuzzy por token
    tokens = re.findall(r'[A-Z]{2,}', texto_up)
    for token in tokens:
        matches = get_close_matches(token, ORGAOS_VALIDOS, n=1, cutoff=0.75)
        if matches:
            return matches[0], f"fuzzy({token}→{matches[0]})"

    return None, None


def detectar_orgao_no_df(df_pagina: pd.DataFrame) -> list[dict]:
    """
    Varre cada token OCR dentro da faixa X da coluna ÓRGÃO,
    palavra a palavra, independente do agrupamento por linha.
    Retorna lista de {top, orgao, estrategia, token_original}.
    Resolve o bug do SMMU: célula alta isola a sigla em top_round exclusivo.
    """
    col_orgao = df_pagina[
        (df_pagina["left"] >= X_ORGAO_MIN) &
        (df_pagina["left"] <= X_ORGAO_MAX) &
        (df_pagina["conf"] > 30)   # limiar menor: token isolado tem menos contexto
    ].copy()

    achados = []
    for _, row in col_orgao.iterrows():
        token = str(row["text"]).strip()
        orgao, estrategia = detectar_orgao(token)
        if orgao:
            achados.append({
                "top":            int(row["top"]),
                "orgao":          orgao,
                "estrategia":     estrategia,
                "token_original": token,
            })
    return achados


# ═══════════════════════════════════════════════════════════════
# 4. LOOP PRINCIPAL DE OCR
# ═══════════════════════════════════════════════════════════════

reader       = PdfReader(PDF_UNIDO)
dados_finais = []
logs         = []
total_paginas = len(reader.pages)

print(f"[ETAPA 2] Iniciando OCR — {total_paginas} páginas...")

for i in range(1, total_paginas + 1):

    print(f"  → Página {i}/{total_paginas}", end="\r")

    pages = convert_from_path(PDF_UNIDO, first_page=i, last_page=i, dpi=300)
    page  = pages[0]

    df = pytesseract.image_to_data(
        page,
        lang="por",
        config="--psm 4",
        output_type=pytesseract.Output.DATAFRAME,
    )
    df = df.dropna(subset=["text"])
    df = df[df["conf"] > 60]
    df["top_round"] = (df["top"] // 10) * 10

    # ── Detecta órgãos palavra a palavra (corrige bug do SMMU)
    orgaos_pagina    = detectar_orgao_no_df(df)
    mapa_orgao_por_top = {a["top"]: a["orgao"] for a in orgaos_pagina}
    for a in orgaos_pagina:
        logs.append(
            f"[PAG {i}] Órgão via {a['estrategia']}: "
            f"'{a['token_original']}' → {a['orgao']} (top={a['top']})"
        )

    # ── Agrupamento por linha (para processo SEI e TOTAL)
    linhas_texto = []
    for _, grupo in df.groupby("top_round"):
        linha = " ".join(grupo.sort_values("left")["text"].tolist())
        linhas_texto.append(linha)

    orgao_atual    = None
    processo_atual = None
    buffer_linha   = ""

    for linha in linhas_texto:
        linha          = normalizar_linha(linha)
        linha_completa = (buffer_linha + " " + linha).strip()

        # ── Processo SEI
        linha_corrigida = corrigir_ocr_processo(linha_completa)
        processo_match  = re.search(REGEX_PROCESSO, linha_corrigida)
        if processo_match:
            processo_atual = processo_match.group()
            buffer_linha   = ""
        else:
            if re.search(r'\d{2}.*-.*\d', linha_corrigida):
                logs.append(f"[PAG {i}] Possível processo inválido: {linha_completa}")
            buffer_linha = linha

        # ── Atualiza órgão a partir do mapa de posição vertical
        # Pega o top mais recente com órgão identificado (acima da linha atual)
        tops_com_orgao = [t for t in mapa_orgao_por_top if t <= df["top"].max()]
        if tops_com_orgao:
            orgao_atual = mapa_orgao_por_top[max(tops_com_orgao)]

        # ── Total
        totais = re.findall(REGEX_TOTAL, linha)
        if totais and orgao_atual:
            for total in totais:
                if not processo_atual:
                    logs.append(f"[PAG {i}] TOTAL sem processo: {linha}")
                dados_finais.append({
                    "ÓRGÃO":        orgao_atual,
                    "PROCESSO SEI": processo_atual,
                    "TOTAL":        total.strip(),
                })

    del page, pages

print()  # quebra linha após o \r do progresso


# ═══════════════════════════════════════════════════════════════
# 5. EXPORTAÇÃO
# ═══════════════════════════════════════════════════════════════

df_final = pd.DataFrame(dados_finais, columns=["ÓRGÃO", "PROCESSO SEI", "TOTAL"])

if not df_final.empty:
    df_final = df_final.drop_duplicates()

df_final.to_csv(SAIDA_CSV, index=False, encoding="utf-8-sig")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(logs))

print(f"[ETAPA 3] Registros exportados : {len(df_final)}")
print(f"          CSV                  : {SAIDA_CSV}")
print(f"          Log                  : {LOG_PATH}")
print("Processamento concluído!")
