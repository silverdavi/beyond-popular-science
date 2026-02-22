## Unpopular Science

LaTeX source for *Unpopular Science* (also published as *Beyond Popular Science*) — a book of 50 chapters spanning mathematics, physics, computer science, chemistry, philosophy, and history.

This is not a popular science book. It is not a textbook. It started as a family flight magazine and grew out of control.

Each chapter takes a phenomenon that seems simple on the surface but turns out to be scientifically intricate: why gold is yellow (relativistic quantum mechanics), why apples fall (time dilation, not spatial curvature), how a 4chan post advanced combinatorics, what makes ice slippery (not what you were taught). The treatment sits somewhere between accessible and rigorous — like a sushi-pizza restaurant, excelling at neither.

The book contains errors. Please report them.

### Download

Pre-compiled PDFs are available as a GitHub release:

```bash
curl -L -o BeyondPopularScience.pdf \
  https://github.com/silverdavi/beyond-popular-science/releases/download/latest/main.pdf
```

Or browse all editions and individual chapter PDFs on the [releases page](https://github.com/silverdavi/beyond-popular-science/releases/tag/latest).

### Build from source

**Requirements:** TeX Live (with `lualatex`), Python 3.10+

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Compile the full book:

```bash
python3 utils/compile_realtime.py main.tex
```

This runs two LuaLaTeX passes and produces `main.pdf`.

To compile a subset of chapters:

```bash
python3 utils/generate_chapter_subset.py 1-5,14,29 -o main_subset.tex
python3 utils/compile_realtime.py main_subset.tex
```

### What's inside

50 chapters, each in its own folder (`01_GoldRelativity`, `29_HatMonotile`, `50_Consciousness`, etc.). Every chapter follows the same structure:

1. Title page
2. Visual sidenote page
3. Summary + topic map + quotation
4. Historical context + main exposition
5. One-page technical section (unapologetically tough)

Chapters can be read independently. The essence is accessible to anyone, mostly in the summaries. Some chapters are extremely mathematical.

### Repository layout

```text
├── main.tex                  # Book entry point
├── preamble.tex              # Packages, macros, layout
├── intro.tex, prologue.tex   # Front matter
├── 01_GoldRelativity/        # Chapter folders (01–50)
│   ├── title.tex
│   ├── summary.tex
│   ├── historical.tex
│   ├── main.tex
│   ├── technical.tex
│   └── (quote.tex, topicmap.tex, imagefigure.tex, ...)
├── utils/
│   └── compile_realtime.py
└── release_pdf.sh            # Publish PDFs as GitHub release
```

### Sample visuals

Each chapter opens with a custom visual sidenote page. A few examples:

#### Chapter 1: Relativistic Gold
![Banach-Tarski Sidenote](README_SOURCE/ch01_banach_tarski.png)

Hilbert's Hotel with infinite buses: each passenger *n* on bus *m* is assigned room *(p_n)^m*, where *p_n* is the *n*th prime. No collisions.

#### Chapter 5: Circle and Wheel Etymology
![Indo-European Language Tree](README_SOURCE/ch05_language_tree.png)

The PIE root \**kʷékʷlos* traced through sound shifts to Greek *kyklos*, Sanskrit *chakra*, and English *wheel*.

#### Chapter 10: Solar Fusion
![Solar Fusion Process](README_SOURCE/ch10_solar_fusion.png)

The proton-proton chain, enabled by quantum tunneling through an energy barrier that classical physics says is impassable.

#### Chapter 25: Firefly Bioluminescence
![Firefly Bioluminescence Scales](README_SOURCE/ch25_firefly_scales.png)

From oxyluciferin photon emission at the Ångström scale to a jar of 40 fireflies producing one candle of light.

#### Chapter 27: Planetary Sky Colors
![Atmospheric Scattering](README_SOURCE/ch27_sky_colors.png)

Rayleigh scattering, Martian dust, Titan's tholins, and a Hertzsprung-Russell diagram.

### Troubleshooting

- Activate the virtual environment first: `source venv/bin/activate`
- If LaTeX fails, check `compile_pass1.log`, `compile_pass2.log`, `main.log`
- Make sure `lualatex` is on your PATH

### License

© David H. Silver. All rights reserved.

ISBN: 979-8-9940-2871-1
