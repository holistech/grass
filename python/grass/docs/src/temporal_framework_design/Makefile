# Build the code design document of the temporal framework.
#
# make          build design.pdf and copy it to ../Temporal-Framework-Code-Design.pdf
# make clean    remove what the build leaves behind
#
# digest.tex holds the SHA-256 of the sources, which design.tex writes into
# the keywords of the PDF. temporal/tests/temporal_framework_design_test.py
# computes the same digest (source_digest) and compares: one line per file
# other than digest.tex and RESIDUES, in the order of the paths as sort(1)
# gives them in the C locale, made of the path, a NUL byte, the SHA-256 of
# the content and a newline. The test reads RESIDUES from this file.

TARGET = ../Temporal-Framework-Code-Design.pdf

# What pdflatex and bibtex leave behind, and only that: any other file, a
# PDF figure as well, counts as a source.
RESIDUES = design.aux design.bbl design.blg design.log design.lof design.lot \
	design.out design.pdf design.toc

.PHONY: all clean digest.tex

all: $(TARGET)

digest.tex:
	@find . -type f ! -path ./digest.tex $(foreach file,$(RESIDUES),! -path ./$(file)) \
		| sed 's|^\./||' | LC_ALL=C sort \
		| while IFS= read -r file; do \
			printf '%s\0%s\n' "$$file" "$$(sha256sum < "$$file" | cut -d' ' -f1)"; \
		done \
		| sha256sum | cut -d' ' -f1 \
		| sed 's|.*|\\newcommand{\\sourcedigest}{&}|' > digest.tex

design.pdf: digest.tex
	pdflatex -interaction=nonstopmode -halt-on-error design
	bibtex design
	pdflatex -interaction=nonstopmode -halt-on-error design
	pdflatex -interaction=nonstopmode -halt-on-error design

$(TARGET): design.pdf
	cp design.pdf $(TARGET)

clean:
	rm -f $(RESIDUES)
