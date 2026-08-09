---
name: proposal-clarity-rewrite
description: "Rewrite this repo's proposal prose into plain, first-principles language. Use when revising the financial statement simulator proposal, its draft, README, or DEMO after reviewer feedback."
version: 0.1.0
---

# Proposal Clarity Rewrite

Use this skill when proposal prose is too dense, too abstract, or too jargon-heavy for a finance reader.

## Use it for

- Rewriting `proposal/Financial_Statement_Simulator_Proposal.tex`
- Rewriting `proposal/Financial_Statement_Simulator_Proposal_Draft_v2.tex`
- Updating `README.md` or `DEMO.md` when claim wording changes
- Explaining the statement-to-state-space pipeline in plain language
- Responding to feedback about unclear structure, jargon, or missing examples

## Rewrite rules

1. Keep the facts and claims unchanged unless a committed artifact proves a change.
2. Define every important term at first use.
3. Use one topic per paragraph.
4. Prefer active voice and simple tense.
5. Keep sentences short. Split compound ideas.
6. Do not use em dashes.
7. Use the proposal vocabulary consistently: structured statement, union state space, knowledge graph, mapping artifact, footing, cash tie, tag, born-digital PDF.
8. Replace slogans with mechanism statements.
9. Add one concrete example when the reader needs a bridge from abstract to concrete.
10. Tie every load-bearing claim to an artifact or section already in the repo.

## Rewrite workflow

1. Read the target section for meaning.
2. List the claims, terms, and evidence it depends on.
3. Rewrite from first principles:
   - what it is
   - how it is designed
   - why it is designed that way
4. Check terminology against `proposal/WRITING-GUIDE.md`.
5. Check claim consistency across the owner section and summary surfaces.
6. Keep numbers and dates exactly as they appear in committed artifacts.
7. If the reader still cannot picture the mechanism, add a worked example.
8. If the rewrite would change a claim, stop and verify the evidence first.

## Structural guide

When you rewrite a section, prefer this order:

1. Plain-language purpose
2. Concrete mechanism
3. Why the design matters
4. Evidence from the repo

For this project, favor the outline in `proposal/OUTLINE.md` over the old compressed draft order.

## Style

- Be direct.
- Use short paragraphs and numbered lists.
- Prefer plain words over jargon.
- Mention file paths with markdown links.
- Do not use em dashes.

## Before and after pattern

Before:
- "The system uses a standard-neutral substrate and a layered onboarding artifact to normalize heterogeneous disclosures."

After:
- "The system reads a statement, stores it in a union state space, and reprints it in the firm's own lines."

Before:
- "The graph handles semantic alignment across firms of different shapes."

After:
- "The graph maps different labels to shared economic meaning when the concepts are the same."

## Review checklist

- Can a finance reader follow it without XBRL background?
- Is every technical term defined before use?
- Is there a concrete example where the reader needs one?
- Are the claims still supported by the repo artifacts?
- Do `README.md` and `DEMO.md` still say the same thing at claim level if they repeat the claim?
