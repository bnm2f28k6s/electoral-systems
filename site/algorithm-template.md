# Algorithm chapter template

This is a proposed writing structure, not a specification of any particular voting system.

## Definition and scope

Name the exact rule and variant. State the number of seats, the intended input, and the source defining the counting procedure.

## Inputs and validation

Define candidate identifiers and the ballot format. Explain whether rankings may be incomplete or tied, whether scores have bounds, how weights work, and which invalid inputs are rejected. Do not silently convert one ballot type into another.

## Counting procedure

Write the mathematical rule, then pseudocode, then executable code. Explain steps before using specialized terminology. Specify tie handling and any random seed rather than hiding them in an implementation detail.

## Worked example

Use a small synthetic election. Show ballots, intermediate counts or rounds, and the result. Test the exact code and expected output before publishing the example.

## Properties and limitations

Define each criterion before discussing it. Cite a proof, an explicit counterexample, or a qualified source. Distinguish empirical behavior under a simulation model from a logical guarantee. State resource bounds for the specific implementation.

## Reproducibility

Record algorithm version, input normalization, arithmetic rules, tie policy, and enough of the trace to reproduce the result. Describe what is not covered, such as voter eligibility, ballot secrecy, auditing, and election law.
