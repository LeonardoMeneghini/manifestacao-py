# manifestacao-py

## 📌 Versão
**Versão 5 (em duas partes)**

- 🔧 Juntar PDFs: **DOING**
- 📄 Extração de dados: `extrator_sei_Dv3.py`

---

## 🚀 Etapas da Abordagem

1. Acessa o SEI e baixa o arquivo completo  
2. Separa por período (2026)  
3. Acessa o SEI e baixa o último arquivo em PDF  
4. Modificar o código para acrescentar mais um arquivo aos existentes → **TODO**  
5. O script junta os PDFs  
6. Processamento dos dados  
7. Geração de arquivo de saída em CSV  
8. Criação de painéis no Power BI  

---

## 🆕 Versão 5

### 🔍 1. Melhorias

#### 1.1 Conflito estrutural em `ORGAOS_VALIDOS`

Existe um problema de ambiguidade entre siglas:

- `"SMP"` é válida  
- `"SMPG"` também é válida  

Como `"SMP"` está contido em `"SMPG"`, a lógica antiga podia retornar o valor incorreto:

```python
"SMP" in "SMPG"  # True
```

1.2 Problema raiz identificado

A lógica antiga utilizava:

if org in t

Consequências:

Dependência da ordem do set (não determinística)
Possíveis conflitos:
SMP vs SMPG
SMS vs SMSEG
SMAP vs SMP
1.3 Correção 1 — orgao_por_texto (fallback textual)
Substituição da busca por substring por word boundary (\b)
Exemplo:
\bSMP\b

✔ Evita match dentro de "SMPG"
✔ Em caso de múltiplos matches, retorna a sigla mais longa (mais específica)

1.4 Correção 2 — canonizar_sigla (via CSV)

Problema:

O OCR pode gravar "SMP" diretamente no coordenadas_orgaos.csv
Nesse caso, o valor não passava pelo fallback textual

Solução:

Criada função de canonização de sigla
Regra aplicada:

Se uma sigla for prefixo estrito de exatamente uma outra sigla válida → promove para a mais longa

Exemplos:

SMP → SMPG ✅
SMS → (SMSEG ou SMSURB) ❌ (ambíguo, mantém original)
📦 Versão 3
🔧 Modificações
Extração da coluna "PROCESSO SEI"
Tipo texto com números, pontos e traços
Não funcionava na versão 2
Remoção de campos:
"CÓDIGO" (truncado)
"QT"
"VALOR"
Inclusão do campo "TOTAL"
Critérios:
Deve conter "R$" seguido de valor monetário
Um único "ÓRGÃO" pode ter múltiplos "TOTAL"
Nestes casos, repetir o valor de "ÓRGÃO"
Problemas de "0 ocorrências":
Encoding estranho do PDF (cid: fonts)
Texto quebrado (OCR ruim)
Regex muito rígida
Melhorias adicionais:
Lista de verificação para identificar siglas de órgãos:
Ex: "PGM", "SMGG", etc.

Regex para "PROCESSO SEI" no formato:

00.0.000000000-0
Validação por score de confiança do OCR
Correção automática de caracteres:
0 ↔ O
1 ↔ I
Log de processos inválidos (debug profissional)
📊 Saída
Arquivo CSV estruturado
Integração com Power BI para visualização
⚠️ TODO
Permitir inclusão dinâmica de novos PDFs no pipeline
