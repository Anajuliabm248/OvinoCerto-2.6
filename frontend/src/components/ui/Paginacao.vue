<template>
  <div class="paginacao">
    <button
      v-for="page in visiblePages"
      :key="page.key"
      class="page"
      :class="{ active: page.value === currentPage, dots: page.dots }"
      :disabled="page.dots"
      @click="!page.dots && $emit('update:currentPage', page.value)"
    >
      {{ page.dots ? '...' : page.value }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  totalPages: { type: Number, required: true },
  currentPage: { type: Number, default: 1 },
})

defineEmits(['update:currentPage'])

const visiblePages = computed(() => {
  const total = props.totalPages
  const current = props.currentPage
  const pages = []

  const pushPage = (value) => pages.push({ key: `p-${value}`, value })
  const pushDots = (key) => pages.push({ key, dots: true })

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pushPage(i)
    return pages
  }

  pushPage(1)

  if (current > 3) pushDots('dots-start')

  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  for (let i = start; i <= end; i++) pushPage(i)

  if (current < total - 2) pushDots('dots-end')

  pushPage(total)

  return pages
})
</script>

<style scoped>
.paginacao {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  background: rgba(255, 255, 255, .15);
  color: var(--white);
  font-size: 13px;
}

.page.active {
  background: var(--white);
  color: var(--primary-dark);
}

.page.dots {
  background: transparent;
  cursor: default;
  color: var(--white);
}
</style>
