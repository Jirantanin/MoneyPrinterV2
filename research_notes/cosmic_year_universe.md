# Cosmic calendar fact-check (Big Bang to ~1 million years ago)

Episode frame: "Cosmic calendar": the age of the universe squeezed into one 365-day year. Big Bang = 1 Jan 00:00:00, now = 31 Dec 24:00:00. The story asks why each step had to wait for the one before it.
Scope: from the Big Bang to about 1 Myr ago. The human story is covered elsewhere.
Researched 2026-10-21. Every excerpt below was read on the page, in the PDF text, or in the paper abstract listed. Paper abstracts were read through the Europe PMC REST API, which returns the publisher's abstract. Excerpts are kept under 15 words.

**Calendar choice: use 13.8 Gyr.** Planck's baseline age is 13.797 ± 0.023 Gyr. With BAO data added it is 13.787 ± 0.020 Gyr (UC01). Both round to 13.8. Swapping 13.8 for 13.787 moves an event fixed in "years ago" by at most about 8 hours: 7.8 h for the Milky Way's disk (13.0 Gyr ago), 2.7 h for Earth, 19 min for the Cambrian, 2–3 min for the asteroid. Events fixed in "years after the Big Bang" move by minutes or less (about 10 min for MoM-z14). Among the headline items, only the Milky Way disk changes date (22 Jan → 21 Jan). Say "13.8 billion years" in the narration.

Scale at 13.8 Gyr (computed): 1 day = 37.81 Myr · 1 hour = 1.575 Myr · 1 minute = 26,256 yr · 1 second = 437.6 yr.

## Calendar table (13.8 Gyr, 365-day year; 13.787 variant for headline items)

Method: `position = (age − years_ago) / age × 365 days`, counted from 1 Jan 00:00:00 of a non-leap year (Python `datetime`, 2001 as the base year). The script was run in the session scratchpad. Times are rounded to the minute.

| # | Step | Best value (range) | Calendar @13.8 | @13.787 | Claim |
|---|---|---|---|---|---|
| 1 | Light elements made (H, He, a little Li) | first ~3 minutes after BB | 1 Jan, a tiny fraction of the first second | same | UC03 |
| 2 | CMB released (universe goes transparent) | 380,000 yr after BB (NASA: 375,000) | **1 Jan 00:14** | 1 Jan 00:14 | UC04 |
| 3 | First stars (Pop III, not yet observed) | model: ~100–250 Myr after BB | **3–7 Jan** (≈6 Jan at 200 Myr) | same ±10 min | UC05 |
| 4 | Most distant confirmed galaxy, MoM-z14 (z = 14.44) | 280 Myr after BB | **8 Jan 09:44** | 8 Jan 09:54 | UC06 |
| 4b | JADES-GS-z14-0 (z = 14.18, the 2024 record) | ~290 Myr after BB | 8 Jan 16:05 | 8 Jan 16:16 | UC06 |
| 5 | Milky Way's old (thick) disk starts forming | 13.0 Gyr ago | **22 Jan 03:50** | 21 Jan 20:03 | UC07 |
| 6 | Gaia-Sausage-Enceladus merger / inner halo assembled | ~11 Gyr ago | 16 Mar 01:23 | 15 Mar 18:48 | UC07 |
| 7 | Solar system's first solids (CAIs) | 4567.30 ± 0.16 Myr ago | **2 Sep 04:45** | 2 Sep 02:01 | UC08 |
| 8 | Earth (age as usually quoted) | 4.54 Gyr ± <1% | **2 Sep 22:05** (1–4 Sep) | 2 Sep 19:22 | UC09 |
| 9 | Moon-forming impact | ≥4.51 Gyr (one dating; younger estimates exist) | 3 Sep 17:08 (or as late as ~7 Sep) | 3 Sep 14:26 | UC10 |
| 10 | Oldest Earth material: Jack Hills zircon | 4.404 ± 0.008 Gyr | **6 Sep 12:25** | 6 Sep 09:47 | UC11 |
| 11 | LUCA (molecular-clock model) | ~4.2 Gyr (4.09–4.33) | 11 Sep (8–14 Sep) | 11 Sep | UC12 |
| 12 | Disputed Isua "stromatolites" | 3.70 Gyr | 25 Sep 03:18 | 25 Sep 01:05 | UC12 |
| 13 | Widely accepted early life: Dresser Fm | ~3.48 Gyr | **30 Sep 22:57** | 30 Sep 20:52 | UC12 |
| 14 | Strelley Pool stromatolite reef | 3.43 Gyr | 2 Oct 06:42 | 2 Oct 04:39 | UC12 |
| 15 | Great Oxidation Event, onset | ~2.43 Gyr (2.46–2.426) | **28 Oct 17:29** (27–28 Oct) | 28 Oct 16:01 | UC13 |
| 16 | Oxygen stays for good | ~2.22 Gyr | 3 Nov 06:47 | 3 Nov 05:27 | UC13 |
| 17 | Oldest eukaryote evidence / multicellular eukaryote | ~1.64 Gyr | **18 Nov 15:00** | 18 Nov 14:00 | UC14 |
| 18 | Decimetre-size multicellular eukaryotes | 1.56 Gyr | 20 Nov 17:44 | 20 Nov 16:48 | UC14 |
| 19 | Algae take over ocean food webs | 659–645 Myr | 14 Dec 14:00–22:30 | 14 Dec | UC14 |
| 20 | Ediacara biota (first large complex organisms) | 571–541 Myr (often "~575") | **16 Dec 21:32** (start) | 16 Dec 21:12 | UC15 |
| 21 | Cambrian begins ("explosion") | 538.8 ± 0.6 Myr | **17 Dec 17:59** | 17 Dec 17:39 | UC16 |
| 22 | Oldest land-plant spores | ~473–471 Myr | 19 Dec 12:23 | 19 Dec 12:06 | UC17 |
| 23 | Oldest air-breathing land animal (millipede) | ~428 or ~423–413 Myr (disputed) | 20 Dec 16:00 – 21 Dec 02:00 | same | UC17 |
| 24 | Oldest tetrapod trackways (Zachelmie) | Eifelian, ~393–388 Myr | 21 Dec ~16:30 | same | UC17 |
| 25 | Earliest dinosaurs | 233.23 ± 0.73 Myr (to ~230) | **25 Dec 19:57** (to ~22:00) | 25 Dec 19:49 | UC18 |
| 26 | Mammal-like teeth (Brasilodon) | 225.42 ± 0.37 Myr | 26 Dec 00:54 | 26 Dec 00:46 | UC19 |
| 27 | Chicxulub impact / K-Pg extinction | 66.04 Myr (ICS boundary 66.00) | **30 Dec 06:05** | 30 Dec 06:02 | UC20 |
| 28 | Mammal richness doubles | within ~100 kyr after impact | 30 Dec ~06:09 (≈4 calendar minutes later) | — | UC21 |
| 29 | Earliest dated stem primate (Purgatorius) | ~105–139 kyr after K-Pg (~65.9 Myr) | 30 Dec 06:09 | 30 Dec 06:07 | UC21 |
| 30 | Human–chimp lineages split | fossils 6–7 Myr; genetics ≥7–8 Myr | **31 Dec ~19:30** (18:55–20:11) | same | UC22 |
| 31 | Hand-off to the human-story researcher | 1 Myr ago | 31 Dec 23:22 | 31 Dec 23:22 | — |

For the hand-off, computed for comparison only: Sagan's "humans at 10:30 PM" on his 15-Gyr calendar works out to about 2.57 Myr ago. On a 13.8-Gyr calendar that age falls at 31 Dec 22:22. *Homo sapiens* at ~300 kyr falls at 23:48:34. The human-story file should check its own numbers.

## Sources

| ID | Title | Publisher | URL | Accessed |
|---|---|---|---|---|
| U01 | Planck Collaboration, "Planck 2018 results. VI. Cosmological parameters", A&A 641, A6 (2020) | arXiv:1807.06209 (PDF text) | https://arxiv.org/pdf/1807.06209 | 2026-10-21 |
| U02 | "Planck CMB" (image page, 2013) | ESA | https://www.esa.int/ESA_Multimedia/Images/2013/03/Planck_CMB | 2026-10-21 |
| U03 | "Planck's view of the cosmic microwave background" (17 Jul 2018) | ESA Science & Technology | https://sci.esa.int/web/planck/-/60500-plancks-view-of-the-cosmic-microwave-background | 2026-10-21 |
| U04 | WMAP mission overview | NASA Science | https://science.nasa.gov/mission/wmap/wmap-overview/ | 2026-10-21 |
| U05 | Fields, Molaro & Sarkar, "24. Big Bang Nucleosynthesis", Review of Particle Physics 2025 | Particle Data Group (LBNL) | https://pdg.lbl.gov/2025/reviews/rpp2025-rev-bbang-nucleosynthesis.pdf | 2026-10-21 |
| U06 | Webb: Early Universe | NASA Science | https://science.nasa.gov/mission/webb/early-universe/ | 2026-10-21 |
| U07 | Stars (Star Basics) | NASA Science | https://science.nasa.gov/universe/stars/ | 2026-10-21 |
| U08 | "NASA Missions Catch First Light from a Gravitational-Wave Event" (Oct 2017) | NASA | https://www.nasa.gov/news-release/nasa-missions-catch-first-light-from-a-gravitational-wave-event/ | 2026-10-21 |
| U09 | Visbal, Hazlett & Bryan, "LAP1-B is the First Observed System Consistent with Theoretical Predictions for Population III Stars" (accepted ApJL) | arXiv:2508.03842 | https://arxiv.org/abs/2508.03842 | 2026-10-21 |
| U10 | Carniani et al., "Spectroscopic confirmation of two luminous galaxies at z∼14", Nature 633, 318 (2024) | arXiv:2405.18485 | https://arxiv.org/abs/2405.18485 | 2026-10-21 |
| U11 | Schouws et al., "Detection of [OIII]88μm in JADES-GS-z14-0 at z=14.1793" (ApJ) | arXiv:2409.20549 | https://arxiv.org/abs/2409.20549 | 2026-10-21 |
| U12 | Naidu et al., "A Cosmic Miracle: A Remarkably Luminous Galaxy at z_spec=14.44 Confirmed with JWST" (Open Journal of Astrophysics) | arXiv:2505.11263 | https://arxiv.org/abs/2505.11263 | 2026-10-21 |
| U13 | "Webb finds most distant known galaxy" (JADES-GS-z14-0 pullout, image jades4) | ESA/Webb | https://esawebb.org/images/jades4/ | 2026-10-21 |
| U14 | "COSMOS Field MoM-z14 Galaxy (NIRCam pullout image)", release weic2603, 28 Jan 2026 | ESA/Webb | https://esawebb.org/images/weic2603a/ | 2026-10-21 |
| U15 | Usage of ESA/Hubble/Webb images and videos | ESA/Webb | https://esawebb.org/copyright/ | 2026-10-21 |
| U16 | Copyright | STScI | https://www.stsci.edu/copyright | 2026-10-21 |
| U17 | List of the most distant astronomical objects (finder only) | Wikipedia | https://en.wikipedia.org/wiki/List_of_the_most_distant_astronomical_objects | 2026-10-21 |
| U18 | Xiang & Rix, "A time-resolved picture of our Milky Way's early formation history", Nature (2022) | arXiv:2203.12110 | https://arxiv.org/abs/2203.12110 | 2026-10-21 |
| U19 | Connelly et al., "The absolute chronology and thermal processing of solids in the solar protoplanetary disk", Science 338 (2012) | Europe PMC (PMID 23118187) | https://europepmc.org/article/MED/23118187 | 2026-10-21 |
| U20 | Geologic Time: Age of the Earth | USGS | https://pubs.usgs.gov/gip/geotime/age.html | 2026-10-21 |
| U21 | Barboni et al., "Early formation of the Moon 4.51 billion years ago", Science Advances (2017) | Europe PMC (PMID 28097222) | https://europepmc.org/article/MED/28097222 | 2026-10-21 |
| U22 | Wilde et al., "Evidence from detrital zircons for the existence of continental crust and oceans on the Earth 4.4 Gyr ago", Nature 409 (2001) | Europe PMC (PMID 11196637) | https://europepmc.org/article/MED/11196637 | 2026-10-21 |
| U23 | "Oldest bit of crust firms up idea of a cool early Earth" (23 Feb 2014) | UW–Madison College of Letters & Science | https://ls.wisc.edu/news/oldest-bit-of-crust-firms-up-idea-of-a-cool-early-earth | 2026-10-21 |
| U24 | Bell et al., "Potentially biogenic carbon preserved in a 4.1 billion-year-old zircon", PNAS (2015) | Europe PMC (PMID 26483481) | https://europepmc.org/article/MED/26483481 | 2026-10-21 |
| U25 | Moody et al., "The nature of the last universal common ancestor and its impact on the early Earth system", Nat. Ecol. Evol. (2024) | Europe PMC (PMID 38997462) | https://europepmc.org/article/MED/38997462 | 2026-10-21 |
| U26 | Dodd et al., "Evidence for early life in Earth's oldest hydrothermal vent precipitates", Nature (2017) | Europe PMC (PMID 28252057) | https://europepmc.org/article/MED/28252057 | 2026-10-21 |
| U27 | Tashiro et al., "Early trace of life from 3.95 Ga sedimentary rocks in Labrador, Canada", Nature (2017) | Europe PMC (PMID 28959955) | https://europepmc.org/article/MED/28959955 | 2026-10-21 |
| U28 | Nutman et al., "Rapid emergence of life shown by discovery of 3,700-million-year-old microbial structures", Nature (2016) | Europe PMC (PMID 27580034) | https://europepmc.org/article/MED/27580034 | 2026-10-21 |
| U29 | Allwood et al., "Reassessing evidence of life in 3,700-million-year-old rocks of Greenland", Nature (2018) | Europe PMC (PMID 30333621) | https://europepmc.org/article/MED/30333621 | 2026-10-21 |
| U30 | Djokic et al., "Earliest signs of life on land preserved in ca. 3.5 Ga hot spring deposits", Nat. Commun. (2017) | Europe PMC (PMID 28486437) | https://europepmc.org/article/MED/28486437 | 2026-10-21 |
| U31 | Noffke et al., "Microbially induced sedimentary structures ... ca. 3.48 billion-year-old Dresser Formation", Astrobiology (2013) | Europe PMC (PMID 24205812) | https://europepmc.org/article/MED/24205812 | 2026-10-21 |
| U32 | Allwood et al., "Stromatolite reef from the Early Archaean era of Australia", Nature (2006) | Europe PMC (PMID 16760969) | https://europepmc.org/article/MED/16760969 | 2026-10-21 |
| U33 | Gumsley et al., "Timing and tempo of the Great Oxidation Event", PNAS (2017) | Europe PMC (PMID 28167763) | https://europepmc.org/article/MED/28167763 | 2026-10-21 |
| U34 | Poulton et al., "A 200-million-year delay in permanent atmospheric oxygenation", Nature (2021) | Europe PMC (PMID 33782617) | https://europepmc.org/article/MED/33782617 | 2026-10-21 |
| U35 | Kadoya et al., "Mantle data imply a decline of oxidizable volcanic gases could have triggered the Great Oxidation", Nat. Commun. (2020) | Europe PMC (PMID 32487988) | https://europepmc.org/article/MED/32487988 | 2026-10-21 |
| U36 | S. Perkins, "The iron record of Earth's oxygen" (5 Jun 2009) | Science News | https://www.sciencenews.org/article/iron-record-earth%E2%80%99s-oxygen | 2026-10-21 |
| U37 | Miao et al., "1.63-billion-year-old multicellular eukaryotes from the Chuanlinggou Formation in North China", Sci. Adv. (2024) | Europe PMC (PMID 38266082) | https://europepmc.org/article/MED/38266082 | 2026-10-21 |
| U38 | Brocks et al., "Lost world of complex life and the late rise of the eukaryotic crown", Nature (2023) | Europe PMC (PMID 37286610) | https://europepmc.org/article/MED/37286610 | 2026-10-21 |
| U39 | Zhu et al., "Decimetre-scale multicellular eukaryotes from the 1.56-billion-year-old Gaoyuzhuang Formation", Nat. Commun. (2016) | Europe PMC (PMID 27186667) | https://europepmc.org/article/MED/27186667 | 2026-10-21 |
| U40 | Brocks et al., "The rise of algae in Cryogenian oceans and the emergence of animals", Nature (2017) | Europe PMC (PMID 28813409) | https://europepmc.org/article/MED/28813409 | 2026-10-21 |
| U41 | Bobrovskiy et al., "Ancient steroids establish the Ediacaran fossil Dickinsonia as one of the earliest animals", Science (2018) | Europe PMC (PMID 30237355) | https://europepmc.org/article/MED/30237355 | 2026-10-21 |
| U42 | International Chronostratigraphic Chart v2026/06 (PDF text) | International Commission on Stratigraphy | https://stratigraphy.org/ICSchart/ChronostratChart2026-06.pdf | 2026-10-21 |
| U43 | Morris et al., "The timescale of early land plant evolution", PNAS (2018) | Europe PMC (PMID 29463716) | https://europepmc.org/article/MED/29463716 | 2026-10-21 |
| U44 | Rubinstein et al., "Early Middle Ordovician evidence for land plants in Argentina", New Phytologist (2010) | Europe PMC (PMID 20731783) | https://europepmc.org/article/MED/20731783 | 2026-10-21 |
| U45 | Brookfield, Catlos & Garza, "Reconciling Divergent Ages for the Oldest Recorded Air-Breathing Land Animal, the Millipede, Pneumodesmus newmani..." (preprint 2025) | Preprints.org via Europe PMC | https://doi.org/10.20944/preprints202502.1525.v1 | 2026-10-21 |
| U46 | Niedźwiedzki et al., "Tetrapod trackways from the early Middle Devonian period of Poland", Nature (2010) | Europe PMC (PMID 20054388) | https://europepmc.org/article/MED/20054388 | 2026-10-21 |
| U47 | Langer, Ramezani & Da Rosa, "U-Pb age constraints on dinosaur rise from south Brazil", Gondwana Research 57, 133–140 (2018) | FAPESP Biblioteca Virtual record | https://bv.fapesp.br/en/publicacao/150065/u-pb-age-constraints-on-dinosaur-rise-from-south-brazil | 2026-10-21 |
| U48 | Martinez et al., "A basal dinosaur from the dawn of the dinosaur era in southwestern Pangaea", Science (2011) | Europe PMC (PMID 21233386) | https://europepmc.org/article/MED/21233386 | 2026-10-21 |
| U49 | Cabreira et al., "Diphyodont tooth replacement of Brasilodon...", J. Anatomy (2022) | Europe PMC (PMID 36065514) | https://europepmc.org/article/MED/36065514 | 2026-10-21 |
| U50 | Renne et al., "Time scales of critical events around the Cretaceous-Paleogene boundary", Science 339 (2013) | Europe PMC (PMID 23393261) | https://europepmc.org/article/MED/23393261 | 2026-10-21 |
| U51 | "Date of dinosaur extinction fixed more accurately than ever before" (Feb 2013) | University of Glasgow news | https://www.gla.ac.uk/news/archiveofnews/2013/february/headline_263831_en.html | 2026-10-21 |
| U52 | Schulte et al., "The Chicxulub asteroid impact and mass extinction at the Cretaceous-Paleogene boundary", Science (2010) | Europe PMC (PMID 20203042) | https://europepmc.org/article/MED/20203042 | 2026-10-21 |
| U53 | Lyson et al., "Exceptional continental record of biotic recovery after the Cretaceous-Paleogene mass extinction", Science (2019) | Europe PMC (PMID 31649141) | https://europepmc.org/article/MED/31649141 | 2026-10-21 |
| U54 | Wilson Mantilla et al., "Earliest Palaeocene purgatoriids and the initial radiation of stem primates", R. Soc. Open Sci. (2021) | Europe PMC (PMID 33972886) | https://europepmc.org/article/MED/33972886 | 2026-10-21 |
| U55 | Brunet et al., "A new hominid from the Upper Miocene of Chad, Central Africa", Nature (2002) | Europe PMC (PMID 12110880) | https://europepmc.org/article/MED/12110880 | 2026-10-21 |
| U56 | Langergraber et al., "Generation times in wild chimpanzees and gorillas suggest earlier divergence times...", PNAS (2012) | Europe PMC (PMID 22891323) | https://europepmc.org/article/MED/22891323 | 2026-10-21 |
| U57 | "Excerpts: The Dragons of Eden" (review/excerpt page by A. Mukerjee, 2009) | IIT Kanpur (personal pages) | https://cse.iitk.ac.in/users/amit/books/sagan-1977-dragons-of-eden.html | 2026-10-21 |
| U58 | The Dragons of Eden (finder only) | Wikipedia | https://en.wikipedia.org/wiki/The_Dragons_of_Eden | 2026-10-21 |
| U59 | Cosmic Calendar (finder only) | Wikipedia | https://en.wikipedia.org/wiki/Cosmic_Calendar | 2026-10-21 |
| U60 | A. P. Manuel, "The Dragons of Eden – Chapter 1: The Cosmic Calendar" (blog, 2017) | The Pensive Reverie | https://thepensivereverie.com/2017/01/18/the-dragons-of-eden-chapter-1-the-cosmic-calendar/ | 2026-10-21 |
| U61 | Terms and conditions of use of images and videos | ESA | https://www.esa.int/ESA_Multimedia/Terms_and_conditions_of_use_of_images_and_videos_available_on_the_esa_website | 2026-10-21 |
| U62 | NASA Images and Media Usage Guidelines | NASA Brand Center | https://www.nasa.gov/nasa-brand-center/images-and-media/ | 2026-10-21 |
| U63 | PIA03379 "Shaded Relief with Height as Color, Yucatan Peninsula, Mexico" | NASA/JPL Photojournal | https://science.nasa.gov/photojournal/shaded-relief-with-height-as-color-yucatan-peninsula-mexico | 2026-10-21 |
| U64 | "Stromatolites of Australia" (image page) | USGS | https://www.usgs.gov/media/images/stromatolites-australia | 2026-10-21 |
| U65 | Wikimedia Commons file metadata (licence/author via Commons API; files listed in Visuals) | Wikimedia Commons | https://commons.wikimedia.org/ | 2026-10-21 |
| U66 | "The James Webb Space Telescope has found the most distant galaxy ever seen... Again." (14 Sep 2026) | BBC Sky at Night Magazine | https://www.skyatnightmagazine.com/news/webb-galaxy-mom-z14 | 2026-10-21 |

Not opened or not relied on: the Science full text of Renne et al. 2013, which a search snippet says gives 66.043 ± 0.011 Ma for the extinction; I could not open it, see UC20. *The Dragons of Eden* itself: the Internet Archive copies are borrow-only (HTTP 401). The worldclass.net excerpt of the chapter (expired certificate). The UNESCO Mistaken Point page (HTTP 403). The Science Advances page for Barboni (403; the abstract came from Europe PMC instead). Valley et al. 2014, *Nature Geoscience* (not indexed in Europe PMC; the UW news release U23 was used instead).

## Claims

### 1. The age of the universe and the calendar scale

**UC01**: Planck 2018 gives the age of the universe in base ΛCDM as **13.797 ± 0.023 Gyr** for the baseline TT,TE,EE+lowE+lensing fit. Adding BAO gives **13.787 ± 0.020 Gyr**.
- Best value: 13.8 Gyr (both fits round to it). Range: about 13.77–13.82 Gyr (1σ, both fits).
- Sources: U01
- Excerpt (U01, Table 2 caption): "Our baseline results are based on Planck TT,TE,EE+lowE+lensing"
- Excerpt (U01, Table 2, Age row, last two columns): "13.797 ± 0.023 | 13.787 ± 0.020"
- Locator: Table 2, row "Age [Gyr]", columns "TT,TE,EE+lowE+lensing" and "+BAO".
- Confidence: **verified** (read in the PDF text)
- Safe wording: "about 13.8 billion years". The draft's "13.787 ± 0.020" is the *+BAO* column, not Planck's baseline. If a number is shown on screen, label it "Planck 2018 + BAO". This is a model-dependent age (it assumes ΛCDM). The Hubble-tension debate doesn't change the 13.8 figure enough to matter at calendar scale. Don't say it was "measured directly".

**UC02** (Sagan's original): Carl Sagan introduced the Cosmic Calendar in *The Dragons of Eden* (Random House, 1977). He compressed **~15 billion years** into one year and put the first humans at about **10:30 PM on 31 December**. He used the calendar again in *Cosmos* (1980).
- Sources: U57, U58, U60; U59 as a finder only
- Excerpt (U57, review/excerpt page): "Taking the age of the universe as 15 bn years."
- Excerpt (U58, Synopsis): "men and women originate at 10:30 P.M. on New Year's Eve"
- Excerpt (U60, blog): "Sagan states this to be 15 billion years old."
- Locator: U58 places the calendar in chapter 2 and U60's title says chapter 1. **The chapter number is unresolved.**
- Confidence: **partly verified, secondary sources only.** The book itself could not be opened. U57 is inconsistent: its own timeline lists *Homo sapiens* at 23:54. The *Cosmos* 1980 use rests on Wikipedia (U59) and was not checked against the episode.
- Why old versions differ: Sagan scaled 15 Gyr, so one of his calendar hours is about 1.71 Myr, not 1.575 Myr. His 10:30 PM equals about 2.57 Myr ago, which matches the earliest *Homo*, not *Homo sapiens*. Modern versions also use newer dates for Earth, life and fossils.
- Safe wording: "The idea comes from Carl Sagan, in his 1977 book *The Dragons of Eden*. In his day the universe was thought to be about 15 billion years old, so his dates differ a little from ours." Don't quote or paraphrase his text closely, and don't name a chapter.

### 2. The early universe: light, first stars, first galaxies

**UC03**: Only the lightest nuclei (hydrogen, deuterium, helium, a trace of lithium) formed in the first few minutes. Everything heavier had to wait for stars.
- Sources: U05, U07, U08
- Excerpt (U05, §24.1): "synthesized at the end of the first three minutes"
- Excerpt (U07, star life cycle): "For the largest stars, this chain continues until silicon fuses into iron."
- Excerpt (U07): "will enrich future molecular clouds and become incorporated into the next generation of stars."
- Excerpt (U08, GW170817): "may be the universe's dominant source for many of the heaviest elements"
- Locator: U05 §24.1 Introduction; U07 sections on star death/supernovae; U08 para. on kilonova (event of 17 Aug 2017).
- Confidence: **verified**
- **The causal link for the story:** the Big Bang made the light elements only. Stars fuse them up to iron. Supernovae and, for many of the heaviest elements (gold, platinum), neutron-star mergers make the rest and scatter it into new gas clouds. Rocky planets and life need the carbon, oxygen, silicon and iron that earlier generations of stars made. So Earth *had* to come late.
- Safe wording: "Every atom heavier than helium (apart from a little lithium) was forged in stars or in stellar explosions and collisions." U08 says "may be the dominant source", so say neutron-star collisions are "a major source" of gold. Don't say they are "the only source". Don't say "supernovae make all heavy elements".

**UC04**: The cosmic microwave background was released about **380,000 years** after the Big Bang (NASA says ~375,000). Planck's redshift of last scattering is z* = 1089.92 ± 0.25 (baseline).
- Sources: U02, U03, U04, U01
- Excerpt (U02/U03, description): "imprinted on the sky when the Universe was just 380 000 years old"
- Excerpt (U04, WMAP overview): "This microwave radiation was released approximately 375,000 years after the birth of the universe."
- Locator: U01 Table 2, row z*. U02 and U03, image description. U04, mission overview text.
- Confidence: **verified**
- Calendar: 1 Jan 00:14. Safe wording: "about 380,000 years after the Big Bang, at a quarter past midnight on 1 January". Don't call it "the first light". It is the oldest light we can see. Don't call it a "photo of the Big Bang".

**UC05**: First stars (Population III, made of almost pure hydrogen and helium) have **not been directly confirmed**. Models put them within the first few hundred million years. The best candidate, LAP1-B, is at z ≈ 6.6, which is much later than the first stars.
- Best value: roughly 100–250 Myr after the Big Bang (my estimate from the sources, not a measured value). NASA's Webb page graphic says 200–400 Myr. But galaxies with plenty of stars already existed by 280–300 Myr (UC06), so the earliest stars must have formed before that.
- Sources: U06, U09, U10
- Excerpt (U06, graphic): "First Stars form 200–400 million years after the big bang."
- Excerpt (U09, abstract): "LAP1-B was found at the redshift theoretically expected"
- Locator: U06, the timeline graphic and the "Cosmic Dawn" text; U09 abstract.
- Confidence: **uncertain (model-based)**
- Calendar: about 3–7 January. Safe wording: "the first stars probably lit up within the first week of January. Nobody has seen them directly yet." Don't call LAP1-B "the first stars found". It is a candidate that is "consistent with" the predictions.

**UC06**: The most distant spectroscopically confirmed galaxy, as of 2026-10-21, is **MoM-z14 at z = 14.44**, seen **280 Myr** after the Big Bang (Naidu et al.; ESA/Webb release 28 Jan 2026). It took the record from **JADES-GS-z14-0**, now refined to z = 14.18 by ALMA (it was 14.32 from NIRSpec in 2024), at ~290–300 Myr.
- Sources: U12, U14, U10, U11, U13; U66 and U17 as currency checks
- Excerpt (U12, abstract): "expands the observational frontier to a mere 280 million years after the Big Bang"
- Excerpt (U10, abstract): "luminous galaxies were already in place 300 million years after the Big Bang"
- Excerpt (U11, abstract): "The ALMA detection yields a spectroscopic redshift of z=14.1793±0.0007"
- Excerpt (U13, description): "observed only 290 million years after the big bang"
- Locator: abstracts; U14 release text (28 Jan 2026).
- Confidence: **verified** for the values. The record holds as of 14 Sep 2026 per U66, and U17 lists no newer confirmed object. Photometric candidates at z > 15 (up to z ≈ 25) are **unconfirmed**.
- Calendar: 8 Jan 09:44 (MoM-z14) and 8 Jan 16:05 (GS-z14-0). Safe wording: "By 8 January, galaxies bright enough for Webb to see already existed." Say "the most distant galaxy confirmed so far". Records fall often, so check again right before publishing. Don't present z ≈ 25 candidates as discoveries.

**UC07**: The Milky Way's old (thick) disk began forming about **13 Gyr ago** (~0.8 Gyr after the Big Bang). The inner halo was assembled about 2 Gyr later, around the Gaia-Sausage-Enceladus merger (~11 Gyr ago).
- Sources: U18
- Excerpt (U18, abstract): "the formation of the Galactic old (thick) disk started 13 Gyr ago"
- Excerpt (U18, abstract): "when the Gaia-Sausage-Enceladus satellite merged with our Galaxy"
- Locator: abstract (Nature 2022 / arXiv:2203.12110)
- Confidence: **verified** for 13 Gyr. ~11 Gyr for the merger is my reading of the "two Gigayears earlier" phrasing in the abstract, so treat it as **approximate**.
- Calendar: 22 Jan (21 Jan with 13.787). Safe wording: "our galaxy started building its disk in late January". Avoid "the Milky Way was born on 22 January". Its oldest halo stars may be older, and "birth" isn't one event.

### 3. Sun, Earth, Moon, oldest crystal

**UC08**: The solar system's first solids, the calcium-aluminium-rich inclusions (CAIs) in meteorites, date to **4567.30 ± 0.16 Myr**. This is the standard "birth of the solar system" age.
- Sources: U19
- Excerpt (U19, abstract): "an age of 4567.30 ± 0.16 million years (My)"
- Confidence: **verified**
- Calendar: 2 Sep 04:45. Safe wording: "the Sun and its planets formed about 4.57 billion years ago, at the start of September." This dates the first solids. The Sun itself ignited at about the same time.

**UC09**: Earth's commonly quoted age is **4.54 billion years**, uncertain by less than 1%.
- Sources: U20, U22
- Excerpt (U20): "of 4.54 billion years with an uncertainty of less than 1 percent"
- Confidence: **verified**
- Calendar: 2 Sep 22:05, with a ±1% range of 1–4 Sep. **The draft's "Earth ≈ early September" is confirmed.** Safe wording: "early September". Earth grew over tens of millions of years, so it has no single birthday. Don't say "Earth formed on 2 September" as if exact.

**UC10**: The Moon formed within about 60 Myr of the solar system's start. One zircon-based study gives **≥4.51 Gyr**.
- Sources: U21
- Excerpt (U21, abstract): "indicating the formation of the Moon within the first ~60 million years"
- Confidence: **verified for this study. The Moon's age is still debated:** some studies argue for ~4.35–4.45 Gyr, which I did not check here.
- Calendar: 3 Sep (on the young-Moon view, as late as about 7 Sep). Safe wording: "a few days after Earth formed, a Mars-sized body hit it and the Moon formed from the debris". Don't give a precise date. U21 dates lunar crust differentiation and says nothing about the impactor, so the giant-impact *mechanism* is the standard model but is not proven by this source.

**UC11**: The oldest known piece of Earth is a detrital zircon from the Jack Hills, Western Australia, dated **4,404 ± 8 Myr**. Its oxygen isotopes suggest liquid water and crust by then. The 2014 atom-probe study confirmed the "at least 4.4 Gyr" age.
- Sources: U22, U23
- Excerpt (U22, abstract): "a detrital zircon with an age as old as 4,404+/-8 Myr"
- Excerpt (U22, abstract): "the earliest evidence for continental crust and oceans on the Earth"
- Excerpt (U23): "Earth's crust first formed at least 4.4 billion years ago"
- Confidence: **verified**
- Calendar: 6 Sep 12:25. Safe wording: "a grain smaller than a grain of sand" and "the oldest known *piece* of Earth". **It is not the oldest rock.** The oldest rocks are about 4.0 Gyr, in Canada. The "oceans" reading is an inference from isotopes, so say "hints of water".

### 4. Life: early, but simple for a very long time

**UC12**: **Safe statement: convincing evidence of life goes back at least about 3.5 Gyr** (Dresser Formation, ~3.48 Gyr; Strelley Pool stromatolite reef, 3.43 Gyr). Older claims are **contested**: Isua "stromatolites" at 3.70 Gyr (later disputed as non-biological), Labrador graphite at >3.95 Gyr, Nuvvuagittuq "microfossils" at ≥3.77 and possibly 4.28 Gyr, and carbon in a 4.1-Gyr Jack Hills zircon. A molecular-clock model puts LUCA at ~4.2 Gyr (4.09–4.33).
- Sources: U30, U31, U32, U28, U29, U26, U27, U24, U25
- Excerpt (U30, abstract): "some of Earth's earliest convincing evidence of life"
- Excerpt (U31, abstract): "Complex mat-forming microbial communities likely existed almost 3.5 billion years ago."
- Excerpt (U32, abstract): "The 3,430-million-year-old Strelley Pool Chert (SPC)"
- Excerpt (U28, abstract, claim): "3,700-Myr-old metacarbonate rocks in the ISB that contain 1-4-cm-high stromatolites"
- Excerpt (U29, abstract, rebuttal): "a non-biological, post-depositional origin for the structures"
- Excerpt (U26, abstract): "at least 3,770 million and possibly 4,280 million years old"
- Excerpt (U24, abstract): "the microfossil record only extends to ∼ 3.5 billion years (Ga)"
- Excerpt (U25, abstract): "LUCA lived ~4.2 Ga (4.09-4.33 Ga)"
- Confidence: **verified that the controversy exists, and verified for the ~3.48–3.43 Gyr evidence.** The older claims are **contested**. LUCA is a **model**.
- Calendar: life is clearly there by 30 Sep – 2 Oct. Contested hints go back to mid-September. LUCA (model) falls around 11 Sep.
- Safe wording: "By the end of September at the latest, and maybe earlier, Earth already had life. That is quick, only a few weeks after Earth formed." On the older claims: "some scientists see traces even older than that, but it's still debated". **Myth to avoid:** "life took billions of years to start". It started early. What took billions of years was the move from single cells to complex life. Don't present the Isua stromatolites as fact.

**UC13**: The **Great Oxidation Event** began **~2.46–2.43 Gyr** ago. Oxygen then went up and down for about 200 Myr and became permanent only about **2.22 Gyr** ago. Oxygen-making photosynthesis existed well before this, but the atmosphere stayed anoxic "for hundreds of millions of years". One leading explanation is that reducing volcanic gases (and dissolved iron, recorded in banded iron formations) used up the oxygen.
- Best value: onset ~2.43 Gyr (range 2.46–2.426); permanent ~2.22 Gyr. The draft's "2.4–2.3" is out of date. Say "about 2.4 billion years ago".
- Sources: U33, U34, U35, U36
- Excerpt (U33, abstract): "the onset of the GOE occurred between ca. 2,460 and 2,426 Ma"
- Excerpt (U34, abstract): "with the Lomagundi carbon isotope excursion at about 2.22 billion years ago"
- Excerpt (U35, abstract): "the atmosphere remained anoxic for hundreds of millions of years"
- Excerpt (U35, abstract): "reducing Archean volcanic gases could have prevented atmospheric O2 from accumulating"
- Excerpt (U36): "accumulated long before Earth's atmosphere became thoroughly oxygenated"
- Confidence: **verified** for the dates. The *cause* of the delay is **an active hypothesis**: U35 shows the volcanic-gas sink "could have" done it, and other explanations exist. When cyanobacteria first appeared is **not established** here.
- Calendar: onset 28 Oct; permanent oxygen 3 Nov.
- Safe wording: "Microbes were making oxygen long before late October. But the iron in the sea and the gases from volcanoes kept soaking it up, until those 'sponges' ran low." Don't say "cyanobacteria appeared, then oxygen rose straight away", or "BIFs prove oxygen". U36 says some formed before free oxygen.

**UC14**: The oldest unambiguous eukaryote evidence is **~1.65 Gyr**. Multicellular eukaryotes appear by **~1.635 Gyr** (Qingshania) and decimetre-sized ones by **1.56 Gyr**. Molecular clocks put the last eukaryotic common ancestor at **~1.2 to >1.8 Gyr**. Biomarkers show a "protosterol biota" from ≥1.64 Gyr, but modern-type eukaryotes became ecologically important only in the Tonian (1.0–0.72 Gyr). Algae took over ocean food webs **659–645 Myr** ago.
- Sources: U37, U38, U39, U40
- Excerpt (U37, abstract): "not much younger than those containing the oldest unambiguous evidence of eukaryotes"
- Excerpt (U37, abstract): "the ~1635-million-year-old Chuanlinggou Formation"
- Excerpt (U38, abstract): "had already emerged between around 1,200 and more than 1,800 million years ago"
- Excerpt (U39, abstract): "at least a billion years before the Cambrian Explosion"
- Excerpt (U40, abstract): "bacteria were the only notable primary producers in the oceans before the Cryogenian"
- Confidence: **verified** for these values. The age of the "oldest unambiguous eukaryote" (~1.65 Gyr) is implied by U37; I did not open a paper dating it directly. The draft's "~1.6–1.8 Gyr" is fine for the clock range, but the fossils I verified are ~1.65–1.56 Gyr.
- Calendar: about 18–20 Nov. Algae take over on 14 Dec.
- Safe wording: "cells with a nucleus show up around mid-November, but for a very long time they stay small and rare". Don't say "complex life began 1.6 billion years ago". Simple multicellularity, yes; animals, no.

### 5. Animals, land, dinosaurs, mammals

**UC15**: The Ediacara biota, the first large complex organisms, spans about **571–541 Myr**. Lipid biomarkers show that *Dickinsonia* was an animal.
- Sources: U41
- Excerpt (U41, abstract): "The enigmatic Ediacara biota (571 million to 541 million years ago)"
- Excerpt (U41, abstract): "the oldest confirmed macroscopic animals in the rock record"
- Confidence: **verified** for the 571–541 range. The often-quoted **~575 Myr** for the oldest Avalon (Mistaken Point) fossils is **unverified** (the UNESCO page returned 403). Use "about 570 million years".
- Calendar: 16 Dec 21:30 (571 Myr). With 575, 16 Dec ~19:00.
- Note: U41 uses 541 as the end because it is a 2018 paper. The ICS now gives 538.8 (UC16).

**UC16**: The Cambrian Period starts at **538.8 ± 0.6 Myr** (ICS chart v2026/06, unchanged from v2024/12).
- Sources: U42
- Excerpt (U42, chart, Cambrian base): "538.8 ±0.6"
- Locator: chart, Phanerozoic column, base of the Fortunian/Terreneuvian
- Confidence: **verified** (read in the PDF text). The draft's value is right, but the chart's uncertainty is ±0.6, not ±0.2.
- Calendar: 17 Dec 17:59. Safe wording: "the Cambrian explosion, on the evening of 17 December". The "explosion" played out over roughly 20 Myr (about half a calendar day), and the earliest animals came before it (UC15). Don't say "animals appeared suddenly in the Cambrian".

**UC17**: Land and the first walkers:
- The oldest land-plant spores are **~473–471 Myr** (Argentina). A molecular clock puts the origin of land plants in the **Cambrian**.
- The oldest recorded air-breathing land animal is the millipede *Pneumodesmus*. Its age is **disputed**: late Wenlock (~428 Myr) or Přídolí–Lochkovian (~423–413 Myr per the ICS chart: Přídolí base 422.7, Pragian base 413.02), and the 2025 review argues for the younger one.
- Tetrapod trackways at Zachelmie, Poland are Eifelian (early Middle Devonian, ~393–388 Myr per ICS). That is about 18 Myr older than the oldest tetrapod body fossils.
- Sources: U44, U43, U45, U46, U42
- Excerpt (U44, abstract): "are currently the earliest evidence of plants on land"
- Excerpt (U43, abstract): "a Cambrian origin of Embryophyta is recovered with highest probability"
- Excerpt (U45, abstract): "the first recorded undoubtedly air-breathing land animal"
- Excerpt (U45, abstract): "firmly dates the millipede-bearing strata as Pridoli-Lochkovian"
- Excerpt (U46, abstract): "approximately 18 million years older than the earliest tetrapod body fossils"
- Confidence: **verified**, but U45 is a **preprint**, so treat the millipede age as open.
- Calendar: plants on land by 19 Dec, the millipede around 20–21 Dec, the first four-legged tracks on 21 Dec.
- Safe wording: "Plants went ashore first, then small animals such as millipedes, then our fish ancestors around 21 December." Don't give one exact "first land animal" date.

**UC18**: The earliest dinosaurs date to about **233–230 Myr** (Late Triassic, Carnian). The Santa Maria Formation in Brazil is 233.23 ± 0.73 Myr. In Ischigualasto, Argentina, early dinosaurs were dominant small herbivores and carnivores by about 230 Myr.
- Sources: U47, U48
- Excerpt (U47, abstract): "weighted mean Pb-206/U-238 date of 233.23 +/- 0.73 Ma"
- Excerpt (U47, abstract): "Triassic dinosaurs from South Brazil are considered as some of the oldest known worldwide."
- Excerpt (U48, abstract): "Some 230 million years ago in the Late Triassic (mid Carnian)"
- Confidence: **verified**
- Calendar: 25 Dec, about 20:00–22:00. Nice beat: **dinosaurs arrive on Christmas evening**. Safe wording: "Christmas night". Don't say "the very first dinosaur". The oldest known ones are about this age, and their ancestors are older.

**UC19**: Mammals: the lineage leading to mammals had mammal-like traits by the Late Triassic. *Brasilodon*, a non-mammal eucynodont living alongside early dinosaurs, already had mammal-style tooth replacement by **225.42 ± 0.37 Myr**. Mammals then lived for more than 150 Myr in the dinosaurs' shadow.
- Sources: U49, U48
- Excerpt (U49, abstract): "to the Norian (225.42 ± 0.37 myr)"
- Excerpt (U49, abstract): "as contemporary of the oldest known dinosaurs"
- Confidence: **verified for *Brasilodon*.** The date of the first true (crown) mammals was **not checked**. Definitions vary: mammaliaforms are around 205 Myr+, crown mammals are later. Avoid giving one.
- Calendar: mammal relatives on 26 Dec around 01:00, so **mammals and dinosaurs arrive on almost the same night**.
- Safe wording: "our mammal relatives were already here when the dinosaurs were, but they stayed small, mostly night-active animals". **Myth to avoid:** "mammals evolved after the dinosaurs died". The "small and nocturnal" part is the standard picture, but no source here was checked for it, so phrase it as "mostly small".

**UC20**: The Chicxulub impact caused the end-Cretaceous mass extinction. The ICS boundary age is **66.00 Myr**. Ar/Ar dating puts the impact at **66.038 Myr** (±~0.011 Myr), synchronous with the extinction to within 32 kyr.
- Sources: U42, U51, U50, U52
- Excerpt (U51): "The new date for the impact – 66,038,000 years ago –"
- Excerpt (U51): "The new extinction date is precise to within 11,000 years."
- Excerpt (U50, abstract): "the Chicxulub bolide impact to within 32,000 years"
- Excerpt (U52, abstract): "lead us to conclude that the Chicxulub impact triggered the mass extinction"
- Confidence: **verified** for 66.0 and 66.038. The **66.043 ± 0.011** extinction figure from the draft appears only in a search snippet, so it is **unverified**; I couldn't open the Science full text. Deccan volcanism as a contributing stressor is a **live debate**: U52 favours the impact, and U50 calls ecosystems "already under near-critical stress".
- Calendar: **30 Dec 06:05** (06:02 with 13.787). **The draft's "dinosaurs die ≈ Dec 30 morning" is confirmed: just after 6 AM on 30 Dec.**
- Safe wording: "66 million years ago, just after six in the morning on 30 December". Say "the non-bird dinosaurs". Birds are dinosaurs that survived.

**UC21**: Why the asteroid "opened the door" for mammals: after the K-Pg event, mammal diversity doubled within ~100 kyr. Maximum body mass recovered to pre-extinction levels and later tripled. Stem primates (*Purgatorius*) appear within ~105–139 kyr after the boundary.
- Sources: U53, U54
- Excerpt (U53, abstract): "Within ~100 thousand years (ka) post-KPgE, mammalian taxonomic richness doubled"
- Excerpt (U54, abstract): "most likely to within 105-139 thousand years post-K/Pg boundary"
- Confidence: **verified** for the timing. The "empty niches" explanation is the standard interpretation, but these abstracts only describe the recovery. Phrase it as "with the big dinosaurs gone, mammals spread into the roles they had left".
- Calendar: about 4 calendar minutes after the impact, mammal diversity has doubled. Primate relatives show up by 06:09 on 30 Dec.
- Safe wording: avoid "mammals replaced dinosaurs overnight". It is fair to say "within a few calendar minutes" for the first rebound, and "over the next ten million years" (about 6 calendar hours) for the large-scale radiation (my estimate, not sourced).

**UC22** (hand-off): The human and chimpanzee lineages split about **6–7 Myr** ago on fossil evidence (*Sahelanthropus*, Chad). Genetic estimates based on generation times give **at least 7–8 Myr**.
- Sources: U55, U56
- Excerpt (U55, abstract): "the fossils are between 6 and 7 million years old"
- Excerpt (U56, abstract): "We date the human-chimpanzee split to at least 7-8 million years"
- Confidence: **verified**. *Sahelanthropus*'s status as a hominin is itself debated, which is outside this file's scope.
- Calendar: 31 Dec, about 19:00–20:00. Safe wording: "on the evening of 31 December our line split from the chimps' line". Never say "humans evolved from chimps".

## Visual evidence candidates (do not download yet)

| Step | Asset | Owner / credit | Licence (as stated) | Note |
|---|---|---|---|---|
| CMB | Planck CMB 2013: https://www.esa.int/ESA_Multimedia/Images/2013/03/Planck_CMB ; 2018 legacy map: https://sci.esa.int/web/planck/-/60500-plancks-view-of-the-cosmic-microwave-background | ESA and the Planck Collaboration | **ESA Standard Licence**, which says no commercial use without written authorisation (U61) | A monetised channel probably needs ESA approval. Safer alternative below. |
| CMB (alt.) | WMAP 9-year full-sky map, on https://science.nasa.gov/mission/wmap/wmap-overview/ | NASA / WMAP Science Team | NASA media are generally not copyrighted. No endorsement implied, no logos (U62). | Preferred for a monetised video. |
| Galaxy | JADES-GS-z14-0 pullout: https://esawebb.org/images/jades4/ | NASA, ESA, CSA, STScI, B. Robertson (UC Santa Cruz), B. Johnson (CfA), S. Tacchella (Cambridge), P. Cargile (CfA) | ESA/Webb: CC BY 4.0, commercial use OK with the full credit (U15). STScI: public domain, credit requested (U16). | Keep the full credit line. |
| Galaxy | MoM-z14 pullout: https://esawebb.org/images/weic2603a/ | NASA, ESA, CSA, STScI, R. Naidu (MIT), image processing J. DePasquale (STScI) | as above | The current record holder. |
| Elements | GW170817 kilonova images and merger animation on U08 | NASA/CXC/E. Troja; NASA Goddard/CI Lab; NASA/Swift | NASA guidelines (U62) | Supports "gold from colliding neutron stars". |
| Zircon | "Jack Hills detrital zircons BSE micrographs": https://commons.wikimedia.org/wiki/File:Jack_Hills_detrital_zircons_BSE_micrographs.jpg | original work A. Cavosie & J. Valley, rearranged by Gretarsson | "Public domain" per Commons (U65) | **Check the PD basis on the file page** before use. The UW release image (U23) is credited "Graphic by Andree Valley", licence unknown. |
| Zircon site | "Jack Hills, Australia (ASTER)": https://commons.wikimedia.org/wiki/File:Jack_Hills,_Australia_(ASTER).jpg | NASA/METI/AIST/Japan Space Systems, ASTER Science Team | Public domain (Commons) | Satellite view of the site. |
| Early life | Strelley Pool stromatolite photos (several): https://commons.wikimedia.org/wiki/File:Stromatolite_(Strelley_Pool_Formation,_Paleoarchean,_3.35-3.46_Ga;_East_Strelley_Greenstone_Belt,_Pilbara_Craton,_Western_Australia)_2_(17186345399).jpg | James St. John | CC BY 2.0 | Real 3.4-Gyr fossils. Best match for UC12. |
| Living analogue | Shark Bay stromatolites: https://www.usgs.gov/media/images/stromatolites-australia | Paul Harrison (photographer), hosted by USGS | **Conflicting**: the page says "Public Domain" and also "CC BY-SA 3.0" (U64) | Treat as CC BY-SA 3.0. Label it "modern stromatolites". |
| Oxygen | "Banded Iron Formation of Hamersley Range": https://commons.wikimedia.org/wiki/File:Banded_Iron_Formation_of_Hamersley_Range_DSCN2938.jpg | USGS (per Commons) | Public domain (Commons) | Alternatives: "BIF Banded Iron Formation.jpg" (Bramfab, CC0); "Banded iron formation Dales Gorge.jpg" (Graeme Churchard, CC BY 2.0). |
| Ediacaran | *Dickinsonia costata*: https://commons.wikimedia.org/wiki/File:DickinsoniaCostata.jpg | Verisimilus (en.wikipedia) | CC BY 2.5 | Also File:Dickinsonia_costata.jpg (Ghedoghedo, CC BY-SA 3.0). |
| Cambrian | *Marrella splendens* (Burgess Shale): https://commons.wikimedia.org/wiki/File:Marrella_splendens_20221227.jpg | Jstuby | CC0 | Alternatives: Ryan Somma "Burgess Shale Fossils.jpg" (CC BY 2.0); James St. John *Waptia & Marrella* (CC BY 2.0). |
| Impact | Chicxulub free-air gravity anomaly: https://commons.wikimedia.org/wiki/File:Chicxulub_Free-Air_Gravity_anomaly.png | Klokočník et al. (2010), *Solid Earth* 1, 71–83 | CC BY 3.0 | Best gravity map with a clear licence. The "public domain" gravity images on Commons trace to a university page with **unclear rights**, so avoid them. |
| Impact | PIA03379 SRTM shaded relief of Yucatán: https://science.nasa.gov/photojournal/shaded-relief-with-height-as-color-yucatan-peninsula-mexico | NASA/JPL | NASA guidelines (U62); no specific notice on the page | Shows the crater's subtle surface trough. |

Not found or not checked: Smithsonian Burgess Shale and Ediacaran images (the Smithsonian's terms vary by unit; many of its images are non-commercial), Mistaken Point photos (UNESCO page 403), and an official Pop III image (none exists; anything shown is an artist's impression and should be labelled so).

## Story notes

**Most surprising facts for a general Thai audience**
1. **Life started early, and complexity came late.** Earth forms in early September and life is clearly there by the end of September. Then nothing bigger than a microbe-scale cell dominates until mid-December. Animals get only the last two weeks or so of the year (UC12, UC15).
2. **Oxygen waited about two "months".** Microbes were making oxygen long before late October, but iron and volcanic gas soaked it up (UC13). The banded iron rocks are rust from that era, and you can show them on screen.
3. **The gold in a ring came from colliding dead stars** (UC03, U08), and every carbon or oxygen atom in our bodies was made in a star that died before the Sun formed. This answers "why did Earth have to wait until September?"
4. **Dinosaurs arrive on Christmas night and die at about 6 AM on 30 December. Mammals were there almost the whole time**, small and in the background, and they doubled in diversity within about 4 calendar minutes of the impact (UC18–UC21).

Also useful: everything from the first galaxy Webb can see (8 Jan) to the Cambrian (17 Dec) happens before the "interesting" animal story starts. The chimp/human split doesn't come until the evening of 31 Dec.

**Myths to avoid**
- "Life took billions of years to start". **Wrong.** It started within a few hundred million years of Earth's formation (a few calendar weeks). Complex life is what took billions of years.
- "Humans appear at 10:30 PM". That was Sagan's 15-Gyr calendar, and it corresponds to the earliest *Homo* (~2.6 Myr). Leave the human timing to the other researcher's numbers.
- "Mammals came after the dinosaurs". Mammal relatives were around from the Late Triassic (UC19).
- "The CMB is a photo of the Big Bang / the first light". It is the oldest light we can see, released 380,000 years later (UC04).
- "JADES-GS-z14-0 is the most distant galaxy". It was replaced by MoM-z14 (z = 14.44) and its own redshift was revised to 14.18 (UC06).
- "Webb found the first stars". Pop III stars are not confirmed. LAP1-B is a candidate (UC05).
- "The Jack Hills zircon is the oldest rock". It is a mineral grain, not a rock (UC11).
- "Neutron stars made all the gold". Say "a major source" (UC03).
- "Earth/Moon formed on date X" as if exact. Use "early September" and "a few days later" (UC09, UC10).

**Open items:** check Sagan's wording and chapter in a physical copy of *Dragons of Eden* (UC02). Find a citable primary date for the Mistaken Point/Avalon ~575 Myr fossils, if that number is wanted (UC15). Get the Renne et al. 2013 full text for 66.043 (UC20). Check the competing young-Moon age (UC10). Confirm the first crown-mammal date if the script needs one (UC19). Re-check the galaxy record just before publishing (UC06). Ask ESA about the Planck map for monetised use, or use WMAP instead.
