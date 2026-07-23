# Writing guide for this white paper

These conventions govern every edit to the paper under `paper/`. They are enforced
automatically: `CLAUDE.md` (loaded at the start of every session) instructs the
assistant to follow this guide on every edit. Keep this guide and `CLAUDE.md` in sync.

## 1. The cardinal rule: first principles before use

Introduce every concept and every equation from first principles, and explain it before
using it. Nothing appears cold.

Concretely, before a term, symbol, or formula is deployed in an argument:

- **Define the term at first use**, in plain language, before leaning on it.
- **Introduce notation before it appears in a formula.** No symbol shows up in an
  equation that was not named first.
- **Give the intuition before the formalism.** Say what the equation means and why it is
  true in words, then write it.
- **Derive equations, or summarize the derivation and point to the appendix.** Do not
  assert a formula the reader is expected to take on faith; either show where it comes
  from inline, or give the one-line idea and cite the appendix that does it in full.
- **Assume a smart non-specialist.** A reader with no economics or finance background
  should be able to follow, because each idea was built up rather than referenced.

Worked examples already in the paper, to match the standard:

- The spending rule `d log S / d log P = 1 - e` is derived from the identity `S = P*Q`
  (full algebra in Appendix A) before it is used to settle the elasticity debate.
- The debt identity `Delta d = (r-g)/(1+g) d + p` is derived in Appendix B, and the
  "snowball" intuition is explained in words before any number is plugged in.
- The equation of exchange `M*V = P*Y` is stated and explained before the money-growth
  "headroom" is drawn from it; `seigniorage = money growth x base/GDP` is built from the
  definition before the 2%-of-GDP bound is asserted.
- Elasticity is defined before the elastic and inelastic regimes are named; TAM,
  category, and capturable are each defined before the figure compares them.

A quick checklist for any new concept or equation:

1. Is the term defined, in words, at first use?
2. Is every symbol introduced before it appears in a formula?
3. Is the intuition stated before the math?
4. Is the equation derived inline, or its derivation summarized with a pointer to an
   appendix?
5. Could a smart non-specialist follow it with no prior background?

If any answer is "no," explain it first.

## 2. Style and voice

- **No em dashes.** Use commas, semicolons, parentheses, and hyphens. Inherited from the
  source conversation; the build is checked for this.
- **One continuous argument**, not a stitched set of topics. The spine is: when AI
  collapses the price of cognition, where does the released value go? Two forces decide
  it (demand-side elasticity; supply-side moats), and the paper builds those tools, then
  applies them in widening circles (the TAM, the macroeconomy, the SpaceX bet).
- **Tight and information-dense**, matching the existing prose. State each idea once, in
  its natural home, then cross-reference rather than repeat.
- **Intellectual honesty.** Concede valid counterpoints and steelman the other side;
  separate what is established from what is illustrative; flag the parameters nobody has
  measured; correct overstatements when found.
- **Name slippery distinctions explicitly** rather than blur them: TAM (addressable) vs
  category vs capturable; real vs nominal; printed vs tax-financed; the category's
  elasticity vs a provider's.

## 3. Structure and mechanics

- **Modular LaTeX.** `main.tex` inputs `preamble.tex`, `sections/NN-*.tex`,
  `appendices/X-*.tex`, and `figures/fig-*.tex`; references live in `references.bib`.
  Appendix filenames match their rendered letters.
- **Callout boxes** (defined in `preamble.tex`), used sparingly: `keytakeaway` for a key
  idea, `workedexample` for a worked calculation, `cautionbox` for a caveat.
- **Worked models go in appendices**, fully exposed: state every assumption, build the
  formula from first principles, give a scenario table, and label them "illustrative,
  not a forecast."
- **Figures** are either conceptual (a theoretical relationship) or grounded in cited
  data or a transparent own-calculation. Never fabricate an empirical series; cite the
  source in `references.bib`.
- **Provenance.** Source conversations are preserved verbatim under `conversation/`; new
  discussions that feed the paper are saved there too, and the provenance appendix lists
  them and flags forward-looking or as-reported facts.

## 4. Build hygiene

- Build with `make` (or `cd paper && latexmk -pdf main.tex`). It must compile with **zero
  undefined references** and no real errors.
- Fix overfull boxes beyond a few points; keep the deliverable em-dash-free.
- After a figure or table change, render the page and look at it before committing.
- Run `make check` before committing (the mechanical backstop in `scripts/check.sh`).
- Commit the rebuilt `paper/main.pdf` with the source.

## 5. Consistency is claim-level, not just structural

A substantive claim lives in one **owner** section but is restated in several **summary
surfaces**. When the owner is corrected, the summaries go stale unless the change is
propagated. Cross-references resolving, section counts, and the absence of stale facts do
**not** catch this; it is a semantic, claim-level check. (This is the failure that left a
pre-correction TAM verdict sitting in the abstract after Section 5 had been corrected.)

**The summary surfaces.** Re-read all of these on any substantive claim change, and
whenever asked whether the paper is consistent:

- the abstract (`paper/main.tex`),
- the introduction's fork and roadmap (`paper/sections/01-introduction.tex`),
- the synthesis, including the fork table and the verdict paragraph
  (`paper/sections/09-synthesis.tex`),
- the closing of the extension (`paper/sections/10-extension-ubi.tex`),
- every figure caption that states a verdict (currently
  `paper/figures/fig-tam-scenarios.tex`),
- the README's outline and intro (`README.md`), which restate every section's verdict (and
  are scanned by `make check`).

**The rule.**

1. When you change a substantive claim, open every summary surface and update each
   restatement to match. Then re-read each to confirm it states the *same* claim, in the
   *same direction*, as the owner section.
2. Treat your own recent edits as suspect. Re-read them; do not assume they already align.
3. When asked "is it consistent," re-read all summary surfaces and diff each restated claim
   against its owner. Report *what* you checked (claim-level vs structural). Never answer
   "yes, consistent" from a structural skim.
4. Run `make check` (build, undefined refs, em dashes, retired phrasings) as the mechanical
   backstop. It does not replace step 3.

**The load-bearing claims** (keep these phrased the same wherever they appear):

- *TAM*: \$22.7T is an *addressable* figure, not capturable revenue; elastic / latent demand
  can match or exceed it as a *category*; capture is gated by a moat and collapses to
  single-digit trillions; the token layer commoditizes. (TAM vs category vs capturable.)
- *Debt*: AI helps through real growth (`g` vs `r`), not deflation or printing; the monetary
  headroom is bounded and self-undermining.
- *Employment*: augmentation vs replacement turns on the labor share, not GDP.
- *Growth*: the long ~2% trend is *maintained* by a relay of general-purpose technologies, not
  guaranteed; AI is a candidate to be the next link, with a serious, mechanism-backed (unlike the
  bubble's) tail case of acceleration that the *weak links* (the hardest tasks to automate) throttle;
  even explosive growth does not settle the distribution fork. (Gordon's exhaustion vs. Jones.)
- *Orbital*: the FLOP is a commodity; the only durable moat is launch; the thesis reduces to
  one cost-per-FLOP inequality; a real moat does not imply a right price.
- *The central fork*: when AI cheapens cognition, value flows to consumer surplus and wages,
  or to the owners of a scarce layer.

**Retired phrasings** (must not reappear; mirror this list in `scripts/check.sh`):

- The TAM critique framed as the headline "deflating," "the more AI wins, the smaller it
  gets," or "prices a cheap world at expensive prices." The corrected critique is that the
  number is *ungrounded*, and that *capture* is the sliver.
- "the TAM fails both laws" / "neither law supports it as capturable revenue." The demand law
  vindicates the addressable *size*; only the supply law denies *capture*.
- The orbital verdict framed as cost-only ("the only question is cost," "the thesis reduces to one
  cost-per-FLOP inequality"). The corrected verdict is two axes, cost *and* deployment speed, both
  gated by launch.

Add to this list whenever a substantive claim is corrected.

**What auto-maintains, and what you update by hand.** `make check` scans *every* `.tex` under
`paper/` plus `README.md`, so new sections, figures, and appendices are covered by the mechanical
guard automatically; there is no file list to keep current, and the summary-surface list above is a
*principle* (any file that restates a verdict it does not own), not a fixed set, so a newly added
surface is already in scope and just needs re-reading against its owner. Two things cannot be
inferred by a script and must be updated by hand, as part of the edit that occasions them:

1. the **retired-phrasings list** in `scripts/check.sh` (and mirrored above);
2. the **load-bearing claims** above: keep their canonical phrasing current as the argument evolves.

These are not a chore to remember later. Recognizing that an edit *reframes, corrects, or
retires* a claim (from the request, e.g. "fix this," "that's overstated," "we no longer say X," or
from your own act of replacing a verdict's wording) is a judgment you make at the moment of the
edit, and the follow-through is part of that same edit: retire the old wording in the guard,
propagate the corrected claim to the summary surfaces, run `make check`. A script cannot infer what
you just retired; you can, because you are the one retiring it. Only the semantic diff itself
(does this restatement mean the same as its owner?) stays a judgment step, the one `make check`
prints at the end.
