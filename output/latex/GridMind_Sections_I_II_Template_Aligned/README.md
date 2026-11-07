# GridMind Sections I and II

Clean editable LaTeX source and compiled PDF, following the supplied university template. The PDF contains no review highlights or comments.

## Compile

Run from this folder with the required TeX packages (IEEEtran, newtxtext, newtxmath, TikZ, and the packages listed in main.tex):

    tectonic --keep-logs main.tex

Alternatively use pdfLaTeX, BibTeX, then pdfLaTeX twice.

## Edit

- main.tex: Sections I and II, Table II, and bibliography commands.
- table_I.tex and table_III.tex: extraction and descriptive statistics.
- references.bib: references.
- selection_figure.tex and selection_figure.pdf: selection figure.
- diagram_labels.json: diagram labels.
- template_diagram_original.png: original university diagram background, preserved losslessly.
- edit_template_diagram.py: fills the original diagram text interiors while preserving boxes, arrows, phase bars, colours and geometry. Run `python edit_template_diagram.py` after changing the labels (requires PyMuPDF and Pillow), then recompile.
- main.pdf: compiled clean version.

The diagram distinguishes overlapping keyword-result occurrences from individual candidate-study records. The final 18-study count comes from the candidate branch; the branches are not additive.
