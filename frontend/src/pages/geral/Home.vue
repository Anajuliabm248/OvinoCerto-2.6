<template>
  <div class="dashboard">
    <Header theme="light" />

    <div class="home-page">
      <div class="cards-grid">
        <router-link
          v-for="item in menuItems"
          :key="item.label"
          :to="item.to"
          class="dashboard-card"
          :class="{ 'card-dark': item.dark }"
        >
          <span class="card-label">
            {{ item.label }}
          </span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import Header from '@/components/layout/Header.vue'

const menuItems = [
  { label: 'Propriedades', to: '/propriedades', dark: false },
  { label: 'Ovinos', to: '/propriedades/ovinos', dark: false },
  { label: 'Ingredientes', to: '/ingredientes', dark: false },
  { label: 'Exigências Nutricionais', to: '/exigencias-nutricionais', dark: false },
  { label: 'Formulações', to: '/formulacoes/ingredientes', dark: false },
  { label: 'Manual', to: '/frontpage', dark: true },
]
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 56px);

  display: flex;
  align-items: center;
  justify-content: center;

  padding: var(--space-xl) var(--space-lg);

  background: var(--background);
}

.cards-grid {
  display: grid;

  grid-template-columns: repeat(3, 260px);
  grid-template-rows: repeat(2, 180px);

  gap: var(--space-md);
}

.dashboard-card {
  background: var(--card-bg);

  border-radius: var(--radius-lg);

  display: flex;
  align-items: center;
  justify-content: center;

  text-decoration: none;

  box-shadow: var(--shadow-md);

  transition:
    transform .2s ease,
    box-shadow .2s ease,
    filter .2s ease;
}

.dashboard-card.card-dark {
  background: var(--primary-dark);
}

.dashboard-card:hover {
  transform: translateY(-3px);

  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.15);

  filter: brightness(1.06);
}

.card-label {
  color: var(--white);

  font-size: 15px;
  font-weight: 500;

  text-align: center;

  padding: 0 var(--space-sm);

  line-height: 1.4;
}

@media (max-width: 1024px) {
  .cards-grid {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: auto;

    width: 100%;
    max-width: 560px;
  }

  .dashboard-card {
    height: 160px;
  }
}

@media (max-width: 768px) {
  .cards-grid {
    grid-template-columns: 1fr 1fr;

    max-width: 100%;

    gap: var(--space-sm);
  }

  .dashboard-card {
    height: 130px;
  }

  .card-label {
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-card {
    height: 100px;
  }
}
</style>