# Electoral systems as algorithms

How does a ballot become an election result? This project will explain electoral voting systems as algorithms: specify the input, describe the counting rule, trace an example, and state exactly what the result means.

This is an early documentation project. No election engine or hosted API exists yet. It is not intended to administer real elections.

## Starting point

[Comparison of electoral systems](https://en.wikipedia.org/wiki/Comparison_of_electoral_systems) provides an initial map of voting methods, logical criteria, and evaluation models. These are different kinds of comparison. Future chapters will identify assumptions behind each claim and cite relevant definitions instead of presenting a universal ranking of systems.

## Proposed reading path

1. Define candidates, ballots, and valid input before introducing a counting rule.
2. Study one single-winner rule with a small, reproducible example.
3. Compare rules using defined criteria and counterexamples.
4. Treat multiwinner and proportional representation methods separately.
5. Explore a shared API after the input and output models are clear.

## Project notes

- [Algorithm chapter template](/algorithm-template.md)
- [API design proposal](/api-design.md)
- [Generated draft API reference](/api/reference)

Docapella generates this static site from Markdown and an OpenAPI specification. The API reference is documentation, not a live service.
