# manifestacao-py
## Versão: Extração - Manifestão de compra v 2 1 0
## Nome do arquivo python: Manifesta_v 2 1 0.py
## Etapas da rotina 2026 será: 
1) Acessa o SEI, baixa o último arquivo em PDF;
2) Modificar o código: acrescentar mais um arquivo aos existentes => TODO;
3) O script junta os PDFs;
4) Processamento;
5) Arquivo de saída em CSV
6) Cria os paines no Power BI

   ------------------------Versão 3---------------------------------------
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
