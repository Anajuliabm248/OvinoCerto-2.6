<template>
  <div class="tabela">
    <div class="tabela-controls" v-if="searchable">
      <input type="text" v-model="search" placeholder="Pesquisar" class="tabela-search" />
      <div class="pagination-wrapper" v-if="totalPages > 1">
        <Paginacao :totalPages="totalPages" v-model:currentPage="currentPage" />
      </div>
    </div>

    <div class="tabela-scroll">
      <table>
        <colgroup>
          <col v-if="selectable" :style="{ width: widthFor(SELECT_COLUMN_WEIGHT) }" />
          <col v-for="col in columns" :key="col.key" :style="{ width: widthFor(col.weight ?? 1) }" />
        </colgroup>

        <thead>
          <tr>
            <th v-if="selectable" title="Seleção">Seleção</th>
            <th v-for="col in columns" :key="col.key" :title="col.label">{{ col.label }}</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="row in pagedRows" :key="row[rowKey]" :class="{ 'row-empty': row.__empty }">
            <td v-if="selectable">
              <button v-if="!row.__empty" type="button" class="select-dot" :class="{ active: isSelected(row) }" @click="toggleSelection(row)" />
            </td>

            <td v-for="col in columns" :key="col.key" :class="{ 'cell-wrap': col.wrap }" :title="row.__empty ? null : String(resolveCell(row, col))">
              <template v-if="row.__empty">&nbsp;</template>
              <template v-else>
                <template v-if="col.key === 'ms'">
                  <input v-model="row.ms" class="ms-input" />
                </template>
                <template v-else-if="col.key === 'acao'">
                  <button class="remove-btn" type="button" @click="$emit('remove', row[rowKey])">×</button>
                </template>
                <template v-else>
                  {{ resolveCell(row, col) }}
                </template>
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
import Paginacao from '@/components/ui/Paginacao.vue'

const PAGE_DEFAULT = 7
const SELECT_COLUMN_WEIGHT = 0.6

const props = defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  rowKey: { type: String, default: 'id' },
  selectable: { type: Boolean, default: false },
  selected: { type: Array, default: () => [] },
  searchable: { type: Boolean, default: true },
  currentPage: { type: Number, default: 1 },
  pageSize: { type: Number, default: PAGE_DEFAULT },
})

const emit = defineEmits(['update:selected', 'update:currentPage', 'update:totalPages', 'remove'])

const currentPage = computed({
  get: () => props.currentPage,
  set: (value) => emit('update:currentPage', value),
})

const search = ref('')

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
  return props.rows.filter((row) => props.columns.some((col) => String(row[col.key] ?? '').toLowerCase().includes(term)))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / props.pageSize)))

watch(totalPages, (value) => emit('update:totalPages', value), { immediate: true })

watch(search, () => { if (props.currentPage !== 1) emit('update:currentPage', 1) })

const pagedRows = computed(() => {
  const start = (props.currentPage - 1) * props.pageSize
  const slice = filteredRows.value.slice(start, start + props.pageSize)
  const missing = props.pageSize - slice.length
  const emptyRows = Array.from({ length: Math.max(0, missing) }, (_, i) => ({ [props.rowKey]: `empty-${start}-${i}`, __empty: true }))
  return [...slice, ...emptyRows]
})

function resolveCell(row, col) {
  if (row.__empty) return ''
  return col.format ? col.format(row) : row[col.key]
}

function isSelected(row) { return props.selected.includes(row[props.rowKey]) }

function toggleSelection(row) {
  const id = row[props.rowKey]
  const next = isSelected(row) ? props.selected.filter((item) => item !== id) : [...props.selected, id]
  emit('update:selected', next)
}
</script>

<style scoped>
.tabela { display:flex; flex-direction:column; gap:var(--space-sm); }
.tabela-controls { display:grid; grid-template-columns: minmax(220px, 1fr) auto; align-items:center; gap:12px; width:100%; }
.tabela-search { width:100%; min-width:220px; background:var(--white); border-radius:999px; padding:8px 16px; border:1px solid rgba(0,0,0,.1); }
.pagination-wrapper { display:flex; justify-content:flex-end; align-items:center; }
.tabela-scroll { overflow-x:auto; border-radius:var(--radius-lg); background:var(--white); }
table { width:100%; border-collapse:collapse; table-layout:fixed; white-space:nowrap }
thead { background:#e6e2d3 }
th { padding:10px 8px; text-align:center; line-height:18px; font-size:12px; font-weight:500; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap }
td { padding:2px 8px; text-align:center; font-size:13px; letter-spacing:-0.5px; line-height:18px; border-top:1px solid #d8d3c4; color:#666; height:44px; min-height:44px; max-height:44px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap }
.cell-wrap { white-space:pre-line }
.row-empty { background:#5f73171e }
.row-empty td { color:transparent }
tbody tr:not(.row-empty):hover { background:#f8f7f2 }
.select-dot { width:20px; height:20px; border-radius:50%; border:2px solid #bbb; background:var(--white); cursor:pointer; padding:0; transition:.15s ease }
.select-dot.active { background:var(--primary-dark); border-color:var(--primary-dark) }
.ms-input { width:44px; text-align:center; padding:3px 0; border-radius:999px; border:1px solid #bbb; font-size:12px }
.remove-btn { border:none; background:transparent; color:#c0392b; font-size:18px; line-height:1; cursor:pointer }
@media (max-width:768px) { .tabela-search { width:100% } }
</style>