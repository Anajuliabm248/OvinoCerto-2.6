<template>
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
        <tr v-for="row in summaryRows" :key="row.label">
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
          <td v-for="status in statusRow" :key="status.label" colspan="2" :class="['status-cell', statusClass(status.label)]">
            {{ status.label }}
          </td>
        </tr>
      </tbody>
    </table>

    <div class="ms-composition">
      <p><span>% da MS (volumoso)</span><strong>{{ msVolumoso }}%</strong></p>
      <p><span>% da MS (concentrado)</span><strong>{{ msConcentrado }}%</strong></p>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  summaryRows: { type: Array, required: true },
  statusRow: { type: Array, required: true },
  msVolumoso: { type: [String, Number], required: true },
  msConcentrado: { type: [String, Number], required: true },
})

function statusClass(label) {
  if (label === 'CERTO') return 'status-ok'
  if (label === 'EXCESSO') return 'status-excess'
  return 'status-deficit'
}
</script>

<style scoped>
.summary-wrapper { background:var(--white); border-radius:var(--radius-lg); margin-top:var(--space-md); padding:var(--space-md); }
.summary-table { width:100%; border-collapse:collapse; table-layout:fixed; font-size:11px; }
.summary-table th,
.summary-table td { padding:8px 6px; text-align:center; border-top:1px solid #e6e2d3; }
.summary-table th { background:#f5f3ef; font-weight:600; color:var(--text); }
.row-label { text-align:left; padding-left:10px; font-weight:600; color:#333; }
.status-row td { padding-top:12px; font-weight:700; }
.status-cell { border-top:none; }
.status-ok { color:#2e7d32; }
.status-deficit { color:#c0392b; }
.status-excess { color:#f39c12; }
.ms-composition { display:flex; justify-content:space-between; gap:var(--space-md); margin-top:14px; padding-top:14px; border-top:1px solid #e6e2d3; }
.ms-composition p { margin:0; font-size:12px; color:#555; display:flex; justify-content:space-between; width:100%; }
.ms-composition span { color:#777; }
.ms-composition strong { color:#1a73e8; }
@media (max-width:900px) { .ms-composition { flex-direction:column; align-items:flex-start; } }
</style>
