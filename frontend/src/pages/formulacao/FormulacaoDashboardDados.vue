<template>
  <PageCard title="Dados da Dieta">
    <template #top-tabs>
      <TabsHeader :tabs="abas" v-model="abaAtiva" />
    </template>

    <template #top-bar-extra>
      <div class="top-bar-actions">
        <Botao label="Cancelar" variant="ghost" type="button" />
        <Botao label="Voltar" variant="ghost" type="button" />
        <Botao label="Salvar" variant="primary" type="button" />
      </div>
    </template>

    <div class="quadros-grid">
      <div class="quadros-column quadros-column--left">
        <Quadro titulo="Quadro 1.0: Dados da Dieta">
          <table class="quadro-table">
          <thead>
            <tr>
              <th>Classificação</th>
              <th>Tipo</th>
              <th>Ingrediente</th>
              <th class="num">MS Kg</th>
              <th class="num">MN Kg</th>
              <th class="num">% MS</th>
              <th class="num">% MN</th>
              <th class="num">R$/Kg MN</th>
              <th class="num">R$/Dia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in ingredientesDieta" :key="item.ingrediente">
              <td>{{ item.classificacao }}</td>
              <td>{{ item.tipo }}</td>
              <td>{{ item.ingrediente }}</td>
              <td class="num">{{ item.msKg }}</td>
              <td class="num">{{ item.mnKg }}</td>
              <td class="num">{{ item.msPct }}</td>
              <td class="num">{{ item.mnPct }}</td>
              <td class="num">{{ item.custoKg }}</td>
              <td class="num">{{ item.custoDia }}</td>
            </tr>

            <tr class="quadro-total">
              <td>-----</td>
              <td></td>
              <td>Dieta</td>
              <td class="num">{{ totalDieta.msKg }}</td>
              <td class="num">{{ totalDieta.mnKg }}</td>
              <td class="num">{{ totalDieta.msPct }}</td>
              <td class="num">{{ totalDieta.mnPct }}</td>
              <td class="num">{{ totalDieta.custoKg }}</td>
              <td class="num">{{ totalDieta.custoDia }}</td>
            </tr>
          </tbody>
        </table>
      </Quadro>

        <Quadro titulo="Quadro 2: Exigência Nutricional da Categoria, Composição Bromatológica da Dieta e Resultados Obtidos">
          <table class="quadro-table">
          <thead>
            <tr>
              <th></th>
              <th class="num">MS (%) da Dieta</th>
              <th class="num">PB %</th>
              <th class="num">NDT %</th>
              <th class="num">FDN %</th>
              <th class="num">EE %</th>
              <th class="num">Ca %</th>
              <th class="num">P %</th>
              <th class="num">Ca/P</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="linha in exigenciaResultados" :key="linha.label">
              <td>{{ linha.label }}</td>
              <td class="num">{{ linha.msPct }}</td>
              <td class="num">{{ linha.pb }}</td>
              <td class="num">{{ linha.ndt }}</td>
              <td class="num">{{ linha.fdn }}</td>
              <td class="num">{{ linha.ee }}</td>
              <td class="num">{{ linha.ca }}</td>
              <td class="num">{{ linha.p }}</td>
              <td class="num">{{ linha.caP }}</td>
            </tr>

            <tr class="status-row">
              <td></td>
              <td></td>
              <td
                v-for="status in statusResultados"
                :key="status"
                class="num"
                :class="statusClass(status)"
              >
                {{ status }}
              </td>
            </tr>
          </tbody>
        </table>
      </Quadro>
      </div>

      <div class="quadros-column quadros-column--right">
        <Quadro titulo="Quadro 1.1: Dados da Dieta">
          <table class="quadro-table">
          <thead>
            <tr>
              <th></th>
              <th class="num">MN Kg Total</th>
              <th class="num">% MS</th>
              <th class="num">% MN</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="grupo in composicaoDieta"
              :key="grupo.label"
              :class="{ 'quadro-total': grupo.total }"
            >
              <td>{{ grupo.label }}</td>
              <td class="num">{{ grupo.mnKgTotal }}</td>
              <td class="num">{{ grupo.msPct }}</td>
              <td class="num">{{ grupo.mnPct }}</td>
            </tr>
          </tbody>
        </table>
      </Quadro>

        <Quadro titulo="Quadro 1.2: Mistura Concentrada">
          <table class="quadro-table">
          <thead>
            <tr>
              <th>Ingrediente</th>
              <th class="num">% MS</th>
              <th class="num">MN (100 kg)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ misturaConcentrada.ingrediente || '-' }}</td>
              <td class="num">{{ misturaConcentrada.msPct }}</td>
              <td class="num">{{ misturaConcentrada.mnKg }}</td>
              <td class="num">
                <CampoTexto
                  v-model="misturaConcentrada.quantidade"
                  class="quadro-input"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </Quadro>
      </div>
    </div>

  </PageCard>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageCard from '@/components/ui/PageCard.vue'
import TabsHeader from '@/components/ui/TabsHeader.vue'
import Quadro from '@/components/ui/Quadro.vue'
import Botao from '@/components/ui/Botao.vue'
import CampoTexto from '@/components/ui/CampoTexto.vue'

// Mesmas abas usadas em FormulacaoDashboard — aqui a ativa é "Dados da Dieta"
const abas = [
  { key: 'formulacao', label: 'Formulação da Dieta' },
  { key: 'dados', label: 'Dados da Dieta' },
  { key: 'ajustes-dieta', label: 'Ajustes da Dieta' },
  { key: 'custos', label: 'Custos e Viabilidade' },
  { key: 'ajustes-alimentacao', label: 'Ajustes de Alimentação' },
  { key: 'observacoes', label: 'Observações' },
  { key: 'relatorio', label: 'Gerar Relatório' },
]

const router = useRouter()
const abaAtiva = ref('dados')

const rotaPorAba = {
  formulacao: 'FormulacaoDashboard',
  dados: 'FormulacaoDashboardDados',
  'ajustes-dieta': 'FormulacaoAjustesDieta',
  custos: 'FormulacaoCustos',
  'ajustes-alimentacao': 'FormulacaoAjustesAlimentacao',
  observacoes: 'FormulacaoObservacoes',
  relatorio: 'FormulacaoRelatorio',
}

watch(abaAtiva, (value) => {
  const rota = rotaPorAba[value]
  if (rota) {
    router.push({ name: rota })
  }
})

// Quadro 1.0
const ingredientesDieta = [
  {
    classificacao: 'Volumoso',
    tipo: 'Forragens Secas',
    ingrediente: 'Capim Elefante Feno',
    msKg: '0.0608',
    mnKg: '0.0700',
    msPct: '10.000000',
    mnPct: '10.23',
    custoKg: 'R$1.00',
    custoDia: 'R$0.07',
  },
  {
    classificacao: 'Volumoso',
    tipo: 'Forragens Secas',
    ingrediente: 'Capim Coast Cross Feno',
    msKg: '0.3648',
    mnKg: '0.4100',
    msPct: '60.000000',
    mnPct: '59.92',
    custoKg: 'R$2.00',
    custoDia: 'R$0.82',
  },
  {
    classificacao: 'Volumoso',
    tipo: 'Forragens Secas',
    ingrediente: 'Alfafa Feno',
    msKg: '0.1824',
    mnKg: '0.2043',
    msPct: '30.000000',
    mnPct: '29.85',
    custoKg: 'R$5.00',
    custoDia: 'R$1.02',
  },
]

const totalDieta = {
  msKg: '0.6080',
  mnKg: '0.6843',
  msPct: '100.000000',
  mnPct: '100.00',
  custoKg: 'R$2.79',
  custoDia: 'R$1.91',
}

// Quadro 1.1
const composicaoDieta = [
  { label: 'Volumoso', mnKgTotal: '0.6843', msPct: '100.000000', mnPct: '100.0000' },
  { label: 'Concentrado', mnKgTotal: '0.0000', msPct: '0.000000', mnPct: '0.0000' },
  { label: 'Total', mnKgTotal: '0.6843', msPct: '100.000000', mnPct: '100.0000', total: true },
]

// Quadro 1.2
const misturaConcentrada = reactive({
  ingrediente: '',
  msPct: '0.00',
  mnKg: '0.00',
  quantidade: '300',
})

// Quadro 2
const exigenciaResultados = [
  {
    label: 'Exigência',
    msPct: '-----',
    pb: '24.34', ndt: '78.95', fdn: '30.00',
    ee: '7.00', ca: '0.84', p: '0.58', caP: '1.45',
  },
  {
    label: 'Dieta',
    msPct: '88.86',
    pb: '11.13', ndt: '51.69', fdn: '69.46',
    ee: '1.85', ca: '0.71', p: '0.52', caP: '1.37',
  },
  {
    label: 'Atendimento',
    msPct: '-----',
    pb: '-13.21', ndt: '-27.26', fdn: '39.46',
    ee: '-5.15', ca: '-0.13', p: '-0.06', caP: '-0.08',
  },
]

// Alinhados às colunas PB, NDT, FDN, EE, Ca, P, Ca/P (a coluna "MS (%) da Dieta" fica em branco)
const statusResultados = ['Déficit', 'Déficit', 'Excesso', 'Certo', 'Déficit', 'Déficit', 'Déficit']

function statusClass(label) {
  const normalized = label.toUpperCase()
  if (normalized === 'CERTO') return 'status-ok'
  if (normalized === 'EXCESSO') return 'status-excess'
  return 'status-deficit'
}

function handleCancelar() {
  console.log('Cancelar dados da dieta')
}

function handleVoltar() {
  console.log('Voltar para a etapa anterior')
}

function handleSalvar() {
  console.log('Salvar dados da dieta:', {
    misturaConcentrada: { ...misturaConcentrada },
  })
}
</script>

<style scoped>
.quadros-grid {
  display: grid;
  width: 100%;
  max-width: 100%;
  grid-template-columns: minmax(0, 4fr) minmax(0, 2fr);
  grid-auto-rows: 1fr;
  gap: var(--space-lg);
  align-items: stretch;
  min-height: 100%;
}
.top-bar-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.quadros-column {
  display: grid;
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: var(--space-lg);
  width: 100%;
  min-height: 0;
}

.quadros-column--left,
.quadros-column--right {
  min-height: 0;
}

.quadro {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.quadro-table {
  width: 100%;
  border-collapse: collapse;
}

.quadro-table th {
  text-align: left;
  padding: 12px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #8a7f5c;
  white-space: nowrap;
}

.quadro-table td {
  padding: 12px 14px;
  font-size: 13px;
}

.quadro-input {
  width: 100%;
  min-width: 80px;
}

.quadro-table th.num,
.quadro-table td.num {
  text-align: right;
}

.quadro-table tbody tr:nth-child(odd) {
  background: #f4f2e6;
}

.quadro-table tbody tr.quadro-total td {
  background: var(--primary-dark);
  color: var(--white);
  font-weight: 700;
}

  .quadro-table td,
  .quadro-table th {
    line-height: 1.5;
  }
.status-row td {
  font-size: 12px;
  font-weight: 700;
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

@media (max-width: 768px) {
  .quadros-grid {
    grid-template-columns: 1fr;
  }

  .quadro-table {
    display: block;
    overflow-x: auto;
  }
}
</style>
