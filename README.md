# manifestacao-py
## Versão: versão 5 em duas partes 
### Juntar PDFs: DOING   
### Extração dos dados: extrator_sei_Dv3.py
---------------Etapas da abordagem------------------------------------------------

0) Acessa o SEI, baixa o arquivo completo;
1) Separa por período (2026);
2) Acessa o SEI, baixa o último arquivo em PDF;
3) Modificar o código: acrescentar mais um arquivo aos existentes => TODO;
4) O script junta os PDFs;
5) Processamento;
6) Arquivo de saída em CSV
7) Cria os paines no Power BI
-----------------------Versão 5--------------------------------------------------
   
1. Melhorias
1.1 Há um conflito estrutural na "ORGAOS_VALIDOS":
"SMP" é uma sigla legítima no conjunto
"SMPG" também é legítima
Quando o OCR lê "SMPG" corretamente, o ``` loop for org ``` in ```ORGAOS_VALIDOS``` pode retornar "SMP" antes de chegar em "SMPG", porque "SMP" in "SMPG" é ```True``` — um prefixo casa dentro do outro

O fix correto não é um remendo pontual para SMPG/SMP — é resolver o problema raiz: a busca deve usar word boundary (```\b```) para comparar siglas, e deve sempre preferir a sigla mais longa quando houver ambiguidade de prefixo. Isso protege todos os pares similares presentes (ex: SMS vs SMSEG, SMP vs SMPG, SMAP, SMTC).
A linha 230 é a carga do "coordenadas_orgaos.csv" — se o OCR gravou "SMP" ali, ele entra direto sem passar pela função. Há necessidade de adicionar uma função de canonização de sigla que resolve esse caso também, e aplicar em ambos os pontos:
1.2. Problema raiz identificado
O bug não era só SMPG/SMP. Era estrutural: a busca antiga usava if org in t (substring simples), então "SMP" in "SMPG" retornava True. Como a iteração em sets é arbitrária, qual sigla vencia dependia da sorte. O mesmo problema potencial existia para SMS/SMSEG, SMAP/SMP, entre outros.

1.3. Correção 1 — orgao_por_texto (fallback textual)
Substituída a busca por substring por busca com word boundary (\b). Agora \bSMP\b não casa dentro de SMPG, porque o G não é um limite de palavra. Em caso de múltiplos matches válidos, retorna sempre o mais longo (mais específico).

1.4. Correção 2 — canonizar_sigla (fonte primária via CSV)
Quando o OCR grava "SMP" diretamente no coordenadas_orgaos.csv, o código aceitava essa sigla sem passar pelo fallback textual. A nova função verifica: "essa sigla é prefixo estrito de exatamente uma outra sigla válida?" — se sim, promove para a mais longa (SMP → SMPG). Se for ambíguo (ex: SMS poderia ser SMSEG ou SMSURB), mantém o original sem arriscar um erro pior.
 







--------------------------Versão 3---------------------------------------
   # Modificações da versão 3:

1) Extração da coluna "PROCESSO SEI" (é um dado tipo texto, com números, ponto e traço): versão 2 não conseguiu extrair o dado;
2) Retirar o campo "CÓDIGO": dado truncado, retirado na versão 3;
3) Outros campos retirados: "QT";  "VALOR"; 
4) Inserir o campo "TOTAL": 
	4.1) Critérios:
		- Deve conter "R$" seguido de espaço e o valor em na notação de moeda) Importante: um registro na coluna "ÓRGÃO" pode ter vários registros de "TOTAL" associados. 
		 - Nesses casos deve-se repetir o que está no campo "ÓRGÃO".
5) Problemas de retorno de "0 ocorrências":
'	5.1) encoding estranho do PDF (cid: fonts)
	5.2) texto quebrado (OCR ruim)
	5.3) regex rígida demais
6) Inserida lista de verificação para capturar o nome da Secretaria/Órgão (sigla de todas as UTs):"PGM"; "SMGG"; (...)
7) Inserido critérios para "PROCESSO SEI", restringindo o seguinte formato:  "00.0.000000000-0".
8) Validação por “score” de confiança do OCR;
9) Correção automática de caracteres (0 ↔ O, 1 ↔ I);
10) Log de processos inválidos (debug profissional)
