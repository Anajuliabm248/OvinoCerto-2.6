<template>
  <div class="graph-block">
    <div class="chart-block">
      <p class="chart-title">% de Ingrediente na MN</p>
      <div class="chart-row">
        <div class="pie" :style="{ background: ingredientPieGradient }"></div>
        <ul class="legend">
          <li v-for="slice in ingredientPie" :key="slice.label">
            <span class="dot" :style="{ background: slice.color }"></span>
            {{ slice.label }}
          </li>
        </ul>
      </div>
    </div>

    <div class="chart-block">
      <p class="chart-title">% do custo (R$) por ingrediente na MN</p>
      <div class="chart-row">
        <div class="pie" :style="{ background: costPieGradient }"></div>
        <ul class="legend">
          <li v-for="slice in costPie" :key="slice.label">
            <span class="dot" :style="{ background: slice.color }"></span>
            {{ slice.label }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  ingredientPie: { type: Array, required: true },
  costPie: { type: Array, required: true },
})

function buildGradient(slices) {
  let cumulative = 0
  const stops = slices.map((slice) => {
    const start = cumulative
    cumulative += slice.value
    return `${slice.color} ${start}% ${cumulative}%`
  })
  return `conic-gradient(${stops.join(', ')})`
}

const ingredientPieGradient = computed(() => buildGradient(props.ingredientPie))
const costPieGradient = computed(() => buildGradient(props.costPie))
</script>

<style scoped>
.graph-block { display:flex; flex-direction:column; gap:var(--space-sm) }
.chart-block { background:var(--white); border-radius:var(--radius-lg); padding:var(--space-sm); }
.chart-title { margin:0 0 8px; font-size:13px; font-weight:600; color:var(--text); }
.chart-row { display:flex; align-items:center; gap:var(--space-md); }
.pie { width:90px; height:90px; flex-shrink:0; border-radius:50%; }
.legend { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:6px; font-size:12px; color:#555; }
.dot { width:10px; height:10px; flex-shrink:0; border-radius:50%; }
</style>
