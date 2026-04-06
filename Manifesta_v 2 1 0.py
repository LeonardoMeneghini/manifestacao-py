# Extração - Manifestão de compra v 4 6 0 
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from pypdf import PdfReader, PdfWriter          # ← pypdf unificado (lê e escreve)
import re
from difflib import get_close_matches
import os

# ============================================================
# 🔹 ETAPA 1 — UNIR OS DOIS PDFs EM pdf_unido.pdf
# ============================================================
pasta_base  = "/home/leonardomeneghini/PyCharmMiscProject"
pdf_a       = os.path.join(pasta_base, "manifesta_2026.pdf")
pdf_b       = os.path.join(pasta_base, "man-16-2026.pdf")
pdf_path    = os.path.join(pasta_base, "pdf_unido.pdf")

def unir_pdfs(arquivo_a: str, arquivo_b: str, destino: str) -> None:
    """Concatena arquivo_a + arquivo_b e salva em destino."""
    writer = PdfWriter()
    for caminho in (arquivo_a, arquivo_b):
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        reader = PdfReader(caminho)
        for page in reader.pages:
            writer.add_page(page)
    with open(destino, "wb") as f:
        writer.write(f)
    print(f"PDFs unidos com sucesso → {destino}  "
          f"({sum(1 for _ in PdfReader(destino).pages)} páginas)")

unir_pdfs(pdf_a, pdf_b, pdf_path)

# ============================================================
# 🔹 ETAPA 2 — EXTRAÇÃO OCR
# ============================================================
saida_csv  = "saida.csv"
log_path   = "log_problemas.txt"
dados_finais = []
logs = []

reader = PdfReader(pdf_path)

orgaos_validos = [
    "PGM","SMGG","SMIDH","SMAS","SMDETE","SMPG","SMGOV","SMEL","SMC","SMF",
    "SMAMUS","SMSURB","SMOI","SMP","SMTC","SMAP","SMMU","SMED","SMS",
    "SMSEG","DMAE","DEMHAB","DMLU","PREVIMPA","EPTC","DEFESA CIVIL","DCPA"
]

aliases_ocr = {
    "SNMU":"SMMU","SMMV":"SMMU","SMMO":"SMMU","SM MU":"SMMU",
    "SNMV":"SMMU","SRNMU":"SMMU","SMRNU":"SMMU","SNIMU":"SMMU",
    "SM0I":"SMOI","SM01":"SMOI",
    "SNIED":"SMED","SNIIED":"SMED",
    "SNIAS":"SMAS","SNGG":"SMGG","SNIDH":"SMIDH","SNDETE":"SMDETE",
}

regex_processo = r'\b\d{2}\.[A-Za-z0-9]\.[A-Za-z0-9]{9}-[A-Za-z0-9]\b'
regex_total    = r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}'


def corrigir_ocr_processo(texto):
    return texto.replace("O", "0").replace("I", "1")


def normalizar_linha(linha):
    linha = re.sub(r'\s*\.\s*', '.', linha)
    linha = re.sub(r'\s*-\s*', '-', linha)
    linha = re.sub(r'\s+', ' ', linha)
    return linha.strip()


def detectar_orgao(linha):
    linha_up = linha.upper()
    for org in orgaos_validos:
        if org in linha_up:
            return org, "exato"
    for alias, orgao_correto in aliases_ocr.items():
        if alias in linha_up:
            return orgao_correto, f"alias({alias})"
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
        page, lang="por", config="--psm 4",
        output_type=pytesseract.Output.DATAFRAME
    )
    df = df.dropna(subset=["text"])
    df = df[df["conf"] > 60]
    df["top_round"] = (df["top"] // 10) * 10

    linhas_texto = []
    for _, grupo in df.groupby("top_round"):
        linhas_texto.append(" ".join(grupo.sort_values("left")["text"].tolist()))

    orgao_atual    = None
    processo_atual = None
    buffer_linha   = ""

    for linha in linhas_texto:
        linha          = normalizar_linha(linha)
        linha_completa = (buffer_linha + " " + linha).strip()

        linha_corrigida = corrigir_ocr_processo(linha_completa)
        processo_match  = re.search(regex_processo, linha_corrigida)
        if processo_match:
            processo_atual = processo_match.group()
            buffer_linha   = ""
        else:
            if re.search(r'\d{2}.*-.*\d', linha_corrigida):
                logs.append(f"[PAG {i}] Possível processo inválido: {linha_completa}")
            buffer_linha = linha

        orgao_encontrado, estrategia = detectar_orgao(linha)
        if orgao_encontrado:
            if orgao_encontrado != orgao_atual:
                logs.append(f"[PAG {i}] Órgão via {estrategia}: '{linha.strip()}' → {orgao_encontrado}")
            orgao_atual = orgao_encontrado

        totais = re.findall(regex_total, linha)
        if totais and orgao_atual:
            for total in totais:
                if not processo_atual:
                    logs.append(f"[PAG {i}] TOTAL sem processo: {linha}")
                dados_finais.append({
                    "ÓRGÃO":        orgao_atual,
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
    f.write("\n".join(logs))

print("Processamento concluído!")
print(f"Log salvo em: {log_path}")
