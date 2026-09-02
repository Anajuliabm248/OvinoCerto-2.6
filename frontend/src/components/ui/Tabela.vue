<template>
  <div class="tabela">
    <div class="tabela-controls" v-if="searchable">
      <input
        type="text"
        v-model="search"
        placeholder="Pesquisar"
        class="tabela-search"
      />
    </div>

    <div class="tabela-scroll">
      <table>
        <colgroup>
          <col v-if="selectable" :style="{ width: widthFor(SELECT_COLUMN_WEIGHT) }" />
          <col
            v-for="col in columns"
            :key="col.key"
            :style="{ width: widthFor(col.weight ?? 1) }"
          />
        </colgroup>

        <thead>
          <tr>
            <th v-if="selectable" title="Seleção">Seleção</th>
            <th v-for="col in columns" :key="col.key" :title="col.label">{{ col.label }}</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="row in pagedRows"
            :key="row[rowKey]"
            :class="{ 'row-empty': row.__empty }"
          >
            <td v-if="selectable">
              <button
                v-if="!row.__empty"
                type="button"
                class="select-dot"
                :class="{ active: isSelected(row) }"
                @click="toggleSelection(row)"
              />
            </td>
            <td
              v-for="col in columns"
              :key="col.key"
              :class="{ 'cell-wrap': col.wrap }"
              :title="row.__empty ? null : String(resolveCell(row, col))"
              @click="handleCellClick($event, row, col)"
            >
              <span v-if="col.render && !row.__empty" v-html="col.render(row)" />
              <template v-else>
                {{ resolveCell(row, col) }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// A tabela sempre mostra exatamente 10 linhas: completa com linhas em
// branco quando há menos dados, e joga o restante para as próximas
// páginas quando há mais — em "dezenas" (1-10, 11-20, 21-30...).
const PAGE_SIZE = 10

// Peso "padrão" da coluna de seleção (bem menor que 1, já que ela só
// tem uma bolinha). Pode ser ajustado se precisar de mais/menos espaço.
const SELECT_COLUMN_WEIGHT = 0.6

const props = defineProps({
  // [{ key, label, wrap?: boolean, weight?: number, format?: (row) => string }]
  // "weight" define a largura relativa da coluna (padrão: 1).
  // Ex.: weight 2 fica duas vezes mais larga que uma coluna com weight 1.
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  rowKey: { type: String, default: 'id' },
  selectable: { type: Boolean, default: true },
  selected: { type: Array, default: () => [] },
  searchable: { type: Boolean, default: true },
  currentPage: { type: Number, default: 1 },
})

const emit = defineEmits(['update:selected', 'update:currentPage', 'update:totalPages', 'cell-click'])

const search = ref('')

// Soma de todos os pesos (colunas + coluna de seleção, se houver).
// Cada coluna recebe (peso / somaTotal) * 100% da largura da tabela —
// então elas sempre se ajustam automaticamente ao espaço máximo disponível.
const totalWeight = computed(() => {
  const base = props.selectable ? SELECT_COLUMN_WEIGHT : 0
  return props.columns.reduce((sum, col) => sum + (col.weight ?? 1), base)
})

function widthFor(weight) {
  return `${(weight / totalWeight.value) * 100}%`
}

const filteredRows = computed(() => {
  if (!props.searchable || !search.value) return props.rows

  const term = search.value.toLowerCase()

  return props.rows.filter((row) =>
    props.columns.some((col) =>
      String(row[col.key] ?? '').toLowerCase().includes(term)
    )
  )
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredRows.value.length / PAGE_SIZE))
)

// Informa o componente pai (que renderiza a <Paginacao /> no canto
// inferior direito do grid) quantas páginas existem.
watch(totalPages, (value) => emit('update:totalPages', value), { immediate: true })

// Buscar sempre volta pra primeira página, senão a dezena visível
// poderia não bater com os resultados filtrados.
watch(search, () => {
  if (props.currentPage !== 1) emit('update:currentPage', 1)
})

const pagedRows = computed(() => {
  const start = (props.currentPage - 1) * PAGE_SIZE
  const slice = filteredRows.value.slice(start, start + PAGE_SIZE)
  const missing = PAGE_SIZE - slice.length

  const emptyRows = Array.from({ length: Math.max(0, missing) }, (_, i) => ({
    [props.rowKey]: `empty-${start}-${i}`,
    __empty: true,
  }))

  return [...slice, ...emptyRows]
})

function formatNumericCell(value) {
  if (value === null || value === undefined || value === '') return value

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value.toFixed(2) : value
  }

  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return value
    if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
      const numeric = Number(trimmed)
      return Number.isFinite(numeric) ? numeric.toFixed(2) : value
    }
  }

  return value
}

function handleCellClick(event, row, col) {
  if (row.__empty || !col.render) return

  const target = event.target.closest('[data-action]')
  if (!target) return

  emit('cell-click', {
    row,
    col,
    action: target.dataset.action,
    id: target.dataset.id,
    event: target,
  })
}

function resolveCell(row, col) {
  if (row.__empty) return ''

  if (col.format) return col.format(row)

  const value = row[col.key]
  if (col.key === 'id' || col.key === 'indice') return value

  return formatNumericCell(value)
}

function isSelected(row) {
  return props.selected.includes(row[props.rowKey])
}

function toggleSelection(row) {
  const id = row[props.rowKey]
  const next = isSelected(row)
    ? props.selected.filter((item) => item !== id)
    : [...props.selected, id]

  emit('update:selected', next)
}
</script>

<style scoped>
.tabela {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.tabela-controls {
  display: flex;
  justify-content: flex-end;
}

.tabela-search {
  width: 220px;
  background: var(--white);
  border-radius: 999px;
  padding: 4px 16px;
}

/* Responsivo ao nº de colunas: cresce e rola horizontalmente sozinho */
.tabela-scroll {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  background: var(--white);
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  white-space: nowrap;
}

thead {
  background: #e6e2d3;
}

th {
  padding: 12px 10px;
  text-align: center;
  line-height: 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

td {
  padding: 2px 10px;
  text-align: center;
  font-size: 14px;
  letter-spacing: -0.7px;
  line-height: 20px;
  border-top: 1px solid #d8d3c4;
  color: #666;
  height: 50px;
  min-height: 50px;
  max-height: 50px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-wrap {
  white-space: pre-line;
}

.row-empty {
  background: #5f73171e;
}

.row-empty td {
  color: transparent;
  
}

tbody tr:not(.row-empty):hover {
  background: #f8f7f2;
}

.select-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #bbb;
  background: var(--white);
  cursor: pointer;
  padding: 0;
  transition: .15s ease;
}

.select-dot.active {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
}

@media (max-width: 768px) {
  .tabela-search {
    width: 100%;
  }
}
</style>
