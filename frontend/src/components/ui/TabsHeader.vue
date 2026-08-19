<template>
  <div class="tabs-header">
    <div class="tabs-header__tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="['tabs-header__tab', { 'is-active': modelValue === tab.key }]"
        @click="$emit('update:modelValue', tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="$slots.actions" class="tabs-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  tabs: {
    type: Array,
    required: true,
    // [{ key: 'formulacao', label: 'Formulação da Dieta' }, ...]
  },
  modelValue: {
    type: String,
    required: true,
  },
  maxWidth: {
    type: String,
    default: '1800px',
  },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
/*
  This bar is meant to read as a literal extension of the card underneath it:
  same tab shape/radius the cards already used, fused with a -1px overlap.
  It's rendered inside PageCard's "page-stack" (via the top-tabs slot), which
  stretches it to the exact width of the card below — so no side padding
  here, or the first tab would drift out of alignment with the card's edge.
  A slot on the right holds page-level actions (e.g. "Ingredientes
  Selecionados") that live at the tab-strip level rather than inside the grid.
*/
.tabs-header {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  max-width: v-bind(maxWidth);

  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-sm);

  margin-left: 20px;
  margin-top: -40px;
  z-index: 5;
}

.tabs-header__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.tabs-header__tab {
  border: none;

  padding: 10px 16px;

  border-radius: 18px 18px 0 0;

  cursor: pointer;

  background: var(--primary-dark);

  color: var(--white);

  font-size: 13px;

  opacity: 1;

  transition: opacity .15s ease;
}

.tabs-header__tab:hover {
  opacity: .8;
}

.tabs-header__tab.is-active {
  background: var(--card-bg);
  opacity: 1;
}

.tabs-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;

  padding-bottom: 6px;
  padding-right: 4px;
}

@media (max-width: 768px) {
  .tabs-header__actions {
    width: 100%;

    padding-bottom: 0;
  }
}
</style>
