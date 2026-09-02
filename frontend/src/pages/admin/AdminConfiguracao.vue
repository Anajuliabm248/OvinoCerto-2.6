<template>
  <div>
    <Header theme="light" />
    <div class="admin-page">
      <div class="admin-container">
        <!-- Conteúdo será adicionado aqui -->
      </div>
    </div>
  </div>
</template>

<script setup>
import Header from '@/components/layout/Header.vue'
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: var(--primary);
  padding-top: 65px;
}

.admin-container {
  width: 100%;
  max-width: 1200px;
  padding: 40px 24px;
}
</style>
