# CHANGELOG


## v0.5.1 (2026-03-16)

### Bug Fixes

- Pyright ignores otel config and update uv lock
  ([`cc22e0b`](https://github.com/gastong256/mono256_sic-core/commit/cc22e0b496a7f2b0386ce4be94d38d4226d7db49))


## v0.5.0 (2026-03-16)

### Bug Fixes

- Apply black format
  ([`8aeb143`](https://github.com/gastong256/mono256_sic-core/commit/8aeb1439f6588822fa7fe1d47fb57630936fb936))

- Update uv lock
  ([`51d03c7`](https://github.com/gastong256/mono256_sic-core/commit/51d03c7a968ebcde396aa6afb738fafe02100f2e))

### Features

- Add versioned report caching and resilient readiness checks
  ([`1e312df`](https://github.com/gastong256/mono256_sic-core/commit/1e312df9c887c72cd55cfc4eab091edfd4190edd))


## v0.4.0 (2026-03-16)

### Bug Fixes

- Apply black format
  ([`77b7f10`](https://github.com/gastong256/mono256_sic-core/commit/77b7f1007cf3d31c4e0bbfd880c15b216d6de7bf))

### Features

- Add aggregated bootstrap and selector-friendly endpoints
  ([`c3fc4f3`](https://github.com/gastong256/mono256_sic-core/commit/c3fc4f38afc47950ef835ee4c7bc1666b9883fc9))


## v0.3.2 (2026-03-15)

### Bug Fixes

- Remove redundant response aliases in reports and teacher endpoints
  ([`fee4487`](https://github.com/gastong256/mono256_sic-core/commit/fee4487f632404f45c65ad346a7edbf498719bcd))


## v0.3.1 (2026-03-12)

### Bug Fixes

- Remove legacy chart bootstrap flag and keep LOAD_CHART_ON_START only
  ([`e6731b8`](https://github.com/gastong256/mono256_sic-core/commit/e6731b89e2c75ac25ec98ebb86835a47e66026ec))


## v0.3.0 (2026-03-12)

### Bug Fixes

- Avoid duplicate username collisions in register throttle test and add early username uniqueness
  validation
  ([`90003ce`](https://github.com/gastong256/mono256_sic-core/commit/90003cea8b916861fc1f2b5fe5785d78281bf528))

- Restore course view schema annotations and split summary/all endpoints to avoid operationId
  collisions
  ([`a7e09e0`](https://github.com/gastong256/mono256_sic-core/commit/a7e09e0c35fb540b8b6a84dcfabfe23d2e22ff9d))

### Features

- Add batch visibility updates, teacher aggregated endpoints, and backward-compatible report/auth
  response aliases
  ([`75a5ae7`](https://github.com/gastong256/mono256_sic-core/commit/75a5ae73dd450304be1240cc162fe6306e030660))


## v0.2.1 (2026-03-11)

### Bug Fixes

- Add redis runtime dependency to prevent token endpoint failures in production
  ([`ea3ed39`](https://github.com/gastong256/mono256_sic-core/commit/ea3ed39f9927fce27f7fc34b113641cfdad28cd6))

- Harden codecov upload with v5 oidc and non-blocking fallback
  ([`278ab8c`](https://github.com/gastong256/mono256_sic-core/commit/278ab8c29213d41b2401a5129c8a9044f54ed6f2))


## v0.2.0 (2026-03-11)

### Features

- Add one-time bootstrap admin creation for no-shell environments
  ([`5f476a1`](https://github.com/gastong256/mono256_sic-core/commit/5f476a12aabd185ae71047c35ddb39f14c8bdac8))


## v0.1.10 (2026-03-11)

### Bug Fixes

- Add configurable migrate verbosity for free-tier startup
  ([`c26435f`](https://github.com/gastong256/mono256_sic-core/commit/c26435f01f7c175ff09861c1992c1732059bad46))


## v0.1.9 (2026-03-11)

### Bug Fixes

- Trigger Render deploy on release published and manual dispatch
  ([`f67d7cf`](https://github.com/gastong256/mono256_sic-core/commit/f67d7cf3e8d7db14ee01e3a56cc0e8849f3de1a9))


## v0.1.8 (2026-03-11)

### Bug Fixes

- Use RELEASE_PAT so release tags trigger downstream workflows
  ([`8d62376`](https://github.com/gastong256/mono256_sic-core/commit/8d62376b4485e97dfd01b6555029486cf1667382))


## v0.1.7 (2026-03-11)

### Bug Fixes

- Trigger Render deploy hook on version tags
  ([`38c5a16`](https://github.com/gastong256/mono256_sic-core/commit/38c5a16fc2c2d6f9fb1525295dcd11b80e0095ba))


## v0.1.6 (2026-03-11)

### Bug Fixes

- Run migrations and collectstatic on startup for free-tier platforms
  ([`f442131`](https://github.com/gastong256/mono256_sic-core/commit/f4421316eb580f78ddf3e152562aa40f2cbf4e05))


## v0.1.5 (2026-03-11)

### Bug Fixes

- Create staticfiles directory in runtime image
  ([`8b60397`](https://github.com/gastong256/mono256_sic-core/commit/8b6039731f9e351268419d6cc499416b9f716ac8))


## v0.1.4 (2026-03-11)

### Bug Fixes

- Run collectstatic during predeploy migrations
  ([`f7b1b2f`](https://github.com/gastong256/mono256_sic-core/commit/f7b1b2fdec9783c29cd2ca49dc6957b8bd7d5c7b))


## v0.1.3 (2026-03-11)

### Bug Fixes

- Keep venv path stable across build and runtime stages
  ([`084a7f1`](https://github.com/gastong256/mono256_sic-core/commit/084a7f1fce283f3a6e3b5acb8f694c7ae6916af9))


## v0.1.2 (2026-03-11)

### Bug Fixes

- Align registration throttle threshold and silence staticfiles warnings
  ([`47aaa23`](https://github.com/gastong256/mono256_sic-core/commit/47aaa23a9c8f350557c8047cc156733e5f085ef6))

- Apply black format
  ([`f10bc0b`](https://github.com/gastong256/mono256_sic-core/commit/f10bc0b5237111adee221501943a307fd323ea4e))

- Make hordak 0055 dependency resolution resilient across package variants
  ([`a6ad899`](https://github.com/gastong256/mono256_sic-core/commit/a6ad899b3b24e735d536084822b7b2797b5068ce))

- Run full CI on main and gate release on successful CI
  ([`bedcd78`](https://github.com/gastong256/mono256_sic-core/commit/bedcd785eddad354612161b53e77b87c4e43d062))

- Run semantic-release from main branch instead of detached HEAD
  ([`b546335`](https://github.com/gastong256/mono256_sic-core/commit/b546335d003e7929247cd2fc9be7a00d6dac4ffb))

- Use frozen lockfile to prevent migration dependency drift
  ([`d6048e1`](https://github.com/gastong256/mono256_sic-core/commit/d6048e110957d6fbd19429f8e8d136b6e5219de2))


## v0.1.1 (2026-03-11)

### Bug Fixes

- Include runtime scripts in build context for Render deploy
  ([`08cb856`](https://github.com/gastong256/mono256_sic-core/commit/08cb856ed0f1389e83d7b5904426cd21e8de36fa))


## v0.1.0 (2026-03-11)

### Bug Fixes

- Add explicit typed response schemas for course companies and paginated journal entries
  ([`5c54de7`](https://github.com/gastong256/mono256_sic-core/commit/5c54de784764ddc590c5dc68a893da69cf35209d))

- Document admin users list as paginated response schema
  ([`593dda4`](https://github.com/gastong256/mono256_sic-core/commit/593dda487a0c0a42e91a57c6875b4d7bd95b2224))

- Document admin users list query params in OpenAPI (page, role, search)
  ([`07e7a34`](https://github.com/gastong256/mono256_sic-core/commit/07e7a34e5a93280837be54875ccb3bf1833e2055))

- Install python-semantic-release in workflow
  ([`e6a9a02`](https://github.com/gastong256/mono256_sic-core/commit/e6a9a028e26504c3557993d4c26258c0e3ee9b5c))

- Remove initialization gate and run semantic release on main
  ([`803b6cc`](https://github.com/gastong256/mono256_sic-core/commit/803b6cccc38ebf5bef36443dd5d3b465cf115c50))

### Chores

- Add postgres preflight and local test db make targets
  ([`a96997b`](https://github.com/gastong256/mono256_sic-core/commit/a96997b400215cba7b4d0aa927effcbcea423bab))

- Add production migration job and harden database connection settings
  ([`707625d`](https://github.com/gastong256/mono256_sic-core/commit/707625d87da20b8e0ec937e9f6d031834a24b6bb))

- Add production operations runbook and link it from README
  ([`1149ec9`](https://github.com/gastong256/mono256_sic-core/commit/1149ec93f58b722af70a7aace3e348b5f6f544b5))

- Add production-like docker compose profile with web healthcheck and prod make targets
  ([`714d5e7`](https://github.com/gastong256/mono256_sic-core/commit/714d5e7da0e7d46477a87782487257922bbbac7e))

- Add Redis-backed shared cache with local fallback and test isolation
  ([`5dcb3ae`](https://github.com/gastong256/mono256_sic-core/commit/5dcb3ae5042091f0b7d0b9ca7727f0123f993dba))

- Add structured HTTP request logging with slow-request detection
  ([`08b2c55`](https://github.com/gastong256/mono256_sic-core/commit/08b2c5577c8f4f88b8034634d8a00a1bb4fb579f))

- Add uvlock openpyxl dependency
  ([`82514b5`](https://github.com/gastong256/mono256_sic-core/commit/82514b542a835ad9dd579b6a9687b01950d9c839))

- Align lint and typecheck gates with current repo baseline
  ([`6551872`](https://github.com/gastong256/mono256_sic-core/commit/655187284784f45a05fee9eaec7eb418155eec79))

- Enforce openapi and production deployment checks in quality gates
  ([`b7db7b4`](https://github.com/gastong256/mono256_sic-core/commit/b7db7b47095600f08f6d250aaadb25f57d82dd4b))

- Harden production settings with strict host/secret validation and secure defaults
  ([`a0e08bb`](https://github.com/gastong256/mono256_sic-core/commit/a0e08bb3c20273d2a325ca77d7377295eaaac3b4))

- Migrate dev dependencies to dependency-groups
  ([`716aa27`](https://github.com/gastong256/mono256_sic-core/commit/716aa276c2fa2cf8eb0c28f09185d2e45535e895))

- Parameterize gunicorn startup via env-driven entrypoint
  ([`750971d`](https://github.com/gastong256/mono256_sic-core/commit/750971d5964df4953d0318e96224d1e2a33e765c))

- Remove unused API permissions module
  ([`8dde513`](https://github.com/gastong256/mono256_sic-core/commit/8dde5136d8c5e949240e8611258a47e1df259d43))

- Version schema artifact and standardize export workflow
  ([`ece7ab4`](https://github.com/gastong256/mono256_sic-core/commit/ece7ab48bf9d26d3121d37db4b7058bc6fd589f2))

### Documentation

- Clarify admin ownership in account management comments
  ([`05e0038`](https://github.com/gastong256/mono256_sic-core/commit/05e0038e25ff73d51265cbcfffa3218c58dbaaef))

### Features

- Add cors support, /me endpoint, and configurable jwt lifetimes
  ([`6bab123`](https://github.com/gastong256/mono256_sic-core/commit/6bab1239b746cb282bb940a64794551b6e30ba15))

- Add journal flow and its migrations
  ([`50fb0d3`](https://github.com/gastong256/mono256_sic-core/commit/50fb0d36fdd58604cd496286ee5c89b30c24d8da))

- Add on-demand xlsx export endpoints for journal book, ledger, and trial balance with runtime
  dependency guardrails
  ([`d428ca4`](https://github.com/gastong256/mono256_sic-core/commit/d428ca47abecb5ee06558485fb65f532d39627f2))

- Add paginated user listing endpoint with role/search filters
  ([`bee1810`](https://github.com/gastong256/mono256_sic-core/commit/bee1810606e13d22dac5265b49a31e6837153226))

- Add reports to summarize the information from the journals (journal, ledger, balance sheets)
  ([`748fb0f`](https://github.com/gastong256/mono256_sic-core/commit/748fb0fda84bc49d86e60cf7c4bbd21dc30dbbd6))

- Add role-based access, courses, teacher supervision, and account visibility controls
  ([`560cd4d`](https://github.com/gastong256/mono256_sic-core/commit/560cd4d47e232c23581d4a3e32f7d75833a33d12))

- Add student self-registration with rotating access code and anti-abuse throttling
  ([`3d3dc6d`](https://github.com/gastong256/mono256_sic-core/commit/3d3dc6d39943e49dd02b4be3d51439b5d365effc))

- Allow registration off available students
  ([`eabdd82`](https://github.com/gastong256/mono256_sic-core/commit/eabdd82b4fa1a64cf21483dc25184ab8825ad7d4))

- Harden producción y optimizar performance de API/reportes
  ([`9ab87f9`](https://github.com/gastong256/mono256_sic-core/commit/9ab87f9c3b15e69e20668415cdb8a71debd1daa3))

### Refactoring

- Centralize student account-visibility resolution logic
  ([`c611ae3`](https://github.com/gastong256/mono256_sic-core/commit/c611ae35f205289c7d68c7deddd14bf697320faa))

- Centralize teacher resolution for admin/teacher scoped endpoints
  ([`bafe682`](https://github.com/gastong256/mono256_sic-core/commit/bafe6827e8e3d2197a11ae6bc3486944e2479632))

- Trim generic comments and keep domain-focused docstrings for SIC/Angrisani logic
  ([`ebec3db`](https://github.com/gastong256/mono256_sic-core/commit/ebec3db249d6b194cb458943edfcf1cfe4f2d6a7))
