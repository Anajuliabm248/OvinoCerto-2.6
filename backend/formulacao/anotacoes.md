# Automação da formulação conforme exigências

A formulação sera desenvolvida baseada nas exigências, considerando filtros para cada uma das exigências onde o usuário pode optar pelo default igual, ou menor ou maior do que a exigência. Além de filtros por menor custo e sendo baseado na categoria e fase do lote correspondente.

## Exigências nutricionais por categoria/fase

As necessidades de energia e proteína variam conforme peso corporal e função produtiva. Em geral:

### Cordeiros em crescimento (pós-desmama, 20–50 kg): 
demanda proteica alta para ganho de peso (p. ex. um cordeiro de 50 kg ganhando 200 g/dia requer ~1,51 kg MS, ~3,27 Mcal EM e ~102 g proteína bruta/dia; em outra tabela, 50 kg +200 g requer ~136,6 Mcal e 95 g PB). Em termos relativos, rações de engorda costumam ter 16–18% PB (embora a exigência líquida de PM seja menor).

### Ovelhas em manutenção (50–60 kg): 
exigência modesta, cerca de 7% de PB na dieta. Em valores absolutos, aproximando-se de 2–3 Mcal/dia e ~60–80 g de proteína/dia (varia com peso e atividade). A ingestão de MS deve ser ~2–3% do PV (p. ex. ~1,0–1,5 kg MS/dia para 50–60 kg).

### Gestação: 
aumenta na fase final (3º tri) devido ao crescimento fetal. Exemplo: uma ovelha de 60 kg com uma cria precisa de ~4,40–4,93 Mcal e ~108–127 g proteína metabolizável (PM) no final da gestação. Para gêmeos ou trigêmeos, esses valores sobem (p.ex. até ~4,40 Mcal e 121 g PM para duas crias). No início da gestação, as exigências são cerca de 15–20% menores.

### Lactação: 
pico de exigência no início da lactação, especialmente com múltiplos filhotes. Exemplo: ovelha de 50 kg amamentando dois cordeiros requer ~3,85 Mcal EM e 170 g PM/dia no início da lactação. Para três cria, sobe para ~4,49 Mcal e 209 g PM (50 kg). No final da lactação, cai significativamente (com dois cria: ~3,06 Mcal e 110 g PM; com um cria: ~2,40 Mcal e 80 g PM).

### Carneiros (reprodutores): mantêm-se em condição corporal moderada; necessidades próximas às de manutenção acrescidas de ~10–20% durante pré-cria (flushing) para estimular a libido. Por ex., um carneiro de ~70 kg de manutenção consome ~3–4 Mcal e ~100–130 g PB/dia.

### Reposição/novilhas:
 exigências intermediárias entre cordeiros e ovelhas adultas. Por exemplo, novilhas de 40–60 kg ganhando 150–300 g/dia requerem ~1,5–2,6 Mcal e 75–130 g PB.

Esses valores baseiam-se em tabelas do NRC (2007), INRA e Embrapa adaptadas à realidade brasileira. Em resumo, para cada categoria recomenda-se cumprir os níveis mínimos de proteína bruta e energia metabolizável descritos nas referências: por exemplo, na engorda de cordeiros cerca de 16–20% de PB e 70–85% de nutrientes digestíveis totais (NDT) na dieta, enquanto o apoio mineral (Ca, P) deve seguir as proporções ~2:1 (Ca:P) .


### métodos de otimização

#### programação linear:
define um único objetivo e só gera uma solução, ex: custo (atende as exigências mínimas de nutrientes)

#### Programação por metas:
extensão do PL, hierarquizando objetivos e permitindo definir prioridades. ex: satisfazer primeiro PB e depois custo

#### soma ponderada:
cria um único objetivo como combinação linear dos objetivos, mas requer escolha arbitrária de pesos.

#### abordagem pareto: 
escolhe um objetivo principal e trata os outros como restrições com limites, repetindo o PL várias vezes para diferentes metas, mas tem alto custo computacional e é difícil de escalar se muitos objetivos

#### algoritmos evolutivos multiobjetivo:
Codificam as proporções da dieta como “indivíduos” em uma população e evoluem as soluções por seleção e cruzamento, calculando múltiplos fitness (custo, PB, FDN), mas são computacionalmente intensivos

Você vai desenvolver APENAS o módulo de formulação automatizada de rações do sistema OvinoCerto, usando como base o projeto Django já existente. Não altere módulos fora do necessário para essa funcionalidade. O restante do sistema já existe e deve ser reaproveitado, especialmente os dados de exigências nutricionais e ingredientes já cadastrados.

OBJETIVO DO MÓDULO

Criar um fluxo completo de formulação de ração para ovinos em Django + Django REST Framework, usando Python, NumPy, Pandas e SciPy, com suporte a otimização por múltiplos critérios, respeitando categoria, fase, peso vivo e GMD do lote.

O usuário deve conseguir:
1. Selecionar um lote.
2. Carregar automaticamente a exigência nutricional correspondente à categoria e fase.
3. Escolher, para cada nutriente relevante, o operador desejado:
   - "="
   - ">="
   - "<="
4. Definir um ou mais objetivos de otimização, como:
   - minimizar custo
   - maximizar PB
   - maximizar NDT
   - minimizar FDN
   - minimizar uso de um ingrediente
   - ou combinar objetivos com pesos
5. Rodar a formulação.
6. Visualizar a fórmula resultante, os nutrientes obtidos, o custo final e possíveis alternativas/recomendações de ingredientes para melhorar a solução.

REGRA CENTRAL DE NEGÓCIO

A categoria e a fase do lote não são opcionais: elas definem a base da exigência nutricional.
Os filtros do usuário não substituem essa base. Eles apenas refinam o problema de otimização.
A sequência obrigatória do sistema é:

1. Identificar o lote
2. Buscar a exigência nutricional base correspondente à categoria e fase
3. Aplicar os operadores escolhidos pelo usuário para cada nutriente
4. Montar as restrições nutricionais e de inclusão de ingredientes
5. Resolver a otimização
6. Exibir o resultado
7. Sugerir ingredientes alternativos ou melhorias, se houver

ESCOPO

Trabalhe somente nesta parte:
- backend Django
- API REST
- models auxiliares, serializers, services, utils
- integração com o solver em Python/SciPy
- retorno da solução e das recomendações

Não implemente telas completas de frontend, exceto se for necessário criar endpoints e contratos de resposta.

REGRAS IMPORTANTES DE MODELAGEM

1. O sistema deve permitir que o usuário defina operadores por nutriente.
   Exemplo:
   - PB >= exigência
   - NDT >= exigência
   - FDN <= exigência
   - Ca = exigência
   - P >= exigência

2. O sistema deve aceitar múltiplos objetivos simultâneos.
   O custo pode ser o principal, mas também pode coexistir com outros objetivos.
   Isso pode ser resolvido com:
   - pesos por objetivo
   - função objetivo composta
   - variáveis de desvio
   - ou outra abordagem estável com SciPy

3. O sistema deve garantir a viabilidade:
   - soma das proporções dos ingredientes = 100% ou 1.0, conforme a convenção adotada
   - limites mínimos e máximos por ingrediente, se existirem
   - respeitar as restrições nutricionais escolhidas
   - impedir soluções matematicamente válidas, mas nutricionalmente absurdas

4. Ingredientes adicionais podem ser considerados como:
   - ingredientes cadastrados no banco
   - ingredientes recomendados para teste de melhoria
   - ou ingredientes candidatos simulados, se já existirem na base

5. Se a solução não for viável com os ingredientes disponíveis, o sistema deve retornar:
   - motivo da inviabilidade
   - quais restrições ficaram apertadas ou impossíveis
   - sugestões de ingredientes que poderiam ajudar, se houver dados para isso

6. Toda a lógica de formulação deve ficar desacoplada do restante do sistema.
   Crie uma camada de serviço/solver separada do controller/view.

ARQUITETURA ESPERADA

Crie algo nessa linha:

- app Django dedicada ao módulo de formulação
- serializers para entrada e saída
- views/api endpoints
- service principal de formulação
- módulo solver separado
- módulo de recomendação/sugestão de ingredientes
- utilitários para calcular composição final, custo e checagem de restrições

MODELOS / ENTIDADES ESPERADAS

Use os modelos já existentes do projeto se eles já cobrem isso. Se faltar alguma estrutura auxiliar, crie apenas o mínimo necessário.

Estruturas mínimas esperadas:
- Lote
- ExigenciaNutricional
- Ingrediente
- Formulação/ResultadoFormula
- RestriçãoNutricional
- ObjetivoOtimizacao

Se os modelos já existirem, adapte apenas o necessário.

COMPORTAMENTO DA API

Crie endpoints REST para:

1. Listar lotes disponíveis para formulação
2. Carregar a exigência base de um lote
3. Receber uma requisição de formulação com:
   - id do lote
   - operadores por nutriente
   - objetivos de otimização
   - pesos dos objetivos
   - ingredientes disponíveis ou filtros de inclusão/exclusão
4. Retornar:
   - formulação final
   - porcentagem de cada ingrediente
   - nutrientes finais obtidos
   - custo total
   - status da solução
   - mensagens de validação ou inviabilidade
5. Opcionalmente retornar recomendações de ingredientes para melhoria

FORMATO DA ENTRADA

A API deve aceitar algo como:

{
  "lote_id": 123,
  "restricoes": [
    {"nutriente": "PB", "operador": ">=", "valor": 16},
    {"nutriente": "NDT", "operador": ">=", "valor": 72},
    {"nutriente": "FDN", "operador": "<=", "valor": 35},
    {"nutriente": "Ca", "operador": "=", "valor": 0.65},
    {"nutriente": "P", "operador": ">=", "valor": 0.30}
  ],
  "objetivos": [
    {"tipo": "CUSTO", "peso": 70},
    {"tipo": "PB", "peso": 20},
    {"tipo": "FDN", "peso": 10}
  ],
  "ingredientes_incluidos": [1, 2, 3],
  "ingredientes_excluidos": [8, 9],
  "permitir_recomendacoes": true
}

SOLVER

Use SciPy para resolver a otimização.
Pode usar programação linear, quadrática ou outra abordagem apropriada, desde que:
- seja estável
- seja explicável
- seja fácil de manter

Sugestão:
- use `scipy.optimize.linprog` se o problema estiver linear
- se houver múltiplos objetivos, transforme-os em uma função objetivo ponderada
- use restrições lineares para os nutrientes
- trate igualdade como igualdade com tolerância pequena quando necessário
- normalize escalas para evitar que um nutriente “engula” os outros

O solver deve:
- montar o vetor de variáveis
- construir a função objetivo
- montar matriz de restrições
- rodar a otimização
- validar a solução
- montar o resultado final

REGRAS PARA OBJETIVOS

A formulação deve permitir:
- minimizar custo
- maximizar PB
- maximizar NDT
- minimizar FDN
- minimizar EE, se necessário
- outros objetivos futuros sem refatoração pesada

Implemente isso de modo que novos objetivos possam ser adicionados com facilidade.

RECOMENDAÇÕES DE INGREDIENTES

Crie uma camada que, quando a fórmula:
- não for viável
- ou for viável mas subótima
- ou houver sobra de margem para melhoria

possa sugerir ingredientes alternativos com base em:
- custo
- perfil nutricional
- impacto em PB, NDT, FDN, Ca, P
- compatibilidade com o lote e seus objetivos

Se possível, gere sugestões comparando a solução atual com variações pequenas de ingredientes.

REGRAS DE IMPLEMENTAÇÃO

1. Escreva código limpo, modular e comentado.
2. Não misture lógica de negócio com view.
3. Não coloque regra de otimização no serializer.
4. Não coloque regra de cálculo diretamente na view.
5. Não hardcode valores que já existem no banco.
6. Reutilize os dados do projeto atual.
7. Preserve o que já existe.
8. Faça tratamento de erro claro para:
   - lote inexistente
   - exigência inexistente
   - ingrediente ausente
   - problema sem solução
   - dados inválidos
9. Retorne respostas JSON bem estruturadas.
10. Se houver incerteza sobre o formato do banco atual, inspecione o projeto antes de criar algo novo.

CRITÉRIO DE SUCESSO

O módulo estará correto quando:
- um lote escolhido carregar sua exigência base automaticamente
- o usuário puder escolher operador por nutriente
- o usuário puder definir objetivos com pesos
- a API retornar uma formulação válida ou explicar por que não foi possível
- a solução usar os ingredientes e exigências já existentes no sistema
- o código ficar pronto para expansão futura sem bagunça arquitetural

ENTREGA ESPERADA

Quero o código implementado no projeto, não apenas explicação.
Se precisar criar arquivos novos, crie:
- app/formulacao/
- services/
- solvers/
- serializers/
- views/
- urls/
- tests/

Inclua também testes básicos do fluxo principal:
- formulação viável
- formulação inviável
- aplicação de restrições por operador
- cálculo de custo
- retorno de recomendações

Antes de codificar, leia a estrutura do projeto atual e adapte tudo ao que já existe.