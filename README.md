# 🐑 OvinoCerto 2.6
> Sistema automatizado de formulação de rações para ovinos da UFSM-Politécnico.

## 📖 Sobre o Projeto
O **OvinoCerto** é uma aplicação web voltada para a otimização e automatização do cálculo de dietas e formulação de rações para ovinos. Baseado na tabela NRC (2007) e nas tabelas do Valadares Filho (2010), a ferramenta permite o cadastro de propriedades, lotes e ingredientes personalizados, além de sugerir e balancear formulações nutricionais de forma inteligente.

## 🚀 Funcionalidades Principais
- **Autenticação:** Criação, edição e acesso a contas de usuário com JWT.
- **Gestão de Propriedades e Lotes:** Gerencie suas propriedades rurais e os rebanhos de ovinos.
- **Ingredientes:** Utilize um vasto banco de dados referenciado ou crie seus próprios ingredientes customizados.
- **Exigências Nutricionais:** Acesso dinâmico à tabela NRC (2007) com buscas e filtros avançados.
- **Formulação Inteligente:**
  - Adição de ingredientes com proporções calculadas pelo sistema.
  - Ajuste manual (travamento) da porcentagem de ingredientes.
  - Sugestões inteligentes de substituição baseadas em custo, proteína ou fibra.
  - Edição dos nutrientes da exigência utilizando operadores lógicos para guiar o balanceamento (`<=`, `>=`, `=`, `ENTRE`).
  - Filtros avançados para otimização de custo da ração.

---

## 🌐 Base URL
```
/api
```

---

## 📚 Documentação da API (Endpoints)

### 1. Autenticação (`/api/auth`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login/` | Valida credenciais e devolve tokens JWT. |
| `POST` | `/api/auth/register/` | Cria um novo usuário e devolve os tokens JWT. |
| `POST` | `/api/auth/refresh/` | Atualiza o token de acesso JWT utilizando um token de refresh. |

### 2. Usuários (`/api/usuarios`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/usuarios/me/` | Retorna o perfil do usuário autenticado. |
| `GET`  | `/api/usuarios/` | Lista os usuários do sistema (suporta paginação). |
| `POST` | `/api/usuarios/` | Cria um novo usuário. |
| `GET`  | `/api/usuarios/{id}/` | Retorna os detalhes de um usuário específico. |
| `PUT` / `PATCH` | `/api/usuarios/{id}/` | Atualiza integralmente ou parcialmente os dados de um usuário. |
| `DELETE` | `/api/usuarios/{id}/` | Remove um usuário do sistema. |
| `PATCH` | `/api/usuarios/{id}/atualizar_perfil/` | Atualiza informações específicas do perfil do usuário. |

### 3. Propriedades (`/api/propriedades`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/propriedades/` | Lista as propriedades do usuário logado (suporta busca por nome, UF, etc). |
| `POST` | `/api/propriedades/` | Cria uma nova propriedade vinculada ao usuário logado. |
| `GET`  | `/api/propriedades/{id}/` | Visualiza os detalhes de uma propriedade específica. |
| `PUT` / `PATCH` | `/api/propriedades/{id}/` | Atualiza as informações de uma propriedade existente (apenas as próprias). |
| `DELETE` | `/api/propriedades/{id}/` | Exclui uma propriedade (apenas as próprias). |

### 4. Lotes (Ovinos) (`/api/lotes`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/lotes/` | Lista os lotes de animais do usuário logado (suporta busca e filtros). |
| `POST` | `/api/lotes/` | Cria um novo lote associado a uma propriedade do usuário. |
| `GET`  | `/api/lotes/{id}/` | Detalhes completos de um lote específico. |
| `PUT` / `PATCH` | `/api/lotes/{id}/` | Edita as informações de um lote existente. |
| `DELETE` | `/api/lotes/{id}/` | Remove um lote do sistema. |
| `GET`  | `/api/lotes/{id}/exigencia/` | Sugere exigências NRC recomendadas para as características daquele lote. |

### 5. Ingredientes (`/api/ingredientes`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/ingredientes/` | Lista todos os ingredientes (Valadares e Customizados). Suporta diversos filtros. |
| `POST` | `/api/ingredientes/` | Cria um novo ingrediente customizado. |
| `GET`  | `/api/ingredientes/meus/` | Atalho: Lista exclusivamente os ingredientes criados pelo usuário logado. |
| `GET`  | `/api/ingredientes/tipos/` | Retorna as opções disponíveis de classificação (volumoso, concentrado, etc) e tipos. |
| `GET`  | `/api/ingredientes/{id}/` | Visualiza os detalhes nutricionais de um ingrediente específico. |
| `PUT` / `PATCH` | `/api/ingredientes/{id}/` | Atualiza um ingrediente (ação permitida apenas para ingredientes customizados do usuário). |
| `DELETE` | `/api/ingredientes/{id}/` | Exclui um ingrediente customizado. |

### 6. Exigências Nutricionais (`/api/exigencias`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/exigencias/` | Lista as exigências nutricionais presentes na Tabela NRC (2007). |
| `POST` | `/api/exigencias/` | Cria uma nova linha de exigência nutricional (Restrito para Admins). |
| `GET`  | `/api/exigencias/categorias/` | Lista os valores únicos de categorias registradas na tabela. |
| `GET`  | `/api/exigencias/lookup/` | Busca a linha NRC mais adequada baseada nos parâmetros do rebanho (fase, peso, gmd). |
| `GET`  | `/api/exigencias/{id}/` | Retorna os detalhes exatos de uma exigência específica. |
| `PUT` / `PATCH` | `/api/exigencias/{id}/` | Edita dados de uma exigência (Restrito para Admins). |
| `DELETE` | `/api/exigencias/{id}/` | Remove uma exigência da base (Restrito para Admins). |

### 7. Formulação (`/api/formulacoes`)
#### Fluxo Principal & Criação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/formulacoes/` | Lista o histórico de formulações geradas pelo usuário. |
| `POST` | `/api/formulacoes/` | Atalho rápido para iniciar a criação de uma formulação. |
| `POST` | `/api/formulacoes/iniciar/` | **Etapa 1:** Inicia uma nova formulação vinculando um lote, uma tabela NRC e um título. |
| `POST` | `/api/formulacoes/{id}/gerar/` | **Etapa 2:** Calcula a distribuição inicial e adiciona os ingredientes à ração. |
| `GET`  | `/api/formulacoes/{id}/` | Retorna o panorama completo de uma formulação. |
| `PUT` / `PATCH` | `/api/formulacoes/{id}/` | Atualiza os dados bases e observações da formulação. |
| `DELETE` | `/api/formulacoes/{id}/` | Exclui completamente a formulação do banco de dados. |

#### Gestão de Ingredientes na Dieta
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/formulacoes/ingredientes-disponiveis/` | Exibe um catálogo de ingredientes ordenados para facilitar a adição (volumoso → concentrado). |
| `POST` | `/api/formulacoes/{id}/ingredientes/` | Insere um novo ingrediente na dieta atual. |
| `DELETE` | `/api/formulacoes/{id}/ingredientes/{ing_form_id}/` | Remove um ingrediente específico da formulação. |
| `PATCH` | `/api/formulacoes/{id}/ingredientes/{ing_form_id}/ajustar/` | Ajusta a porcentagem manualmente, travando o ingrediente e disparando recálculo automático. |
| `POST` | `/api/formulacoes/{id}/ingredientes/{ing_form_id}/destravar/` | Remove a trava de um ingrediente, permitindo sua redistribuição automática na próxima alteração. |
| `GET`  | `/api/formulacoes/{id}/sugestoes/` | Analisa a dieta e gera sugestões inteligentes de adição ou substituição de ingredientes. |

#### Metas (Exigências) e Recálculo
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/formulacoes/exigencias-nrc/` | Sugere diferentes exigências da tabela NRC para o lote informado. |
| `GET`  | `/api/formulacoes/{id}/exigencia/` | Visualiza as metas nutricionais (exigências) atualmente aplicadas à dieta. |
| `PATCH` | `/api/formulacoes/{id}/exigencia/{nutriente}/` | Personaliza a meta de um nutriente na dieta usando operadores lógicos (`>`, `<`, `=`, `ENTRE`). |
| `POST` | `/api/formulacoes/{id}/recalcular/` | Aciona o recálculo do balanceamento da ração após alterações na configuração. |
| `GET`  | `/api/formulacoes/{id}/resultado/` | Traz a análise e o resultado final da eficácia da dieta montada. |

#### Histórico, Versões e Auditoria (Snapshots)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET`  | `/api/formulacoes/{id}/eventos/` | Log de auditoria rastreando todas as modificações feitas na dieta. |
| `GET`  | `/api/formulacoes/{id}/versoes/` | Lista os 'snapshots' (versões congeladas no tempo) desta formulação. |
| `GET`  | `/api/formulacoes/{id}/versoes/{versao_num}/` | Visualiza os ingredientes e dados de uma versão/snapshot específica. |
| `POST` | `/api/formulacoes/{id}/versoes/{versao_num}/restaurar/` | Restaura a formulação atual revertendo os dados para uma versão anterior. |
