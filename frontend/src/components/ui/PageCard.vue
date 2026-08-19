<template>
  <div class="page-shell">
    <div class="page-header">
      <Header />
    </div>

    <main class="page-content">
      <div class="page-stack" :class="`size-${size}`">

        <slot name="top-tabs" />

        <div class="page-card">

          <div class="page-top-bar" v-if="title || $slots['top-bar-extra']">
            <div v-if="title">
              <h3>{{ title }}</h3>
              <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
            </div>

            <div class="page-top-bar-extra">
              <slot name="top-bar-extra" />
            </div>
          </div>

          <div class="page-card-body">
            <slot />
          </div>

          <div class="page-bottom-bar" v-if="$slots.actions || $slots.pagination">
            <div class="page-bottom-left">
              <slot name="actions" />
            </div>
            <div class="page-bottom-right">
              <slot name="pagination" />
            </div>
          </div>

        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import Header from '@/components/layout/Header.vue'

defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  // 'default' -> páginas de listagem/tabela (80% x 80% da tela)
  // 'form'    -> páginas de cadastro/"adicionar" (60% x 50% da tela, centralizado)
  size: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'form'].includes(value),
  },
})
</script>

<style scoped>
/*
  O Header fica em overlay (position: fixed), por CIMA da página, e não
  no fluxo normal empurrando o conteúdo para baixo. Assim o page-content
  continua ocupando exatamente 100vh — sem "100vh + altura do header",
  que era o que causava o scroll (vertical, e por consequência lateral
  por causa da barra de rolagem).
*/
.page-shell {
  position: relative;
  min-height: 100vh;
  background: var(--background);
  overflow-x: hidden;
}

.page-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 20;
}

.page-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-lg);
  box-sizing: border-box;
}

/*
  page-stack agrupa qualquer coisa "acima do card" (por ex. um <TabsHeader />
  passado via slot top-tabs) junto com o próprio card. É este grupo — e não
  só o card — que recebe o margin-top que afasta tudo do Header fixo. Assim
  o conteúdo do slot fica colado ao card (sem gap extra), e o conjunto todo
  ainda respeita a folga necessária para não ficar atrás do Header.
*/
.page-stack {
  display: flex;
  flex-direction: column;

  position: relative;
  margin-top: 10vh;

  box-sizing: border-box;
}

.page-stack.size-default {
  width: 80vw;
  height: 80vh;
}

.page-stack.size-form {
  width: 55vw;
  height: 45vh;
}

.page-card {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  background: var(--card-bg);
  border-radius: 24px;
  padding: var(--space-lg);
  box-shadow: var(--shadow-md);
  box-sizing: border-box;
}

/* When a TabsHeader is present, add top padding so the absolute header
   doesn't visually overlap the card content (table). This keeps the
   same gap across the entire card including the table. */
.page-stack > .tabs-header + .page-card {
  padding-top: var(--space-lg);
}

.page-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-md);
  flex-shrink: 0;
}

.page-top-bar h3 {
  margin: 0;
  color: var(--white);
  font-weight: 500;
}

.page-subtitle {
  margin: 0;
  margin-top: -4px;
  color: rgba(255, 255, 255, .75);
  font-size: 14px;
}

/* Conteúdo cresce para preencher o card e rola internamente se passar do tamanho fixo */
.page-card-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.page-bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-md);
  flex-shrink: 0;
}

.page-bottom-right:empty,
.page-bottom-left:empty {
  display: none;
}

@media (max-width: 1024px) {
  .page-stack.size-default {
    width: 90vw;
    height: 85vh;
  }

  .page-stack.size-form {
    width: 80vw;
    height: auto;
    max-height: 85vh;
  }
}

@media (max-width: 768px) {
  .page-content {
    padding: var(--space-md);
  }

  .page-card {
    padding: var(--space-md);
  }

  .page-stack.size-default {
    width: 100%;
    height: 90vh;
  }

  .page-stack.size-form {
    width: 100%;
    height: auto;
    max-height: 90vh;
  }

  .page-bottom-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }
}
</style>
