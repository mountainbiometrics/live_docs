---
title: "Dashboard"
cssclasses:
  - dashboard
---

# 🗂 live_docs — Dashboard

> [!info] What this page is
> A **Dataview** demo. Dataview lets you embed *live queries inside a note body* —
> something Bases can't do. The killer trick for this vault: it resolves the
> opaque-ID edges (`belongs_to`, `requires`, …) into **human labels and summaries**.
>
> This file is throwaway scaffolding at the vault root. `ldoc` doesn't know it exists;
> delete it anytime. Everything below is read-only — no query ever writes to a doc.

## At a glance

```dataviewjs
const p = dv.pages('"02-docs"');
const n = t => p.where(x => x.type === t).length;
dv.paragraph(
  `**${p.length}** docs &nbsp;·&nbsp; ` +
  `**${p.where(x=>x.status=="living").length}** living &nbsp;·&nbsp; ` +
  `**${p.where(x=>x.status=="deprecated").length}** deprecated &nbsp;·&nbsp; ` +
  `**${n("index")}** indexes &nbsp;·&nbsp; ` +
  `**${n("decision")}** decisions &nbsp;·&nbsp; ` +
  `**${n("principle")}** principles`
);
```

## Docs by type

```dataview
TABLE WITHOUT ID type AS "Type", length(rows) AS "Count"
FROM "02-docs"
GROUP BY type
SORT length(rows) DESC
```

## Index docs — the navigational signposts

Note how each row links to an opaque-ID file but *displays its label* — that's
`link(file.path, label)` doing the work.

```dataview
TABLE WITHOUT ID link(file.path, label) AS "Index", summary AS "What it groups"
FROM "02-docs"
WHERE type = "index"
SORT label ASC
```

## Most-revised docs (churn signal from `history`)

The number of `history` entries is a proxy for how "hot" a doc is. This reads the
nested `history` list — exactly the kind of structured access Bases tables can't do.

```dataviewjs
const rows = dv.pages('"02-docs"')
  .where(p => p.history)
  .map(p => {
    const h = Array.isArray(p.history) ? p.history : [p.history];
    const last = h[h.length - 1];
    return { p, n: h.length, last: last ? last.summary : "" };
  })
  .sort(r => r.n, 'desc')
  .slice(0, 10);
dv.table(["Doc", "Type", "Revisions", "Latest change"],
  rows.map(r => [
    dv.fileLink(r.p.file.path, false, r.p.label ?? r.p.file.name),
    r.p.type, r.n, r.last
  ]));
```

## Orphans — docs not grouped under any index

```dataview
TABLE WITHOUT ID link(file.path, label) AS "Doc", type AS "Type"
FROM "02-docs"
WHERE !belongs_to AND type != "index"
SORT type ASC, label ASC
```

## Deprecated → what superseded it

```dataviewjs
const rows = dv.pages('"02-docs"').where(p => p.status === "deprecated");
dv.table(["Deprecated doc", "Superseded by"],
  rows.map(p => {
    const sup = (p.superseded_by ?? []).map(l => {
      const t = dv.page(l.path); return t?.label ?? l;
    });
    return [dv.fileLink(p.file.path, false, p.label ?? p.file.name), sup];
  }));
```

## The headline demo — edges resolved to labels

Every decision, with its `requires` dependencies shown as **labels** instead of
`[[20260615…]]`. This is the inline "expand related docs" view you wanted — the thing
the raw frontmatter and the core graph can't give you.

```dataviewjs
const rows = dv.pages('"02-docs"')
  .where(p => p.type === "decision")
  .sort(p => p.label)
  .slice(0, 20);
dv.table(["Decision", "Requires"],
  rows.map(p => {
    const reqs = (p.requires ?? []).map(l => {
      const t = dv.page(l.path); return t?.label ?? l;
    });
    return [dv.fileLink(p.file.path, false, p.label ?? p.file.name), reqs.length ? reqs : "—"];
  }));
```
