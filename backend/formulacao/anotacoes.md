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

# Calculos

cms -> consumo de matéria seca (quandtidade max de alimento seco que o animal consegue digerir)
    - é definido pela tabela nrc de exigências


# Serializers -> FormulacaoDetailSerializer

a porcentagem do nutriente é calculada pela soma dos kgs de cada nutriente, e dividido entre o consumo de matéria seca por kg (cms_kg)
depois converte o kg/dia / cms_kg x 100 em % da matéria seca (MS)
verifica o valor obtido pelo exigido e operador (<=, >=, ==), com tolerância de 0.05
e retorna cada nutriente/kg 

# Linear solver 

### _build_objective -> 
monta o que o linprog vai minimizar e maximizar
````
if objetivo == 'CUSTO': c[i] = ing.custo_kg
elif objetivo == 'PB':  c[i] = -ing.pb     # maximizar = minimizar negativo
elif objetivo == 'FDN': c[i] = ing.fdn
````

### _build_ineq ->
converte o operador >= para <= multiplicando por -1 os dois lados da inequação
ja que o liprog só aceita restrições de desigualdade no formato <=

### _build_eq ->
garante que as frações somem 1, resultando em 100% da dieta

### _calc_nutrientes
o sistema calcula cada nutriente da mistura por média ponderada (simplex). EX:
- Se 70% da mistura é milho (que tem 11% de proteína) e 30% é farelo de soja (que tem 45% de proteína), a proteína total da mistura é:
> 0,70 × 11% + 0,30 × 45% = 7,7% + 13,5% = 21,2%
- O sistema faz esse cálculo para todos os nutrientes ao mesmo tempo, com todos os ingredientes, e vai ajustando as proporções até encontrar uma combinação que:
    - Atenda todas as regras nutricionais
    - Minimize (ou maximize) o objetivo escolhido