<template>
  <select
    class="seletor"
    :value="modelValue"
    @change="$emit('update:modelValue', $event.target.value)"
  >
    <option value="" disabled :selected="!modelValue">{{ placeholder }}</option>
    <option
      v-for="opt in normalizedOptions"
      :key="opt.value"
      :value="opt.value"
    >
      {{ opt.label }}
    </option>
  </select>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] }, // string[] ou { value, label }[]
  placeholder: { type: String, default: 'Selecione' },
})

defineEmits(['update:modelValue'])

const normalizedOptions = computed(() =>
  props.options.map((opt) =>
    typeof opt === 'object' ? opt : { value: opt, label: opt }
  )
)
</script>

<style scoped>
.seletor {
  width: 100%;
  background: var(--white);
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  color: var(--text);
  font-size: 14px;
  box-sizing: border-box;
  appearance: none;
  cursor: pointer;
}
</style>
