# Dados Confirmados — Simulador Kanban Stateo 3/8

Este documento registra os dados de processo e as regras de Kanban informados para
a Stateo 3/8, complementando a especificação funcional (`Pasted_content.txt`).
Valores marcados como **a confirmar** são usados no protótipo como premissas
ajustáveis, não como fatos operacionais definitivos.

## Dados de processo

- **Demanda média informada:** 11.069 peças por semana.
- **Demanda diária aproximada:** 1.845 peças por dia produtivo.
  - 11.069 ÷ 6 dias = 1.844,83 ≈ 1.845 peças/dia.
  - 1.845 × 6 dias = 11.070 peças/semana — diferença de **1 peça** em relação aos
    11.069 informados, por arredondamento. Isso é esperado e documentado, não um erro.
- **Turnos (dias produtivos):**
  | Turno | Horas |
  |---|---|
  | Turno 1 | 7,42 h |
  | Turno 2 | 7,42 h |
  | Turno 3 | 5,33 h |
  | **Total/dia** | **20,17 h** |
- **Capacidade efetiva informada:** 75 peças/hora para a Stateo 3/8, **já considerando
  o rendimento de 76%**. Esse valor não deve ser multiplicado pelo rendimento novamente.
- **Capacidade nominal calculada:** 75 × 20,17 h = **1.512,75 peças/dia**; em 6 dias
  produtivos, **9.076,5 peças/semana**.
- **Comparação teórica (a confirmar):** a capacidade calculada fica **1.992,5 peças/semana**
  abaixo da demanda média informada (11.069 − 9.076,5). Isso é apresentado no app como um
  **alerta teórico para validação**, não como déficit operacional confirmado.
- **Divergência de taxa (a confirmar):** um ciclo de 37,97 s por peça com 76% de
  rendimento implica aproximadamente **72,1 peças/hora**, diferente das 75 peças/hora
  informadas. O simulador usa 75 peças/h como o valor efetivo reportado e expõe essa
  divergência para validação futura.
- **Operadores:** existem operadores por operação e por turno, mas a quantidade ainda
  não foi fornecida. Nenhum número foi presumido; o simulador **não** limita a produção
  por quantidade de operadores.

## Regras do Kanban

- Um roller contém **144 peças**.
- São **19 posições** no trilho: **13 verdes, 1 amarela e 5 vermelhas**.
- O protótipo interpreta a quantidade de cartões de cada zona como sua capacidade e
  inicia a simulação com os **19 rollers cheios**.
- A demanda diária é convertida em cartões/rollers inteiros **arredondando para cima**
  (`Pasted_content.txt`).
- **Reposição diária (clarificação do responsável pelo processo, 2026-10-01):** a cada
  dia, após o consumo da demanda, a máquina repõe o que a capacidade de produção diária
  permitir — não é necessário esperar o estoque cair na faixa amarela/vermelha
  (6 rollers no arranjo 13+1+5) para a produção começar. O trilho esvazia com o consumo
  e enche de volta com a produção do mesmo dia, podendo terminar no verde, no limiar ou
  na faixa amarela/vermelha, dependendo do saldo entre demanda e capacidade de produção.
  A faixa amarela/vermelha permanece como classificação visual de risco/alerta.
- **Rollers prontos** (estoque disponível para consumo) são mantidos separados do
  **roller em produção (WIP)**. O WIP não conta como estoque disponível até ser concluído.
- A variação de demanda diária é apenas demonstrativa: uma semana simulada de 6 dias
  preserva o total semanal informado de 11.069 peças (a variação muda a distribuição
  entre os dias, não o total). Valores manuais informados pelo usuário substituem os
  dias correspondentes e podem alterar o total.

## O que ainda não foi modelado

Falhas e manutenção; setup próprio da Stateo 3/8; estoque entre as quatro etapas do
processo; transporte e layout físico; restrição de 48 horas; sucata/qualidade;
múltiplos produtos e sequenciamento; quantidade de operadores por turno/operação.
