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

#### Problema raiz identificado
O bug não era só SMPG/SMP. Era estrutural: a busca antiga usava if org in t (substring simples), então "SMP" in "SMPG" retornava True. Como a iteração em sets é arbitrária, qual sigla vencia dependia da sorte. O mesmo problema potencial existia para SMS/SMSEG, SMAP/SMP, entre outros.
##### Correção 1 — orgao_por_texto (fallback textual)
Substituída a busca por substring por busca com word boundary (\b). Agora \bSMP\b não casa dentro de SMPG, porque o G não é um limite de palavra. Em caso de múltiplos matches válidos, retorna sempre o mais longo (mais específico).
##### Correção 2 — canonizar_sigla (fonte primária via CSV)
Quando o OCR grava "SMP" diretamente no coordenadas_orgaos.csv, o código aceitava essa sigla sem passar pelo fallback textual. A nova função verifica: "essa sigla é prefixo estrito de exatamente uma outra sigla válida?" — se sim, promove para a mais longa (SMP → SMPG). Se for ambíguo (ex: SMS poderia ser SMSEG ou SMSURB), mantém o original sem arriscar um erro pior.
