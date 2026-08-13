# OvinoCerto 2.6

Sistema web da UFSM-Politécnico para organizar propriedades e lotes, consultar
referências nutricionais e formular dietas para ovinos com controle de exigências, custo e
viabilidade econômica.

## Como o sistema está organizado

O repositório possui duas aplicações:

- `backend/`: API Django REST Framework, autenticação JWT e motores de cálculo.
- `frontend/`: interface Vue 3 criada com Vite, Pinia, Vue Router e Axios.

Os apps do backend têm responsabilidades bem separadas:

| App | Responsabilidade |
| --- | --- |
| `accounts` | Conta Django, perfil de negócio, cadastro e login. |
| `propriedade` | Propriedades pertencentes ao usuário autenticado. |
| `lote` | Dados zootécnicos e agrupamento dos animais. |
| `exigencia_nrc` | Catálogo de referências nutricionais NRC. |
| `ingrediente` | Catálogo Valadares, ingredientes customizados e preços pessoais. |
| `formulacao` | Formulação, recálculo, alertas, custos, versões e viabilidade. |

Dentro de `formulacao`, `domain/` e `engines/` não acessam o banco. Os
`repositories/` traduzem models para vetores e persistem resultados. Os
`services/` orquestram cada caso de uso e as transações. A pasta `api/` cuida
somente do contrato HTTP.

## Regras importantes da formulação

- `ms_porcent` é salvo no banco em percentual de `0` a `100`.
- Os motores trabalham com frações de `0` a `1`.
- A soma das participações deve terminar em `1.0`, isto é, 100% da MS.
- O percentual de volumoso informado é um alvo estrutural rígido.
- Limites máximos por ingrediente são rígidos na geração e na redistribuição.
- Participações `MANUAL_TRAVADA` não são alteradas automaticamente.
- Exigências nutricionais são atendidas por melhor esforço. Se a seleção de
  ingredientes não permitir atendê-las, a estrutura da dieta continua válida e
  os desvios aparecem como alertas.
- O preço regional pertence ao usuário. Um preço local da receita não altera o
  catálogo nem outras formulações.
- Parâmetros de viabilidade são uma cópia de simulação: editá-los não altera o
  lote, a exigência NRC ou a formulação nutricional.

## Requisitos

- Python 3.11 ou mais recente.
- Node.js 20 ou mais recente.
- SQLite para desenvolvimento ou PostgreSQL para ambientes compartilhados.

## Instalação

Crie e ative um ambiente virtual na raiz do projeto. No PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copie os valores de `.env.example` para um arquivo `.env` na raiz e ajuste-os.
Em desenvolvimento, `USE_SQLITE=true` dispensa a instalação do PostgreSQL.
Nunca use o segredo de exemplo em produção.

Prepare o banco e, quando necessário, carregue os catálogos:

```powershell
python backend\manage.py migrate
python backend\manage.py seed_ingredientes
python backend\manage.py seed_exigencias
python backend\manage.py createsuperuser
```

Inicie a API:

```powershell
python backend\manage.py runserver
```

Em outro terminal, prepare e inicie a interface:

```powershell
cd frontend
npm install
npm run dev
```

A interface abre normalmente em `http://localhost:5173` e a API em
`http://localhost:8000/api`. Para usar outro endereço, crie
`frontend/.env.local` com `VITE_API_URL=https://servidor/api`.


## API e documentação interativa

- Swagger: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- Schema OpenAPI: `http://localhost:8000/api/schema/`

Fluxo principal:

| Método | Endpoint | O que faz |
| --- | --- | --- |
| `POST` | `/api/auth/register/` | Cria conta e perfil e retorna JWT. |
| `POST` | `/api/auth/login/` | Autentica por e-mail e senha. |
| `GET/POST` | `/api/propriedades/` | Lista ou cria propriedades próprias. |
| `GET/POST` | `/api/lotes/` | Lista ou cria lotes próprios. |
| `GET` | `/api/lotes/{id}/exigencia/` | Sugere referências NRC para escolha. |
| `GET/POST` | `/api/ingredientes/` | Lista ou cria ingredientes customizados. |
| `PATCH` | `/api/ingredientes/{id}/preco/` | Define o preço regional do usuário. |
| `POST` | `/api/formulacoes/iniciar/` | Cria formulação e copia a exigência NRC. |
| `POST` | `/api/formulacoes/{id}/gerar/` | Gera a distribuição inicial. |
| `PATCH` | `/api/formulacoes/{id}/ingredientes/{linha}/ajustar/` | Trava uma participação e redistribui o restante. |
| `POST` | `/api/formulacoes/{id}/ingredientes/{linha}/destravar/` | Libera e redistribui a participação. |
| `POST` | `/api/formulacoes/{id}/recalcular/` | Refaz nutrientes, custos, alertas e versão. |
| `GET` | `/api/formulacoes/{id}/resultado/` | Mostra adequação e soma da dieta. |
| `GET` | `/api/formulacoes/{id}/custos/` | Mostra os custos atuais. |
| `PATCH` | `/api/formulacoes/{id}/viabilidade/parametros/` | Atualiza o cenário econômico. |
| `GET` | `/api/formulacoes/{id}/viabilidade/` | Calcula consumo, investimento e resultado. |
| `GET` | `/api/formulacoes/{id}/versoes/` | Lista versões imutáveis da formulação. |
| `GET` | `/api/formulacoes/{id}/eventos/` | Consulta a trilha de auditoria. |


