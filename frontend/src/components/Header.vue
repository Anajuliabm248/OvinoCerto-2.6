<template>
  <header class="header">
    <div class="header-inner">

      <!-- Logo -->
      <RouterLink to="/home" class="logo-container">
        <img
          src="@/assets/logo_branca_2.png"
          alt="OvinoCerto"
          class="logo"
        >
      </RouterLink>

      <!-- Navegação -->
      <nav class="nav">

        <RouterLink to="/home" class="nav-item">
          Home
        </RouterLink>

        <div
          class="dropdown"
          @mouseenter="dropdownOpen = true"
          @mouseleave="dropdownOpen = false"
          @mousemove="dropdownOpen = true"
        >
          <button class="nav-item dropdown-button" type="button">
            <RouterLink to="/propriedades" class="nav-item">
              Propriedades
            </RouterLink>

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
            @mouseenter="dropdownOpen = true"
            @mouseleave="dropdownOpen = false"
          >

            <RouterLink
              to="/propriedades/ovinos"
              class="dropdown-item"
              @click="dropdownOpen = false"
            >
              Ovinos / Lotes
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
          to="/formulacoes/ingredientes"
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
  padding-bottom: 12px;
  margin-bottom: -12px;
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
  top: 32px;
  left: 50%;
  transform: translateX(-50%);

  min-width: 168px;
  padding: 6px;

  background: #5f7317;

  border-radius: 14px;

  overflow: hidden;
  z-index: 100;
}

.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 12px;
  color: white;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: .04em;
  text-decoration: none;
  border-radius: 10px;
  transition: background-color .2s ease, color .2s ease;
}

.dropdown-item:hover {
  background: var(--primary-dark);
  color: white;
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