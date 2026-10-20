# gh-api-gateway

A small Python launcher for `gh api` using an explicitly authorized API gateway and an existing `GH_TOKEN`. It creates a temporary gh profile, configures the experimental `api_host` setting for the logical host `github.com`, runs one API command, and removes that profile on normal exit. It does not modify your normal gh configuration.

## Requirements and use

- Python 3.9+ and a trusted GitHub CLI executable whose `gh help config` documents `api_host`. This setting is experimental; check your installed version. The implementation was informed by gh 2.102.0 help output.
- An HTTPS gateway you operate or are explicitly authorized to use, with routing compatible with GitHub API requests.
- `GH_TOKEN` supplied by an already authorized credential provider. Do not paste credentials into arguments, source files, or chat.

```sh
python3 gh_api_gateway.py \
  --gh /opt/gh/bin/gh \
  --api-host gateway.example.com \
  -- user --method GET --jq '{login, id}'
```

`gateway.example.com` and the binary path are placeholders. Confirm the returned identity and the target resource's access before making changes. The launcher does not enforce a particular account or grant repository permissions. It forwards API arguments, including write methods; choose only operations you are authorized to perform.

Alternate GitHub credential variables and gh debug variables are removed from the child environment. The existing `GH_TOKEN` stays in the child process environment, never command arguments. A fresh profile avoids persisted gh credentials and aliases. The child otherwise inherits its parent's environment, so use a trusted executable and ordinary environment hygiene. There is no credential discovery, Vault access, login, or fallback to another identity.

## Vault and platform Network secrets

A credential provider may inject `GH_TOKEN` into this launcher's process. The already public [Token Vault MCP](https://github.com/Hanssen0-Alter-Ego/token-vault-mcp) supplies its own proof-bound, one-use helper; follow that project's current instructions rather than duplicating its protocol here. A platform-managed Network secret may instead supply authentication under that platform's supported configuration. Network-only injection does not necessarily create `GH_TOKEN`; this launcher requires that variable and will stop if it is missing. Do not extract platform secrets to satisfy that requirement.

This repository does not provision a gateway, configure platform Network secrets, or repair platform authentication internals. Use only approved hosts and existing authorization. Never publish a generated private Vault plugin bundle: it can contain a management key.

## Limits

`api_host` is **not a security boundary**: gh documents that requests to the canonical host remain authenticated. A gateway can see credentials and API data. Endpoint validation here prevents common accidental overrides but is not a sandbox or an egress policy. Authentication, redirects, gateway behavior, and network restrictions must be managed separately by the operator.

Only relative `gh api` endpoints are accepted; explicit `--hostname` overrides and arguments containing `://` are rejected. The latter deliberately also excludes URL-valued request fields. Git clone/push, artifacts, other gh commands, redirects, and large transfers are outside this launcher's verified scope. Temporary profile cleanup is best effort on normal process exit; forced termination may leave a profile containing the gateway hostname (the launcher does not write the token there).

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use synthetic environment values and a mocked CLI boundary. They cover routing, credential-variable selection, private profile creation/cleanup, failure propagation and endpoint restrictions. They do not contact GitHub, Vault, or a gateway, and do not establish live interoperability. No third-party code is bundled. New launcher and tests are licensed under MIT; linked projects retain their own terms.
