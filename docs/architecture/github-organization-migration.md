# Подготовка GitHub Organization и перенос репозитория

Дата: 2026-05-18
Статус: операционный чеклист, transfer выполнен

Этот документ фиксирует подготовку GitHub organization
`industrial-data-platform`, перенос первого репозитория и проверку доступа
Sergey. Это не архитектурное решение продукта; это операционный чеклист для
переезда текущего проекта в organization, где будут issues, project planning и
CI/CD workflows.

Итоговый repository после transfer/rename:

```text
industrial-data-platform/industrial-data-platform
```

Canonical remote:

```bash
git@github.com:industrial-data-platform/industrial-data-platform.git
```

## 1. Подготовка organization до переноса

Создать GitHub organization:

- slug: `industrial-data-platform`
- display name: `Industrial Data Platform`
- visibility/profile: по умолчанию private/internal для рабочих материалов

Минимальная настройка владельцев и безопасности:

- пригласить `SergeyDubovitsky` в organization с ролью `Owner`;
- включить или потребовать 2FA для owners и будущих members;
- создать team `maintainers`, если кроме owners появятся участники с доступом к
  репозиторию;
- для `maintainers` использовать `Maintain` как default-доступ к repo; `Admin`
  давать только тем, кто реально управляет repository settings, secrets,
  branch protection и transfer.

Перед переносом включить на уровне organization/repository policy:

- Issues;
- Projects;
- Actions;
- Pages.

## 2. Перенос первого репозитория

Финальный transfer/rename target:

```text
previous personal repo -> industrial-data-platform/industrial-data-platform
```

Исторически первый перенос планировался без rename, но после подготовки
organization repository переименован в `industrial-data-platform`. Локальные
remotes теперь должны использовать финальный repository URL.

После transfer проверить repository settings:

- default branch остается `main`;
- Issues включены;
- Projects включены;
- Actions включены;
- Pages source установлен в `GitHub Actions`;
- Workflow permissions установлены в `Read and write permissions`.

Почему важны workflow permissions: `.github/workflows/python-ci.yml` использует
`GITHUB_TOKEN` для force-push coverage badge в branch `badges`, поэтому
repository-level Actions permissions должны разрешать запись в contents.

Существующие workflows, которые должны остаться после transfer:

- `.github/workflows/python-ci.yml`
- `.github/workflows/deploy-likec4-pages.yml`

После переноса локальный remote обновляется вручную:

```bash
git remote set-url origin git@github.com:industrial-data-platform/industrial-data-platform.git
git fetch origin
```

Проверка удаленного доступа:

```bash
git ls-remote git@github.com:industrial-data-platform/industrial-data-platform.git
```

## 3. Organization project

Создать organization project:

- name: `Industrial Data Platform Roadmap`
- visibility: private
- owner: `industrial-data-platform`
- linked repository: `industrial-data-platform/industrial-data-platform`

Рекомендуемые views:

- `Backlog`
- `Current`
- `Done`

Рекомендуемые fields:

- `Status`
- `Priority`
- `Area`
- `Milestone`

Рекомендуемые `Area` values:

- `Config Registry`
- `Telemetry Store`
- `Web Monitoring`
- `Catalog`
- `CI/Infra`
- `Docs`

Первичная проверка project:

- issue из `industrial-data-platform/industrial-data-platform` можно добавить
  в project;
- PR из `industrial-data-platform/industrial-data-platform` можно добавить
  в project;
- Sergey видит project и может менять поля.

## 4. Мини-инструкция для Sergey

После приглашения:

1. Принять invitation в organization `industrial-data-platform`.
2. Включить 2FA, если GitHub попросит.
3. Проверить, что роль в organization: `Owner`.
4. Открыть repo
   `https://github.com/industrial-data-platform/industrial-data-platform`.
5. Проверить доступ к:
   - repository settings;
   - Actions;
   - Projects;
   - Issues.
6. В локальном checkout обновить remote:

```bash
git remote set-url origin git@github.com:industrial-data-platform/industrial-data-platform.git
git fetch origin
git status --short --branch
```

7. Проверить, что доступны branches и можно создать test branch при
   необходимости.

## 5. Чеклист после переноса

После transfer и настройки organization:

- `https://github.com/industrial-data-platform` открывается;
- `SergeyDubovitsky` отображается среди owners;
- `https://github.com/industrial-data-platform/industrial-data-platform` открывается;
- `git ls-remote git@github.com:industrial-data-platform/industrial-data-platform.git`
  работает;
- `Python CI` запускается на PR или push;
- `Deploy LikeC4 Pages` запускается вручную через `workflow_dispatch`;
- GitHub Pages environment `github-pages` создается workflow-ом;
- branch `badges` создается или обновляется после первого push на `main`;
- organization project видит issues и PR из repo.

## 6. Предположения

- Organization slug уже выбран: `industrial-data-platform`.
- Первый repo перенесен в organization и переименован в
  `industrial-data-platform`.
- GitHub login Sergey: `SergeyDubovitsky`.
- GitHub organization и transfer выполнены владельцем через GitHub UI.
- Secrets для текущих workflows не требуются; используется `GITHUB_TOKEN`.

## Ссылки

- GitHub Docs: transfer a repository
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>
- GitHub Docs: repository roles for an organization
  <https://docs.github.com/en/organizations/managing-access-to-your-organizations-repositories/repository-roles-for-an-organization>
- GitHub Docs: require 2FA in an organization
  <https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-two-factor-authentication-for-your-organization/requiring-two-factor-authentication-in-your-organization>
- GitHub Docs: workflow permissions for `GITHUB_TOKEN`
  <https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication>
- GitHub Docs: GitHub Pages with custom workflows
  <https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages>
- GitHub Docs: GitHub Projects
  <https://docs.github.com/en/issues/planning-and-tracking-with-projects>
