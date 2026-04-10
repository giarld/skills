---
name: make-pdf
description: Generate a professional, compileable LaTeX document and final PDF from structured source materials such as outlines, notes, transcripts, articles, screenshots, diagrams, datasets, or mixed research assets. Use when the user wants a reusable PDF production workflow that is not tied to any one content platform.
---

# Make PDF

Use this skill to turn source materials into a complete, compileable `.tex` document and a rendered PDF.

This skill extracts the general PDF-production layer from platform-specific workflows. It is suitable for lecture notes, technical reports, reading notes, tutorials, explainers, summaries, internal memos, and figure-rich educational documents.

## Goal

Produce a professional PDF package from arbitrary source materials.

The output must:

- be a complete `.tex` document from `\documentclass` to `\end{document}`
- compile successfully to PDF as part of final delivery
- preserve the important content and structure of the source materials
- use figures, formulas, code blocks, tables, and callout boxes when they materially improve understanding
- include a clean front page with document metadata and an optional cover image

## Accepted Inputs

This skill is intentionally source-agnostic. Inputs may include:

- user-written outlines or rough notes
- markdown, plain text, HTML, or existing documents
- transcripts, captions, or interview records
- screenshots, diagrams, plots, tables, or scanned figures
- code snippets or repositories that need explanatory writeups
- mixed assets collected in a working directory

If the source is large or heterogeneous, first normalize it into a working set: metadata, text sources, images, generated plots, and a target outline.

## Workflow

### 1. Inspect the source package first

Before writing:

- identify the main source type and intended document type
- list the available assets and their likely roles
- extract title, author, date, source URL, and cover image if available
- identify whether the document should read as notes, tutorial, report, or synthesis

### 2. Design the document structure

Create a structure before drafting prose.

- define the top-level sections
- break dense sections into smaller subsections
- decide where figures, formulas, code, tables, and boxes are actually needed
- reconstruct the most teachable or most readable flow instead of mirroring raw source order when that order is noisy

### 3. Start from the template

Start from `assets/document-template.tex`.

- fill the metadata block
- set `\coverimagepath` when a suitable cover exists
- replace the body placeholder with the final document content
- keep the final document self-contained and compileable
- the template prefers `ctex` when available and falls back to plain XeLaTeX when it is not; for Chinese-heavy output, a fuller TeX install with CJK support is still preferable

### 4. Write for understanding

The document should read like it was edited by a careful human author.

- explain motivation before detail when the material is conceptual
- keep transitions explicit so the reader can follow why one section leads to the next
- compress repetition, but do not drop critical detail
- use normal prose for routine exposition and reserve emphasis boxes for genuinely high-signal ideas

## Writing Rules

1. Write in the language requested by the user. If unspecified, preserve the dominant language of the source materials.

2. Organize the document with `\section{...}` and `\subsection{...}`.
   Reconstruct order when needed for clarity.

3. Keep the front page informative and restrained.
   If a cover image is available and useful, place it on the first page via the metadata block.

4. Use figures whenever they materially improve explanation.
   Do not add decorative images.

5. Do not place images inside custom message boxes.

6. When a mathematical formula appears:
   first explain in plain language what it expresses and why it appears
   show it in display math using `$$...$$`
   then immediately follow with a flat list that explains every symbol when the notation is nontrivial

7. When code examples appear:
   explain the role of the code before the listing
   wrap the listing in `lstlisting`
   include a descriptive `caption`

8. Use callout boxes deliberately:
   use `importantbox` for core claims, definitions, and must-remember mechanisms
   use `knowledgebox` for context, prerequisites, intuition, and side knowledge
   use `warningbox` for mistakes, caveats, hidden assumptions, and misleading intuitions

9. End each major section with a short local synthesis when the material is dense.

10. End the whole document with a final top-level section such as `\section{总结与延伸}` or `\section{Conclusion and Next Steps}`.
    That section should compress the core takeaways and, when appropriate, include limitations, open questions, or practical follow-up actions.

11. Do not emit unresolved placeholders such as `[cite]`, `TODO`, or unfinished template markers in the final LaTeX.

## Figure and Asset Handling

Select figures for explanatory value.

- prefer the clearest and most complete asset version available
- crop or redraw cluttered visuals when doing so improves readability
- if an external visualization would explain the idea better than a screenshot, rebuild it using LaTeX-native tools or scripts
- prefer vector output such as `pdf` for generated charts and diagrams

When a figure comes from a source asset with meaningful provenance, record that provenance in nearby prose or a footnote when it helps the reader or future maintenance.

## Visualization

For material that is hard to explain with prose alone, add accurate visualizations.

Two preferred routes:

- generate LaTeX-native visuals with TikZ or PGFPlots
- generate figures ahead of time with scripts and include them as images

Use visualizations for:

- process flows and pipelines
- architecture diagrams
- plots, curves, and comparisons
- distributions and heatmaps
- rewritten tables or summary charts
- concept maps that compress a section's main idea

## Compilation

The document is not complete until it compiles.

Preferred compilation flow:

1. Try `latexmk -xelatex -interaction=nonstopmode -halt-on-error <file>.tex`
2. If `latexmk` is unavailable, run `xelatex` enough times to resolve references
3. Inspect the log for missing assets, broken commands, overfull layout issues, and package failures
4. Fix compile errors instead of handing the user an unbuilt `.tex`

## Final Checklist

Before delivery, verify all of the following:

- the metadata block is filled correctly
- all referenced figures and generated assets exist
- code listings, tables, formulas, and callout boxes compile correctly
- the narrative flow is coherent rather than source-dump shaped
- the final PDF was actually produced

## Delivery

Deliver all of the following:

- the final `.tex` file
- any copied or generated figure assets referenced by the document
- the compiled PDF
- optional helper artifacts only when they are actually useful, such as generated charts or logs

## Asset

- `assets/document-template.tex`: default LaTeX template to copy and fill
