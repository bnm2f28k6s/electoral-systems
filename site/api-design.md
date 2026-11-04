# API design proposal

**Status: exploratory contract example. No backend is implemented.** The endpoint shown in the reference cannot be called on this GitHub Pages site.

## What OpenAPI contributes

[OpenAPI 3.0](https://spec.openapis.org/oas/v3.0.3.html) describes HTTP operations and data schemas. [Docapella's OpenAPI support](https://docapella.com/openapi) renders specifications into reference pages and navigation. It does not implement counting rules or create an API server.

The included specification starts with one small operation, `GET /systems`, to demonstrate documentation integration without pretending we have agreed on a universal election request.

## Possible next step

A future counting operation might accept an exact system identifier and version, candidate identifiers, a ballot format appropriate to that rule, and explicit variant options. It could return winners or unresolved ties and an inspectable count trace. This is a proposal, not the implemented contract.

Before specifying it, decide how to handle ranked, approval, score, and party-list ballots; invalid ballots; incomplete rankings; ties; fractional arithmetic; multiple seats; and reproducible randomness. A generic schema must not conceal incompatible rules.

## Hosting boundary

GitHub Pages hosts static documentation and files. A working election API would need separate compute hosting, validation and resource limits, and its own security review. No real ballots or voter data should be submitted to this documentation project.
