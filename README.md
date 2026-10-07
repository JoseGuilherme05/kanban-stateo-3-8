# Simulador de Kanban de Produção — Stateo 3/8

Protótipo em Python + Streamlit, pronto para abrir no VS Code. A especificação principal é o arquivo funcional enviado (`Pasted_content.txt`); o PPTX e os documentos complementares servem como contexto e fonte secundária de parâmetros.

## Executar no VS Code

1. Instale Python 3.10 ou superior.
2. Abra esta pasta no VS Code.
3. No terminal integrado, crie e ative um ambiente virtual:

   **Windows (PowerShell)**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Instale as dependências e inicie o app:

   ```bash
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

O Streamlit abrirá o simulador no navegador. O código fica local e editável no VS Code.

## O que o protótipo simula

- Trilho vertical com zonas verde, amarela e vermelha.
- 19 posições por padrão: 13 verdes, 1 amarela e 5 vermelhas.
- 144 peças por roller.
- Estado inicial cheio (19 rollers; capacidade de 2.736 peças).
- Demanda variável dia a dia, ancorada na demanda semanal confirmada de 11.069 peças (1.845 peças/dia em 6 dias produtivos); a variação diária é apenas demonstrativa, não uma série histórica real — veja `dados_confirmados.md`.
- Conversão da demanda diária em cartões por arredondamento para cima.
- Retirada dos cartões ao longo das horas de operação.
- A cada dia, após o consumo, a máquina repõe o que a capacidade de produção diária permitir — não espera o estoque cair na faixa amarela/vermelha (6 rollers no cenário padrão) para começar. O nível sobe e desce dia a dia, podendo terminar no verde, no limiar ou na faixa amarela/vermelha.
- Produção na taxa configurada e liberação de um roller por vez ao completar 144 peças; rollers prontos ficam separados do roller em produção (WIP), que não conta como estoque disponível.
- Máquina em produção até o estoque voltar à capacidade máxima ou esgotar a capacidade de produção do dia.
- Painel de capacidade teórica vs. demanda informada: 3 turnos (7,42 + 7,42 + 5,33 = 20,17 h/dia), 75 peças/h efetivas, 1.512,75 peças/dia, 9.076,5 peças/semana (6 dias produtivos) comparadas aos 11.069 peças/semana informados — apresentado como alerta teórico para validação, não déficit confirmado.
- Histórico diário, gráfico do estoque, rupturas, arredondamento e exportação CSV.

## Premissas visíveis e editáveis

- **Demanda:** 1.845 peças/dia (11.069/semana ÷ 6 dias, com 1 peça de diferença por arredondamento) é o valor informado; a variação diária em torno dessa média é sintética e demonstrativa. Use a entrada de demandas manuais para substituir dias por valores reais.
- **Produção:** 75 peças/h é a taxa efetiva informada, já considerando o rendimento de 76% — não é aplicado novamente no cálculo.
- **Conferência da taxa:** 37,97 s por peça × 76% de rendimento implica aproximadamente 72,1 peças/h, diferente das 75 peças/h informadas. O simulador usa 75 como dado reportado, mas essa taxa precisa ser validada.
- **Horas por dia:** 20,17 h/dia é a soma dos 3 turnos informados (7,42 + 7,42 + 5,33 h); editável no simulador caso outra jornada se aplique.
- **19 posições cheias:** a capacidade padrão atual é a soma de 13 cartões verdes, 1 amarelo e 5 vermelhos. O protótipo interpreta os números das zonas como a capacidade de cada faixa e inicia com o trilho cheio.
- **Operadores:** existem operadores por operação/turno, mas a quantidade não foi informada; o simulador não limita a produção por esse fator.
- Consumo e produção ocorrem dentro da mesma janela de operação, e a demanda se distribui uniformemente nesse período.
- A máquina repõe todo dia em que há consumo, limitada pela capacidade de produção diária; a faixa amarela/vermelha é uma classificação visual de risco, não o gatilho exclusivo da produção.

## Ainda não modelado

Falhas e manutenção; setup próprio da Stateo 3/8; estoque entre as quatro etapas; transporte e layout físico; restrição de 48 horas; sucata/qualidade; múltiplos produtos e sequenciamento; quantidade de operadores por turno/operação. Os tempos de setup encontrados no arquivo complementar referem-se à Impregnação Mazzali e à Finição Automática, não foram aplicados automaticamente à Stateo 3/8.

## Arquivos

- `app.py`: interface Streamlit.
- `simulation.py`: lógica principal, independente da interface.
- `tests/test_simulation.py`: testes automatizados da lógica.
- `requirements.txt`: dependências.
- `Pasted_content.txt`: cópia da especificação funcional principal usada como base do modelo.
- `dados_confirmados.md`: dados de processo e regras de Kanban confirmados (turnos, taxa efetiva, demanda semanal, operadores pendentes).
