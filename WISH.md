# Wishlist items

Noting these here as potential followup tasks so that it's recorded without having to tackle them right away.

## Skill Improvements

- [ ] A new skill for "orchestrators"?  Something that tells an agent that is delegating livedocs skills to subagents, how to do that efficiently (not micromanaging, not pre-determining scope, etc.)
- [ ] Some "macro" orchestrator skills that work like claude's `code-review` skill where it fans out a specific set of subagents that scan for things from different perspectives.
  - [ ] Like a review agent; looks at changes, checks cascade decisions, identifies cruft and stuff immediately instead of waiting for followup gardening passes, etc.
  - [ ] A tree exploring agent that tries looking at the system as a whole (and finds discrepancies in it)
  - [ ] A "Why" not "What" agent that focuses on live_docs' principles

## Review Improvements

- [ ] Make an `ldoc` command/helper that "stages" a "review" (generates a `git add ...` command that stages a review and all the docs that it touched, so that if there are multiple reviews, they can be pushed through `git` in contextual batches)
- [x] Rework "review" tracking process:
  - [x] Instead of tooling around "timestamp", have a "session_id".
  - [x] LLMs (instead of checking the current time) initiate a new "session" (and get a unique id, and put it in their env vars)
  - [x] All `ldoc` commands can take `--note` params (and track the session_id from the env vars) and "log" their changes alongside that optional note (same note that will automatically be on the "history" log)
- [x] LLMs can finalize their session with a summary.
- [x] Make review files more mechanically structured (require using ldoc instead of allowing hand-writing)
- [x] Put edge additions (non-hierarchical) in "Minor Alterations" instead of "Revisions"
- [ ] Refine/clean the cascade summaries (I don't actually know where those originated...) (could make mechanical, should use wikilink-style either way)
- [ ] Really emphasize that the review process is the main mechanism for keeping the human in the loop, and it shouldn't ever be skipped (though with the rework it will be easier to mechanically enforce)
- [x] Reviews should show deleted docs...

## CLI Improvements

- [ ] Add an auto/self-updater that checks for and/or gets the latest version
- [ ] "installing" should maybe copy the binary instead of linking? or something, so that it's "versioned" and not picking up local changes unintentionally?
- [ ] Audit/refine flags for consistent conventions
- [ ] Audit/refine verb list (want to make sure it stays concise)
  - [ ] Add more "aliases" (like `list` should be another alias for `ls`)

## Viewer Improvements

- [x] Type icons should show up in wiki-link-style expansions in text
- [x] Doc ID should be visible in more views (doesn't need to be prominent, but agents will usually reference docs by id)
- [x] "Neighbor-graph" could be a lot more useful if it were edge-aware; hopping to only specific edges depending on the current edge:
  - [x] When showing ancestors, hop to their ancestors (maybe two generations up?)
  - [x] When showing descendents, hop to their descendants (one generation)
  - [x] When showing requires, hop to their _ancestor_ (one generation, just to see their immedite scope)
  - [x] When showing relates, don't hop anywhere
  - [x] Don't even show a single hop to references
- [x] Neighbor-graph always on
- [x] Neighbor-graph nodes styled based on type and/or domain?
- [x] Review "summary" shows more:
  - [x] count new docs
  - [x] count how many new edges to existing docs
  - [x] count touched (existing) docs
  - [x] count of new edges from existing to existing docs
  - [x] Summary text (if provided; see below)
- [x] "inline" view should be in a side-panel

## Reference handling

- [ ] Make the "normalized" reference docs... better.
- [ ] Disregard reference (or archived) docs in most `ldoc` commands (like validate)
  - [ ] And deprioritize them in search commands (ie: group them last)
- [ ] Disregard reference (or archived) docs in most views within the viewer (don't show in graph or reader tree; catalog defaults to living status — references still appear in per-doc connection lists)
- [ ] Reference (or archived) files should be immutable (`ldoc` should prevent changes, and warn against attempts)
  - This is to prevent attempts at treating references as live docs; they're "snapshots"; if they're irrelevant, they should be deleted (re-snapshotted)
  - Just to make the "live_docs" vs. "normal documentation" distinction clear.

## Status/Level Improvements

- [ ] Better clarification between these.
- [ ] Stricter/better assignment between "incidental", "preference", and "requirement"
  - [ ] Better instructions for allowing new "explicit" information to overwrite existing "incidental" information (ie: at least account for this in that decision process)
  - [ ] Maybe pick a better name for "requirement" since that conflicts with the `type`
- [ ] Stricter/better assignment between "target", and "living" 
- [ ] Consolidate current `types`?  (or at least set them up to better clarify the abstract "why" vs. the spec-like "what")
- [ ] Make clear the allowance to describe conflicting dichotomies:
  - eg: When documenting a system that has some backwards compatibility support, there would be multiple conflicting "paths", and that's fine, live_docs should just make it clear/obvious that one is the desired state and one exists solely to support an existing constraint.
  - There are a couple of places where I've mentioned that we don't store "migration information", but that's for stuff like mid feature deployment kind of migrations; for "migrating to kubernetes" as a multi-month long initiative that is absolutely worth adding to live_docs
- [ ] speaking of temp work: I think that a section for wishlist/backlog/in-progress notes would be valuable...
  - Not to replace PM/task-tracking software or anything, but as a place to "stage" stuff, and where it can start being tied in to the rest of the docs, but in a shadow way.
  - [ ] Like reference docs, these docs should be outside of normal checks and searches and stuff.
  - [ ] Get it's own section in the "home" page of the viewer
  - [ ] Also: "pending actions" where LLMs can add their own notes, requests, questions
    - [ ] Something is deprecated, it cascades to another doc, that doc needs to be revised or deprecated itself; but the LLM doesn't know the desired resolution: it can mark it as needing clarification: that pending clarification lives in this subsystem.
    - [ ] Things marked as "target" can be noted here (so they actually get followed up on), and can be "promoted" to actualized (though the "target" vs. "actual" was a little bit more for the whole dichotomy thing)
    - [ ] (especially since LLMs are so reluctant to rewrite things) note inconsistencies or conflicts that need input before cleaning up.

## Config Options

- [ ] Could provide a set list of desired domains
- [ ] Could provide a custom set of types along with their descriptions, and instructions for how LLMs should understand or use them.
- [ ] Custom viewer options
  - [ ] build location
  - [ ] port and stuff (if server, see below)
  - [x] Options for setting the html `title` (tab + navbar heading), `subtitle`, and `favicon`
  - [x] domain -> color map for pill/node colors
  - [x] type -> icon map for the prefix icons
  - [ ] custom css rules?

## Storage Improvements

- [ ] Decide a better `id` format.  Things to consider:
  - We need something that won't conflict if people (or agents) are adding docs at the same time
  - Git's hashes are nice because their leftmost characters have just as much entropy, meaning you can shorthand reference them with their first characters.
    - Can't actually "hash" because our docs aren't immutable (as opposed to git commits which are)
  - Current ones have the advantage of being automatically "sorted"... so we would lose that (just to be aware)
- [ ] Migration helpers? (like if we rename a frontmatter field, it comes with a script to migrate existing)
- [ ] Question whether flat files is ideal (could maybe use a metadata database?)

## Package/Ergonomics (maybe? Eventually?) - Don't do lightly

- [ ] Viewer "server" for file-watching, hot-reloading, and maybe things like review signoff
- [ ] Decide on a real CLI framework?
- [ ] Make a real python package? (test suite, packaging, etc.)


## Integrated Lexicon

- [ ] A "box" for listing lexical terms
- [ ] A structure/definition for defining terms: (domain, term, definition, allowed_aliases, restricted_aliases, similar_terms, etc.)
- [ ] Define a format for explicit linking (specifically for terms that appear in multiple "domains")
- [ ] `ldoc` formatter auto-links terms within docs' bodies/summaries
- [ ] `ldoc` helpers/validators that "suggest" or "auto-explicit-link" terms in a changed doc
- [ ] `ldoc viewer` auto-links terms
  - [ ] and hover/tooltip definitions
  - [ ] a "catalog-like" view for lexical terms
    - [ ] (maybe) some usage stats (num of docs with backlinks, count per doc_type?, count per scope/domain?)
- [ ] Replace any vestigial "keywords" field/functionality to instead lookup by these "terms" as keywords.
- [ ] New or integrated Agent Skills:
  - [ ] identify terms that should be added to the lexicon
  - [ ] add/adjust definitions of terms
  - [ ] identify overlapping or conflicting terms
  - [ ] align/garden docs to replace "restricted_aliases" with approved terms
