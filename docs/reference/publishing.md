# GitHub Pages Publishing

The published documentation is built directly from `ThothAI`.

## Repository Files

This setup relies on:

- `mkdocs.yml`
- `requirements-docs.txt`
- `.github/workflows/docs-pages.yml`

## Workflow Behavior

The workflow:

1. checks out the repository
2. installs the MkDocs dependencies
3. runs `mkdocs build --strict`
4. uploads the generated `site/` directory
5. deploys it with `actions/deploy-pages`

Only the GitHub `origin` remote is in scope for this publishing flow.
The `uni` remote is intentionally ignored.

## One-Time Maintainer Steps

In GitHub repository settings:

1. open `Settings -> Pages`
2. set the source to `GitHub Actions`
3. allow the first deployment to publish the site

The expected public URL is:

`https://mptyl.github.io/ThothAI/`
