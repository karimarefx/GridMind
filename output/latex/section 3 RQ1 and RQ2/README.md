# section 3 RQ1 and RQ2

Standalone clean PDF and editable LaTeX for the two assigned research questions, shortened and edited with the Humanizer skill. The original longer version and Sections I and II are preserved separately. This package contains no teammates' sections.

## Compile

From this folder, run:

    tectonic --keep-logs main.tex

Alternatively run pdfLaTeX, BibTeX, then pdfLaTeX twice. The TeX installation must include IEEEtran, newtxtext, newtxmath, cite, xurl and hyperref.

## Merge into the proposal

Copy `section_iii_karim.tex` alongside the proposal's main source. Insert `\input{section_iii_karim.tex}` after Section II and before the proposal's bibliography. The fragment supplies the Section III heading and subsections A and B; subsequent teammates can append RQ3 onward under the same section. Do not insert the standalone wrapper's `\setcounter{section}{2}` into the combined proposal.

The bibliography reuses the existing study keys. The existing proposal bibliography already contains all entries used here; do not duplicate them. Compile the combined proposal to generate its own citation numbers. The standalone PDF numbers its cited references independently in first-citation order. Its wrapper balances the standalone reference columns with `\IEEEtriggeratref{9}`; this command is not part of the insertable fragment and should not be copied into the combined proposal.

The opener introduces all five RQs for the eventual combined Section III; only RQ1 and RQ2 are included in this contribution.

`main.tex` is only the standalone wrapper. `section_iii_karim.tex` is the editable submission text. `references.bib` contains only the 18 cited studies. The PDF has no review highlights or annotations.
