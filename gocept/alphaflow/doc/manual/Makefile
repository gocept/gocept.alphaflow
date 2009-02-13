# Makefile für Jucon-Handbuch

MKHOWTO="/home/ctheune/tmp/Python-2.4.2/Doc/tools/mkhowto"

.PHONY: all pdf html clean

all: pdf html

pdf:
	$(MKHOWTO) --pdf -a4 manual.tex
	
html:
	$(MKHOWTO) -s 5 manual.tex

clean:
	rm -rf *.aux *.toc *.log *.out *.lot *.lof *.how
	rm -rf manual.pdf
	rm -rf *.l2h~
	rm -rf manual/

