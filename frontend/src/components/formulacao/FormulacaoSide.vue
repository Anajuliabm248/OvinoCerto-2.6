<template>
  <div class="dashboard-side">
    <ul class="info-list">
      <li><span>Categoria:</span><strong>{{ animalInfo.categoria }}</strong></li>
      <li><span>Fase:</span><strong>{{ animalInfo.fase }}</strong></li>
      <li><span>Tipo de Parto:</span><strong>{{ animalInfo.tipoParto }}</strong></li>
      <li><span>PV (kg):</span><strong>{{ animalInfo.pv }}</strong></li>
      <li><span>GMD (kg):</span><strong>{{ animalInfo.gmd }}</strong></li>
      <li><span>PV (%):</span><strong>{{ animalInfo.pvPct }}</strong></li>
      <li><span>CMS (kg):</span><strong>{{ animalInfo.cms }}</strong></li>
    </ul>

    <div class="cost-summary">
      <p class="cost-value">R$/kg MN <strong>{{ custoPorKg }}</strong></p>
      <p class="ratio-value">Relação Ca/P <strong>{{ relacaoCaP }}</strong></p>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  animalInfo: { type: Object, required: true },
  custoPorKg: { type: [String, Number], required: true },
  relacaoCaP: { type: [String, Number], required: true },
})
</script>

<style scoped>
.dashboard-side {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-sm);
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: var(--space-sm);
  min-height: 0;
}
.chart-title { margin:0 0 8px; font-size:12px; font-weight:600; color:var(--text); }
.chart-row { display:flex; align-items:center; gap:var(--space-sm); }
.pie { width:88px; height:88px; flex-shrink:0; border-radius:50%; }
.legend { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:4px; font-size:13px; color:#555; }
.dot { width:9px; height:9px; flex-shrink:0; border-radius:50%; }
.info-list { list-style:none; margin:0; padding:6px 0 0; border-top:1px solid #e2ddd0; display:flex; flex-direction:column; gap:4px; font-size:14px; }
.info-list li { display:flex; justify-content:space-between; color:#555; line-height:1.4; }
.info-list strong { color:#2e7d32; font-weight:600; }
.cost-summary { display:flex; flex-direction:column; gap:4px; padding-top:6px; border-top:1px solid #e2ddd0; }
.cost-value, .ratio-value { display:flex; justify-content:space-between; margin:0; font-size:14px; color:#555; line-height:1.4; }
.cost-value strong { color:#2e7d32; }
.ratio-value strong { color:#c0392b; }
</style>