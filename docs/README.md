# Site-Sentry documentation

Site-Sentry is a Python CLI that **audits a live site with Lighthouse**, **plans fixes** with a LangGraph manager, runs **specialized agents** (SEO, performance, errors, optional content), and **opens a GitHub pull request** when configured.

## Documentation index

| Document | Description |
|----------|-------------|
| [Getting started](getting-started.md) | Install, `sentry init`, first run, prerequisites |
| [Configuration](configuration.md) | `sentry.config.yaml`, environment variables, `SentryConfig` |
| [CLI reference](cli.md) | `sentry` commands and flags |
| [Architecture](architecture.md) | Pipeline, agents, memory, GitHub integration |
| [Python modules](api-reference.md) | Package layout and important entry points |
| [Deployment](deployment.md) | Docker image and Compose service |
| [Troubleshooting](troubleshooting.md) | Common failures and checks |

## Repository

- [GitHub: rajatbalyan/agentx-2025](https://github.com/rajatbalyan/agentx-2025) (repository name; the Python package is **`site_sentry`**, CLI command **`sentry`**)

## License

See [LICENSE](../LICENSE) in the repository root.
