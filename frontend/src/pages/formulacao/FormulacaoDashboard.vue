<template>
  <div class="dashboard-page">
    <Header />

    <main class="content">

      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="dashboard-layout">

        <div class="diet-card">

          <div class="top-bar">
            <h3>Geração de Formulações</h3>
            <p class="subtitle">
              3. Formulação da Dieta
            </p>
          </div>

          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Ingrediente</th>
                  <th>MS(%)</th>
                  <th>MS(kg)</th>
                  <th>PB(%)</th>
                  <th>PB(kg)</th>
                  <th>NDT(%)</th>
                  <th>NDT(kg)</th>
                  <th>FDN(%)</th>
                  <th>FDN(kg)</th>
                  <th>EE(%)</th>
                  <th>EE(kg)</th>
                  <th>Ca(%)</th>
                  <th>Ca(kg)</th>
                  <th>P(%)</th>
                  <th>P(g)</th>
                  <th>MS Ingrediente</th>
                  <th>Custo</th>
                  <th>Ação</th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="item in dietIngredients"
                  :key="item.id"
                >
                  <td class="ingredient-name">{{ item.nome }}</td>
                  <td>
                    <input
                      v-model="item.ms"
                      class="ms-input"
                    />
                  </td>
                  <td>{{ item.msKg }}</td>
                  <td>{{ item.pbPct }}</td>
                  <td>{{ item.pbKg }}</td>
                  <td>{{ item.ndtPct }}</td>
                  <td>{{ item.ndtKg }}</td>
                  <td>{{ item.fdnPct }}</td>
                  <td>{{ item.fdnKg }}</td>
                  <td>{{ item.eePct }}</td>
                  <td>{{ item.eeKg }}</td>
                  <td>{{ item.caPct }}</td>
                  <td>{{ item.caKg }}</td>
                  <td>{{ item.pPct }}</td>
                  <td>{{ item.pG }}</td>
                  <td>{{ item.msIngrediente }}</td>
                  <td>
                    <span class="cost-pill">R$ {{ item.custo }}</span>
                  </td>
                  <td>
                    <button
                      class="remove-btn"
                      type="button"
                      @click="removeIngredient(item.id)"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="summary-wrapper">
            <table class="summary-table">
              <thead>
                <tr>
                  <th></th>
                  <th>MS(%)</th>
                  <th>MS(kg)</th>
                  <th>PB(%)</th>
                  <th>PB(kg)</th>
                  <th>NDT(%)</th>
                  <th>NDT(kg)</th>
                  <th>FDN(%)</th>
                  <th>FDN(kg)</th>
                  <th>EE(%)</th>
                  <th>EE(kg)</th>
                  <th>Ca(%)</th>
                  <th>Ca(kg)</th>
                  <th>P(%)</th>
                  <th>P(g)</th>
                </tr>
              </thead>

              <tbody>
                <tr
                  v-for="row in summaryRows"
                  :key="row.label"
                >
                  <td class="row-label">{{ row.label }}</td>
                  <td>{{ row.msPct }}</td>
                  <td>{{ row.msKg }}</td>
                  <td>{{ row.pbPct }}</td>
                  <td>{{ row.pbKg }}</td>
                  <td>{{ row.ndtPct }}</td>
                  <td>{{ row.ndtKg }}</td>
                  <td>{{ row.fdnPct }}</td>
                  <td>{{ row.fdnKg }}</td>
                  <td>{{ row.eePct }}</td>
                  <td>{{ row.eeKg }}</td>
                  <td>{{ row.caPct }}</td>
                  <td>{{ row.caKg }}</td>
                  <td>{{ row.pPct }}</td>
                  <td>{{ row.pG }}</td>
                </tr>

                <tr class="status-row">
                  <td></td>
                  <td
                    v-for="status in statusRow"
                    :key="status.label"
                    colspan="2"
                    :class="['status-cell', statusClass(status.label)]"
                  >
                    {{ status.label }}
                  </td>
                </tr>
              </tbody>
            </table>

            <div class="ms-composition">
              <p>
                <span>% da MS (volumoso)</span>
                <strong>{{ msVolumoso }}%</strong>
              </p>
              <p>
                <span>% da MS (concentrado)</span>
                <strong>{{ msConcentrado }}%</strong>
              </p>
            </div>
          </div>

        </div>

        <aside class="info-card">

          <div class="chart-block">
            <p class="chart-title">% de Ingrediente na MN</p>

            <div class="chart-row">
              <div
                class="pie"
                :style="{ background: ingredientPieGradient }"
              ></div>

              <ul class="legend">
                <li
                  v-for="slice in ingredientPie"
                  :key="slice.label"
                >
                  <span
                    class="dot"
                    :style="{ background: slice.color }"
                  ></span>
                  {{ slice.label }}
                </li>
              </ul>
            </div>
          </div>

          <div class="chart-block">
            <p class="chart-title">% do custo (R$) por ingrediente na MN</p>

            <div class="chart-row">
              <div
                class="pie"
                :style="{ background: costPieGradient }"
              ></div>

              <ul class="legend">
                <li
                  v-for="slice in costPie"
                  :key="slice.label"
                >
                  <span
                    class="dot"
                    :style="{ background: slice.color }"
                  ></span>
                  {{ slice.label }}
                </li>
              </ul>
            </div>
          </div>

          <ul class="info-list">
            <li>
              <span>Categoria:</span>
              <strong>{{ animalInfo.categoria }}</strong>
            </li>
            <li>
              <span>Fase:</span>
              <strong>{{ animalInfo.fase }}</strong>
            </li>
            <li>
              <span>Tipo de Parto:</span>
              <strong>{{ animalInfo.tipoParto }}</strong>
            </li>
            <li>
              <span>PV (kg):</span>
              <strong>{{ animalInfo.pv }}</strong>
            </li>
            <li>
              <span>GMD (kg):</span>
              <strong>{{ animalInfo.gmd }}</strong>
            </li>
            <li>
              <span>PV (%):</span>
              <strong>{{ animalInfo.pvPct }}</strong>
            </li>
            <li>
              <span>CMS (kg):</span>
              <strong>{{ animalInfo.cms }}</strong>
            </li>
          </ul>

          <div class="cost-summary">
            <p class="cost-value">
              R$/kg MN
              <strong>{{ custoPorKg }}</strong>
            </p>

            <p class="ratio-value">
              Relação Ca/P
              <strong>{{ relacaoCaP }}</strong>
            </p>
          </div>

        </aside>

      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Header from '@/components/Header.vue'

const tabs = [
  { key: 'formulacao', label: 'Formulação da Dieta' },
  { key: 'dados', label: 'Dados da Dieta' },
  { key: 'ajustes-dieta', label: 'Ajustes da Dieta' },
  { key: 'custos', label: 'Custos e Viabilidade' },
  { key: 'ajustes-alimentacao', label: 'Ajustes de Alimentação' },
  { key: 'observacoes', label: 'Observações' },
  { key: 'relatorio', label: 'Gerar Relatório' },
]

const activeTab = ref('formulacao')

const dietIngredients = ref(
  Array.from({ length: 6 }, (_, index) => ({
    id: index + 1,
    nome: 'Capim Elefante Feno',
    ms: '10',
    msKg: '0.06080',
    pbPct: '5.87',
    pbKg: '0.0036',
    ndtPct: '46.85',
    ndtKg: '0.0285',
    fdnPct: '77.49',
    fdnKg: '0.0471',
    eePct: '1.73',
    eeKg: '0.0011',
    caPct: '0.30',
    caKg: '0.1874',
    pPct: '0.16',
    pG: '0.0973',
    msIngrediente: '86.85',
    custo: '1.00',
  }))
)

function removeIngredient(id) {
  dietIngredients.value = dietIngredients.value.filter(
    (item) => item.id !== id
  )
}

const summaryRows = [
  {
    label: 'Dieta',
    msPct: '100.00', msKg: '0.6080',
    pbPct: '11.13', pbKg: '0.0676',
    ndtPct: '51.69', ndtKg: '0.3143',
    fdnPct: '69.46', fdnKg: '0.4223',
    eePct: '1.85', eeKg: '0.0112',
    caPct: '0.71', caKg: '4.3',
    pPct: '0.52', pG: '3.1',
  },
  {
    label: 'Exigências',
    msPct: '100.00', msKg: '0.6080',
    pbPct: '11.13', pbKg: '0.0676',
    ndtPct: '51.69', ndtKg: '0.3143',
    fdnPct: '69.46', fdnKg: '0.4223',
    eePct: '1.85', eeKg: '0.0112',
    caPct: '0.71', caKg: '4.3',
    pPct: '0.52', pG: '3.1',
  },
  {
    label: 'Controle',
    msPct: '100.00', msKg: '0.6080',
    pbPct: '11.13', pbKg: '0.0676',
    ndtPct: '51.69', ndtKg: '0.3143',
    fdnPct: '69.46', fdnKg: '0.4223',
    eePct: '1.85', eeKg: '0.0112',
    caPct: '0.71', caKg: '4.3',
    pPct: '0.52', pG: '3.1',
  },
]

const statusRow = [
  { label: 'CERTO' },
  { label: 'DÉFICIT' },
  { label: 'DÉFICIT' },
  { label: 'EXCESSO' },
  { label: 'CERTO' },
  { label: 'DÉFICIT' },
  { label: 'DÉFICIT' },
]

function statusClass(label) {
  if (label === 'CERTO') return 'status-ok'
  if (label === 'EXCESSO') return 'status-excess'
  return 'status-deficit'
}

const msVolumoso = ref('100')
const msConcentrado = ref('0')

const ingredientPie = [
  { label: 'Capim Elefante Feno', value: 10.2, color: '#3b5bdb' },
  { label: 'Capim Coast Cross Feno', value: 59.9, color: '#c0392b' },
  { label: 'Alfafa Feno', value: 29.9, color: '#e07b1f' },
]

const costPie = [
  { label: 'Capim Elefante Feno', value: 3.7, color: '#3b5bdb' },
  { label: 'Capim Coast Cross Feno', value: 42.9, color: '#c0392b' },
  { label: 'Alfafa Feno', value: 53.4, color: '#e07b1f' },
]

function buildGradient(slices) {
  let cumulative = 0
  const stops = slices.map((slice) => {
    const start = cumulative
    cumulative += slice.value
    return `${slice.color} ${start}% ${cumulative}%`
  })
  return `conic-gradient(${stops.join(', ')})`
}

const ingredientPieGradient = computed(() => buildGradient(ingredientPie))
const costPieGradient = computed(() => buildGradient(costPie))

const animalInfo = ref({
  categoria: 'Cordeiros(as) (4 meses)',
  fase: 'Crescimento',
  tipoParto: '-',
  pv: '20.000',
  gmd: '0.3000',
  pvPct: '3.04',
  cms: '0.6080',
})

const custoPorKg = ref('2.79')
const relacaoCaP = ref('1.37')
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;

  background: var(--background);
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;

  padding: 24px;
}

.tabs {
  width: 100%;
  max-width: 1800px;

  display: flex;
  flex-wrap: wrap;
  gap: 2px;

  margin-bottom: -1px;

  padding-left: 32px;
}

.tab {
  border: none;

  padding: 10px 16px;

  border-radius: 18px 18px 0 0;

  cursor: pointer;

  background: var(--primary-dark);

  color: var(--white);

  font-size: 13px;
}

.tab.active {
  background: var(--card-bg);
  opacity: 1;
}

.dashboard-layout {
  width: 100%;
  max-width: 1800px;

  display: flex;

  gap: var(--space-lg);

  align-items: flex-start;
}

.diet-card {
  flex: 1;
  min-width: 0;

  background: var(--card-bg);

  border-radius: 24px;

  padding: var(--space-lg);

  box-shadow: var(--shadow-md);
}

.top-bar {
  margin-bottom: var(--space-md);
}

.top-bar h3 {
  margin: 0;

  color: var(--white);

  font-weight: 500;
}

.subtitle {
  margin: 0;

  color: rgba(255,255,255,.75);

  font-size: 14px;
}

.table-wrapper {
  max-height: 260px;
  overflow-y: auto;
  overflow-x: auto;

  border-radius: var(--radius-lg);

  background: var(--white);

  margin-bottom: var(--space-md);
}

table {
  width: 100%;

  border-collapse: collapse;

  white-space: nowrap;
}

thead {
  background: #e6e2d3;

  position: sticky;
  top: 0;

  z-index: 1;
}

th {
  padding: 10px 8px;

  text-align: center;
  line-height: 16px;

  font-size: 12px;
  font-weight: 500;

  color: var(--text);
}

td {
  padding: 4px 8px;

  text-align: center;

  font-size: 13px;
  line-height: 18px;

  border-top: 1px solid #d8d3c4;

  color: #666;
}

.ingredient-name {
  text-align: left;
  white-space: normal;

  min-width: 140px;
}

tbody tr:hover {
  background: #f8f7f2;
}

.ms-input {
  width: 44px;

  text-align: center;

  padding: 3px 0;

  border-radius: 999px;

  border: 1px solid #bbb;

  font-size: 13px;
}

.cost-pill {
  display: inline-block;

  padding: 3px 10px;

  border-radius: 999px;

  border: 1px solid #bbb;

  font-size: 13px;
}

.remove-btn {
  border: none;

  background: transparent;

  color: #c0392b;

  font-size: 18px;
  line-height: 1;

  cursor: pointer;
}

.summary-wrapper {
  background: var(--white);

  border-radius: var(--radius-lg);

  padding: var(--space-sm);
}

.summary-table {
  margin-bottom: var(--space-sm);
}

.row-label {
  text-align: left;
  font-weight: 600;

  color: var(--text);
}

.status-row td {
  border-top: 1px solid #d8d3c4;

  font-size: 11px;
  font-weight: 700;
  letter-spacing: .3px;
}

.status-ok {
  color: #2e7d32;
}

.status-deficit {
  color: #c0392b;
}

.status-excess {
  color: #2f5fd6;
}

.ms-composition {
  display: flex;
  gap: var(--space-lg);

  padding: 4px 12px;

  font-size: 13px;

  color: #666;
}

.ms-composition p {
  display: flex;
  gap: 6px;

  margin: 0;
}

.info-card {
  width: 320px;
  flex-shrink: 0;

  background: var(--white);

  border-radius: 24px;

  padding: var(--space-lg);

  box-shadow: var(--shadow-md);

  display: flex;
  flex-direction: column;

  gap: var(--space-md);
}

.chart-title {
  margin: 0 0 10px;

  font-size: 13px;
  font-weight: 600;

  color: var(--text);
}

.chart-row {
  display: flex;
  align-items: center;

  gap: var(--space-md);
}

.pie {
  width: 90px;
  height: 90px;
  flex-shrink: 0;

  border-radius: 50%;
}

.legend {
  list-style: none;

  margin: 0;
  padding: 0;

  display: flex;
  flex-direction: column;

  gap: 6px;

  font-size: 12px;

  color: #555;
}

.legend li {
  display: flex;
  align-items: center;

  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  flex-shrink: 0;

  border-radius: 50%;
}

.info-list {
  list-style: none;

  margin: 0;
  padding: 0;

  display: flex;
  flex-direction: column;

  gap: 6px;

  font-size: 13px;
}

.info-list li {
  display: flex;
  justify-content: space-between;

  color: #555;
}

.info-list strong {
  color: #2e7d32;
  font-weight: 600;
}

.cost-summary {
  display: flex;
  flex-direction: column;

  gap: 6px;

  padding-top: var(--space-sm);

  border-top: 1px solid #e2ddd0;
}

.cost-value,
.ratio-value {
  display: flex;
  justify-content: space-between;

  margin: 0;

  font-size: 13px;

  color: #555;
}

.cost-value strong {
  color: #2e7d32;
}

.ratio-value strong {
  color: #c0392b;
}

@media (max-width: 1200px) {
  .dashboard-layout {
    flex-direction: column;
  }

  .info-card {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .content {
    padding: var(--space-md);
  }

  .diet-card,
  .info-card {
    padding: var(--space-md);
  }

  .ms-composition {
    flex-direction: column;
    gap: 4px;
  }
}
</style>