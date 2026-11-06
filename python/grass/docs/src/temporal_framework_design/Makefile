# Build the code design document of the temporal framework.
#
# make          build design.pdf and copy it to ../Temporal-Framework-Code-Design.pdf
# make clean    remove what the build leaves behind
#
# digest.tex holds the SHA-256 of the sources, which design.tex writes into
# the keywords of the PDF. temporal/tests/temporal_framework_design_test.py
# computes the same digest (source_digest) and compares: one line per file
# that is not a build residue, in the order of the paths as sort(1) gives
# them in the C locale, made of the path, a NUL byte, the SHA-256 of the
# content and a newline. Keep the excluded names here and in BUILD_RESIDUES of
# the test equal.

TARGET = ../Temporal-Framework-Code-Design.pdf

.PHONY: all clean digest.tex

all: $(TARGET)

digest.tex:
	@find . -type f ! -name digest.tex ! -name '*.aux' ! -name '*.bbl' \
		! -name '*.blg' ! -name '*.log' ! -name '*.out' ! -name '*.pdf' \
		! -name '*.toc' ! -name '*.pyc' ! -path '*/__pycache__/*' \
		! -path '*/_minted*' \
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
	rm -f design.aux design.bbl design.blg design.log design.out design.toc \
		design.lof design.lot design.pdf
