<template>
  <RouterLink
    v-if="to"
    :to="to"
    class="botao"
    :class="[variant, { 'botao-block': block }]"
  >
    {{ label }}
  </RouterLink>

  <button
    v-else
    :type="type"
    class="botao"
    :class="[variant, { 'botao-block': block }]"
    @click="$emit('click', $event)"
  >
    {{ label }}
  </button>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  to: { type: [String, Object], default: null },
  type: { type: String, default: 'button' },
  variant: { type: String, default: 'primary' }, // primary | outline | ghost
  block: { type: Boolean, default: false },
})

defineEmits(['click'])
</script>

<style scoped>
.botao {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  padding: 12px 24px;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  transition: filter .2s ease;
  box-sizing: border-box;
}

.botao:hover {
  filter: brightness(1.1);
}

.botao.primary {
  background: var(--primary-dark);
  color: var(--white);
}

.botao.outline {
  background: transparent;
  color: var(--primary-dark);
  border: 2px solid var(--primary-dark);
}

.botao.ghost {
  background: rgba(255, 255, 255, .15);
  color: var(--white);
}

.botao-block {
  width: 100%;
}
</style>
