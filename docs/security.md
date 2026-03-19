# Security Notes

This project currently documents security as a set of practical good practices, not as a formal security program.

## Authentication and Authorization

- API access is authenticated.
- Role-based access applies across admin, teacher and student roles.
- Company and course visibility is enforced in the backend.
- Demo companies are read-only after import.

## Secrets

- never commit secrets
- use environment variables or the platform secret store
- production secrets should be rotated through operational procedures, not source control

## Production Defaults

- keep `DEBUG=false`
- use production settings in production
- enforce HTTPS at the edge
- keep trusted hosts and CSRF origins explicit
- use Redis over TLS when the provider requires it

## Demo Imports

Demo imports are operationally convenient, but still deserve care:

- only import trusted payloads
- prefer one-shot import flags
- switch import flags off after use
- treat public demo URLs as public assets

## Principle of Least Privilege

- keep admin access restricted
- use read-only demos when the data should not be mutated
- avoid overexposing internal operations to student roles

## Incident Mindset

The project currently favors:

- fast detection
- simple rollback
- clear logs
- operational alerts

Detailed incident handling procedures belong in the operations layer and deployment environment.
