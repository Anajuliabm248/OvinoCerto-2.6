<template>
  <section class="quadro">
    <p class="quadro-title">{{ titulo }}</p>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  titulo: { type: String, required: true },
})
</script>

<style scoped>
.quadro {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
}

.quadro-title {
  margin: 0 0 var(--space-sm);
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}
</style>
