<template>
  <header class="header">
    <div class="header-inner">

      <!-- Logo -->
      <RouterLink to="/" class="logo-container">
        <img
          src="@/assets/logo_branca_2.png"
          alt="OvinoCerto"
          class="logo"
        >
      </RouterLink>

      <!-- Navegação -->
      <nav class="nav">

        <RouterLink to="/" class="nav-item">
          Home
        </RouterLink>

        <div
          class="dropdown"
          @mouseenter="dropdownOpen = true"
          @mouseleave="dropdownOpen = false"
        >
          <button class="nav-item dropdown-button">
            Propriedades

            <svg
              class="arrow"
              :class="{ open: dropdownOpen }"
              viewBox="0 0 24 24"
            >
              <path
                d="M6 9L12 15L18 9"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              />
            </svg>
          </button>

          <div
            v-if="dropdownOpen"
            class="dropdown-menu"
          >
            <RouterLink
              to="/propriedades"
              class="dropdown-item"
            >
              Ver Propriedades
            </RouterLink>

            <RouterLink
              to="/propriedades/nova"
              class="dropdown-item"
            >
              Nova Propriedade
            </RouterLink>
          </div>
        </div>

        <RouterLink
          to="/ingredientes"
          class="nav-item"
        >
          Ingredientes
        </RouterLink>

        <RouterLink
          to="/exigencias-nutricionais"
          class="nav-item"
        >
          Exigências Nutricionais
        </RouterLink>

        <RouterLink
          to="/formulacoes"
          class="nav-item"
        >
          Formulações
        </RouterLink>

      </nav>

      <!-- Ações -->
      <div class="actions">

        <button
          class="logout"
          @click="logout"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
          >
            <path
              d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>

        <RouterLink
          to="/conta"
          class="account"
        >
          Conta
        </RouterLink>

      </div>

    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const dropdownOpen = ref(false)

const router = useRouter()

function logout() {
  router.push('/login')
}
</script>

<style scoped>
.header {
  height: 65px;
  background: #5f7317;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 0 36px;

  position: relative;
}

.header-inner {
  width: 100%;

  display: flex;
  align-items: center;
  justify-content: center;

  position: relative;
}

/* ======================
   LOGO
====================== */

.logo-container {
  display: flex;
  align-items: center;

  position: absolute;
  left: 24px;
}

.logo {
  width: 40px;
  height: 40px;
  object-fit: contain;

  background-color: var(--primary-dark);
  border-radius: 50%;
}

/* ======================
   MENU
====================== */

.nav {
  display: flex;
  justify-content: center;
  align-items: center;

  gap: 36px;
}

.nav-item {
  color: white;

  font-size: 15px;
  font-weight: 500;
  letter-spacing: .04em;

  text-decoration: none;

  display: flex;
  align-items: center;

  gap: 6px;

  transition: opacity .2s;
}

.nav-item:hover {
  opacity: .8;
}

.dropdown {
  position: relative;
}

.dropdown-button {
  background: none;
  border: none;
  cursor: pointer;
}

.arrow {
  width: 12px;
  height: 12px;

  transition: .2s;
}

.arrow.open {
  transform: rotate(180deg);
}

/* ======================
   DROPDOWN
====================== */

.dropdown-menu {
  position: absolute;

  top: calc(100% + 10px);
  left: 0;

  min-width: 180px;

  background: white;

  border-radius: 8px;

  overflow: hidden;

  box-shadow:
    0 10px 30px rgba(0,0,0,.15);

  z-index: 100;
}

.dropdown-item {
  display: block;

  padding: 12px 16px;

  color: #333;

  font-size: 14px;

  text-decoration: none;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

/* ======================
   AÇÕES
====================== */

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;

  gap: 13px;

  position: absolute;
  right: 24px;
}

.logout {
  width: 40px;
  height: 40px;

  padding: 0;

  border: none;
  border-radius: 50%;

  background: #324507;

  color: white;

  display: flex;
  align-items: center;
  justify-content: center;

  cursor: pointer;

  box-sizing: border-box;
  flex-shrink: 0;
}

.logout svg {
  width: 20px;
  height: 20px;
}

.account {
  min-width: 117px;
  height: 36px;

  border-radius: 999px;

  background: #324507;

  color: white;

  font-size: 13px;
  font-weight: 500;

  text-decoration: none;

  display: flex;
  align-items: center;
  justify-content: center;
}

/* ======================
   MOBILE
====================== */

@media (max-width: 900px) {
  .nav {
    display: none;
  }

  .header-inner {
    grid-template-columns: 1fr auto;
  }
}
</style>