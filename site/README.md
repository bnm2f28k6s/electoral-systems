# Electoral systems as algorithms

An election rule turns ballots into a result. Different rules can choose different winners from the same voters. This guide explains **25 ways to choose one winner**, with worked counts, criteria, runnable Python and TypeScript, and a local API that executes the algorithms.

Start with [plurality](/methods/plurality.md): each voter supports one candidate, and the largest total wins. Then try [instant-runoff](/methods/instant-runoff.md), which transfers preferences, or [approval](/methods/approval.md), which lets voters support several candidates. The [method catalog](/methods.md) covers every row in the single-winner comparison table used as our starting reference, including its lottery methods.

## Follow a ballot through the count

<Steps>
  <Step title="Choose the ballot format">
    A single mark, an ordered ranking, approvals, and numerical scores convey different information. Read the [ballot guide](/ballots.md) before comparing results.
  </Step>
  <Step title="Run a counting rule">
    Each method chapter explains the steps, shows intermediate counts, and includes complete Python and TypeScript examples. Copy a code block into a file and run it locally.
  </Step>
  <Step title="Understand the tradeoffs">
    A criterion is a precise guarantee over elections, not a quality score. Read the [criteria guide](/criteria.md) and each method's qualifications. No rule satisfies every desirable property.
  </Step>
  <Step title="Simulate an API request">
    Start the [local server](/api-design.md), send synthetic ballots, and inspect its JSON response. It runs the same Python engine as the examples.
  </Step>
</Steps>

## What the examples mean

The algorithms are deliberately small teaching implementations. Ranked examples use complete rankings with no equal ranks. Intermediate ties use the order in which candidates were supplied; final equal winners are returned together. Random methods expose their distribution and use a reproducible seed. These choices are part of the documented variant, not universal election rules.

The [sources](/sources.md) distinguish definitions, mathematical properties, and practical implementation choices. A property of a standard method may depend on assumptions that our restricted example cannot express. Each chapter records those qualifications rather than treating one successful count as a proof.

GitHub Pages serves this documentation; it does not run a backend. The API runs locally. This resource explains counting and does not provide voter registration, secret ballots, election administration, or certification.
