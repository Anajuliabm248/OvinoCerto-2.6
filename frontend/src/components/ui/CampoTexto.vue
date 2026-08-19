<template>
  <input
    class="campo-texto"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :min="min"
    @input="$emit('update:modelValue', $event.target.value)"
  />
</template>

<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '' },
  type: { type: String, default: 'text' },
  min: { type: [String, Number], default: null },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.campo-texto {
  width: 100%;
  background: var(--white);
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  color: var(--text);
  font-size: 14px;
  box-sizing: border-box;
}
</style>
