"""Generates ../sources.json — the HydroLoop Source Ledger.

Every numeric default used by the simulation is declared here ONCE, with its
classification. Edit this file (or sources.json directly) when better data
arrive; the model reads defaults only from sources.json.

Research date for all web checks: 2026-10-14.
"""
import json, os

RD = "2026-10-14"

# Evidence types (exactly as required)
LSD = "Local Saudi Data"
PED = "Published Experimental Data"
LIT = "Literature Assumption"
DES = "Design Input"
MEA = "Measured Input"
MAN = "Manufacturer Data"
CAL = "Calculated Value"

# Confidence scale
H, HM, M, LM, L = "High", "High-Medium", "Medium", "Low-Medium", "Low"

S = {}  # citation registry
def cite(key, text, url="", doi="", year=None, location="International"):
    S[key] = dict(text=text, url=url, doi=doi, year=year, location=location)

cite("NOAA_JED", "NOAA 1991-2020 climate normals for Jeddah (King Abdulaziz Intl. Airport), with Jeddah Regional Climate Center; sunshine: DWD 1994-2022. Table retrieved via the Wikipedia 'Jeddah' climate box (secondary compilation).",
     "https://en.wikipedia.org/wiki/Jeddah", "", 2020, "Saudi")
cite("FAO56", "Allen R.G., Pereira L.S., Raes D., Smith M. (1998) Crop evapotranspiration - FAO Irrigation and Drainage Paper 56 (Angstrom default coefficients as=0.25, bs=0.50; latent heat formula in Annex 3).",
     "https://www.fao.org/4/x0490e/x0490e00.htm", "", 1998)
cite("DB", "Duffie J.A., Beckman W.A. Solar Engineering of Thermal Processes (Erbs monthly diffuse correlation; Collares-Pereira & Rabl and Liu & Jordan hourly ratios; isotropic-sky tilted-surface model).",
     "", "10.1002/9781118671603", 2013)
cite("ASHRAE_F", "ASHRAE Handbook - Fundamentals (2009/2017): Ch.1 psychrometrics (implemented by PsychroLib 2.5.0); Ch.14 Table 'Fraction of daily temperature range' for design-day hourly temperature profiles.",
     "https://www.ashrae.org", "", 2017)
cite("PSYCHROLIB", "Meyer D., Thevenard D. (2019) PsychroLib: a library of psychrometric functions to calculate thermodynamic properties of air. Journal of Open Source Software 4(33):1137.",
     "https://github.com/psychrometrics/psychrolib", "10.21105/joss.01137", 2019)
cite("ASHRAE621", "ASHRAE Standard 62.1 Ventilation for Acceptable Indoor Air Quality (office: 2.5 L/s.person + 0.3 L/s.m2).",
     "https://www.ashrae.org", "", 2022)
cite("THIMIJAN", "Thimijan R.W., Heins R.D. (1983) Photometric, radiometric and quantum light units of measure: a review of procedures for interconversion. HortScience 18:818-822 (sunlight PAR: about 4.57 umol/J).",
     "", "10.21273/HORTSCI.18.6.818", 1983)
cite("KAUST_LIB", "KAUST (2024) KSA Algae Living Library - a resource of locally isolated microalgae and cyanobacteria from the Kingdom of Saudi Arabia (de Freitas B.C.B., Lauersen K.J., Barsotti A., dos Santos Mendes M.). Main document, last updated 18 Sep 2024.",
     "https://ssb.kaust.edu.sa/docs/default-source/default-document-library/20240918---living-library-of-ksa-microalgae---main-document.pdf", "", 2024, "Saudi")
cite("UTEX_BG11", "UTEX Culture Collection of Algae - BG-11 Medium (improved recipe as of March 2009) and BG-11 Trace Metals Solution.",
     "https://utex.org/products/bg-11-medium", "", 2009)
cite("ZIJFFERS2010", "Zijffers J.-W.F., Schippers K.J., Zheng K., Janssen M., Tramper J., Wijffels R.H. (2010) Maximum photosynthetic yield of green microalgae in photobioreactors. Marine Biotechnology 12:708-718.",
     "https://link.springer.com/article/10.1007/s10126-010-9258-2", "10.1007/s10126-010-9258-2", 2010)
cite("HUESEMANN2018", "Huesemann M., Chavis A., Edmundson S., et al. (2018) Climate-simulated raceway pond culturing: quantifying the maximum achievable annual biomass productivity of Chlorella sorokiniana in the contiguous USA. J. Appl. Phycol. 30:287-298.",
     "https://link.springer.com/article/10.1007/s10811-017-1256-6", "10.1007/s10811-017-1256-6", 2018)
cite("SILVA2025", "Silva-Benavides A.-M., Torzillo G. (2025) Interplay between light and temperature on growth of Chlorella sorokiniana (Chlorellaceae) cultures under laboratory conditions. Revista de Biologia Tropical 73(S1).",
     "https://www.scielo.sa.cr/scielo.php?script=sci_arttext&pid=S0034-77442025000200004", "10.15517/rev.biol.trop..v73is1.63637", 2025)
cite("KESSLER1985", "Kessler E. (1985) Upper limits of temperature for growth in Chlorella (Chlorophyceae). Plant Systematics and Evolution 151:67-71.",
     "https://link.springer.com/article/10.1007/BF02418020", "10.1007/BF02418020", 1985)
cite("BASHAN2016", "Bashan Y., Lopez B.R., Huss V.A.R., Amavizca E., de-Bashan L.E. (2016) Chlorella sorokiniana (formerly C. vulgaris) UTEX 2714, a non-thermotolerant microalga useful for biotechnological applications and as a reference strain. J. Appl. Phycol. 28:113-121.",
     "https://luzb6.sg-host.com/inmemoriam/bashanY/Chlorella-Sorokiniana-new-ID-2016.pdf", "10.1007/s10811-015-0571-z", 2016)
cite("LI2013", "Li T., Zheng Y., Yu L., Chen S. (2013) High productivity cultivation of a heat-resistant microalga Chlorella sorokiniana for biofuel production. Bioresource Technology 131:60-67 (heterotrophic; tolerates up to 42 C, highest growth 1.60 d-1 at 37 C).",
     "https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/High-productivity-cultivation-of-a-heat-resistant/99900547042001842", "10.1016/j.biortech.2012.11.121", 2013)
cite("GABRIELYAN2022", "Gabrielyan D.A., Gabel B.V., Sinetova M.A., et al. (2022) Optimization of CO2 supply for the intensive cultivation of Chlorella sorokiniana IPPAS C-1 in the laboratory and pilot-scale flat-panel photobioreactors. Life 12(10):1469.",
     "https://pmc.ncbi.nlm.nih.gov/articles/PMC9605657", "10.3390/life12101469", 2022)
cite("ZIGANSHINA2022", "Ziganshina E.E., Bulynina S.S., Ziganshin A.M. (2022) Growth characteristics of Chlorella sorokiniana in a photobioreactor during the utilization of different forms of nitrogen at various temperatures. Plants 11(8):1086.",
     "https://www.mdpi.com/2223-7747/11/8/1086", "10.3390/plants11081086", 2022)
cite("CHISTI2007", "Chisti Y. (2007) Biodiesel from microalgae. Biotechnology Advances 25:294-306 (approximate biomass formula CO0.48H1.83N0.11P0.01; ~1.83 t CO2 per t biomass at ~50% carbon).",
     "", "10.1016/j.biotechadv.2007.02.001", 2007)
cite("DOI2014", "Paper requested by the team: DOI 10.1016/j.biortech.2014.05.118 - 'Cell growth kinetics of Chlorella sorokiniana and nutritional values of its biomass', Bioresource Technology (2014). Title confirmed via ScienceDirect listing; the reported values (1.83 g CO2/g, 1.9 g O2/g) could NOT be read from the original during this audit (publisher page blocked; Crossref/Europe PMC rate-limited).",
     "https://www.sciencedirect.com/science/article/abs/pii/S0960852414008360", "10.1016/j.biortech.2014.05.118", 2014)
cite("WILLIAMS1991", "Williams P.J.leB., Robertson J.E. (1991) Overall planktonic oxygen and carbon dioxide metabolisms: the problem of reconciling observations and calculations of photosynthetic quotients. J. Plankton Res. 13(suppl.1):153-169 (high-precision PQ mostly 1.0-1.36).",
     "https://academic.oup.com/plankt/article/13/supp1/153/1406071", "10.1093/oxfordjournals.plankt.a042366", 1991)
cite("KAZBAR", "Kazbar A. (PhD thesis, Universite de Nantes, GEPEA) Investigation of the impact of dissolved oxygen concentration and design dark fraction on photobioreactor performance (Chlorella vulgaris; 'high DO' group defined as DO > 30 mg/L).",
     "https://archive.bu.univ-nantes.fr/pollux/fichiers/download/2b229523-7a92-462c-809d-bb0015ad79c6", "", None)
cite("NOAA_CO2", "NOAA Global Monitoring Laboratory - Trends in atmospheric CO2, Mauna Loa monthly mean (September 2026: 426.07 ppm; page last updated 09 Oct 2026).",
     "https://gml.noaa.gov/ccgg/trends/", "", 2026)
cite("ALGHAMDI2024", "AlGhamdi S.A., Alromi D., Jambi E., Alzughaibi T., Al-Ansari A. (2024) Heavy metals and microbial assessment of air conditioning condensate water in Jeddah city-Saudi Arabia: concept of sustainable water resources. Sustainable Water Resources Management 10:139 (CC BY 4.0).",
     "https://link.springer.com/article/10.1007/s40899-024-01122-2", "10.1007/s40899-024-01122-2", 2024, "Saudi")
cite("HUSSEIN2012", "Hussein M.H., Magram S.F. (2012) Domestic water quality in Jeddah, Saudi Arabia. JKAU: Eng. Sci. 23(1):207-223 (113 samples from household storage tanks).",
     "https://www.kau.edu.sa/Files/320/Researches/61859_32828.pdf", "", 2012, "Saudi")
cite("KHAN2023", "Khan M.O. (2023, preprint, not peer-reviewed) Quality assessment of condensate water generating from air conditioning units. Preprints.org 202310.1639 (Bangladesh).",
     "https://www.preprints.org/manuscript/202310.1639", "", 2023)
cite("IBRAHIM2017", "Ibrahim N.I., Al-Farayedhi A.A., Gandhidasan P. (2017) Experimental investigation of a vapor compression system with condenser air pre-cooling by condensate. Applied Thermal Engineering 110:1255-1263 (KFUPM; 1.5 TR split unit; ~4 C pre-cooling, 6.1% lower compressor power, COP +21.4%).",
     "https://pure.kfupm.edu.sa/en/publications/experimental-investigation-of-a-vapor-compression-system-with-con/", "10.1016/j.applthermaleng.2016.09.042", 2017, "Saudi")
cite("AHMED2025", "Ahmed F., Ramana A.S., Jayakumar K. (2025) Experimental study on adiabatic pre-cooling systems for air cooled condensers in hot and humid climates. Scientific Reports 15:4933 (1 TR split, Chennai; 100 mm cellulose pad effectiveness max 0.63, avg 0.55; pad water 1.3-1.7 kg/h vs condensate 0.6-0.92 kg/h).",
     "https://www.nature.com/articles/s41598-024-82863-0", "10.1038/s41598-024-82863-0", 2025)
cite("YANG2021", "Yang H., Pei N., Liu L., Fan M., Qin Y. (2021) Experimental study on the effect of condensate water on the performance of split air conditioning system. Energy Reports 7:840-851.",
     "", "10.1016/j.egyr.2021.01.037", 2021)
cite("EVAPCO", "EVAPCO white paper - adiabatic pre-cooling pad testing (10 pad designs, 4 suppliers; saturation efficiency 43-74% at 600 fpm, max 78% at 400 fpm; pressure drop 0.070-0.342 in. H2O at 600 fpm).",
     "https://evapco.com/media/341302", "", None)
cite("ORNL2019", "Shen B., New J., Ally M. (2019) Energy and economics analyses of condenser evaporative precooling for various climates, buildings and refrigerants. Energies 12(11):2079 (greatest potential in hot, dry climates).",
     "https://www.mdpi.com/1996-1073/12/11/2079", "10.3390/en12112079", 2019)
cite("ER2026", "Energy Reports (2026) 'Performance enhancement of air conditioner with evaporative cooling of intake air to the condenser using condensate water' (ScienceDirect PII S2352484726000065). Identified, but full text/abstract could not be read (robots-blocked) - NOT used numerically.",
     "https://www.sciencedirect.com/science/article/pii/S2352484726000065", "", 2026)
cite("ER2024", "Energy Reports (2024) 'Experimental study on heat recovery and utilization of air conditioning condensate' (PII S2352484724006644). Identified, not readable here - NOT used numerically. The team's note about avoiding direct spray on aluminium fins could not be verified from this source.",
     "https://www.sciencedirect.com/science/article/pii/S2352484724006644", "", 2024)
cite("ECRA2018", "Electricity & Cogeneration Regulatory Authority (ECRA, now SERA) tariff decision effective 1 Jan 2018, reported by Saudi Gazette (12 Dec 2017): Government 32 halalas/kWh flat; residential 18/30; commercial 20/30. Saudi Gazette (21 Jun 2025) reports residential/commercial tariffs unchanged in the 2025 guide; the government rate was not re-confirmed on an official page during this audit.",
     "https://saudigazette.com.sa/article/524039", "", 2018, "Saudi")
cite("DNA2021", "Designated National Authority of Saudi Arabia (2021) Development of the Kingdom's Updated Grid Emission Factor (0.568 tCO2/MWh), as cited in KFUPM Greenhouse Gas Emissions Inventory.",
     "https://sustainability.kfupm.edu.sa/documents/53/Greenhouse_Gas_Emissions_Inventory.pdf", "", 2021, "Saudi")
cite("HAILEA", "Retail listing of Hailea ACO-208 piston air pump: 2100 L/h (35 L/min), 18 W, 220-240 V (manufacturer rating as reproduced by retailer).",
     "https://www.emag.bg/vyzdushna-pompa-hailea-aco-208-2100-l-ch-pylen-komplekt-35-l-min-220-240-v-18w-142x80x78mm-502unjcqdjcvii/pd/D718X72BM/", "", None)
cite("FLUIDS", "Standard fluid-mechanics references (e.g., White F.M., Fluid Mechanics): sharp-edged orifice discharge coefficient ~0.61; Darcy-Weisbach with Swamee-Jain (1976) friction factor; typical minor-loss coefficients (entrance 0.5, standard 90 deg elbow ~0.9); smooth plastic pipe roughness ~0.0015 mm.",
     "", "", None)
cite("PROJECT", "HydroLoop / EcoFlow Algae Facade - Miyahthon 3 digital-bootcamp submission (validation targets).", "", "", 2026, "Saudi")
cite("NONE", "No reliable source found - value is a user Design Input and must be measured or replaced.", "", "", None)

E = []  # ledger entries
def add(key, name, value, unit, dtype, src, conf, used_as, strain="", cond="", warn="", group=""):
    c = S[src]
    E.append(dict(key=key, name=name, value=value, unit=unit, data_type=dtype,
                  source=c["text"], source_key=src, url=c["url"], doi=c["doi"], year=c["year"],
                  location=c["location"], strain=strain, conditions=cond, confidence=conf,
                  warning=warn, used_as=used_as, group=group))

# ---------------- CLIMATE ----------------
G = "Climate"
add("lat", "Site latitude", 21.49, "deg N", DES, "PROJECT", H, "Solar geometry", cond="Team-specified location (Jeddah)", group=G)
add("lon", "Site longitude", 39.19, "deg E", DES, "PROJECT", H, "NASA POWER request", group=G)
add("elev_m", "Site elevation", 12.0, "m", DES, "NONE", M, "Standard-atmosphere pressure", warn="Jeddah coastal elevation; replace with surveyed value", group=G)
add("noaa_tmax", "Monthly mean daily max temperature (Jan..Dec)", [28.8,29.8,31.7,34.5,37.1,38.3,39.4,38.7,37.4,36.6,33.3,30.6], "C", LSD, "NOAA_JED", HM, "Hourly temperature profile", cond="1991-2020 normals, KAIA station", warn="Monthly means: real hourly extremes (e.g., 45-52 C records) are not represented; use NASA POWER/measured hourly data for extremes", group=G)
add("noaa_tmin", "Monthly mean daily min temperature (Jan..Dec)", [18.8,19.0,20.2,22.8,25.0,25.8,27.6,28.6,27.3,25.0,22.9,20.6], "C", LSD, "NOAA_JED", HM, "Hourly temperature profile", cond="1991-2020 normals", group=G)
add("noaa_rh", "Monthly mean relative humidity (Jan..Dec)", [60,60,60,57,56,58,53,59,67,66,65,63], "%", LSD, "NOAA_JED", HM, "Humidity ratio (held constant through each day)", cond="1991-2020 normals", warn="Mean RH converted to a constant daily humidity ratio at the daily-mean temperature (ASHRAE design-day convention); hourly humidity peaks are not represented", group=G)
add("noaa_sun", "Monthly sunshine hours (Jan..Dec)", [236.0,232.2,261.0,273.7,300.8,295.8,300.3,278.3,252.7,265.5,246.1,236.2], "h/month", LSD, "NOAA_JED", M, "Angstrom-Prescott solar estimate", cond="DWD 1994-2022", group=G)
add("ang_a", "Angstrom coefficient a_s", 0.25, "-", LIT, "FAO56", LM, "Global radiation from sunshine", warn="FAO-56 default for uncalibrated sites; Jeddah-calibrated coefficients or NASA POWER data should replace it", group=G)
add("ang_b", "Angstrom coefficient b_s", 0.50, "-", LIT, "FAO56", LM, "Global radiation from sunshine", group=G)
add("albedo", "Ground reflectance", 0.20, "-", LIT, "DB", LM, "Ground-reflected radiation on facade", warn="Urban Jeddah surfaces may differ", group=G)
add("f_par", "PAR fraction of global solar radiation", 0.45, "-", LIT, "THIMIJAN", LM, "PPFD from irradiance", warn="Typical 0.45-0.50; not measured for Jeddah", group=G)
add("umol_per_J", "Quantum conversion for sunlight PAR", 4.57, "umol/J", LIT, "THIMIJAN", M, "PPFD from PAR W/m2", group=G)
add("facade_az", "Facade azimuth (0=south, -90=east, +90=west)", 0.0, "deg", DES, "NONE", H, "Facade irradiance", group=G)
add("shade", "External shading fraction on panel", 0.0, "-", DES, "NONE", L, "Reduces light and solar heat", group=G)
add("rh_offset", "Relative-humidity offset applied to climate (sensitivity)", 0.0, "% points", DES, "NONE", H, "Sensitivity only", group=G)
add("t_offset", "Air-temperature offset applied to climate (sensitivity)", 0.0, "C", DES, "NONE", H, "Sensitivity only", group=G)
add("cond_scale", "Condensate multiplier (sensitivity)", 1.0, "-", DES, "NONE", H, "Sensitivity only", group=G)
add("light_scale", "Light multiplier on facade PPFD (sensitivity)", 1.0, "-", DES, "NONE", H, "Sensitivity only", group=G)
add("nutrient_strength", "BG-11 dosing strength in refill medium (1 = full BG-11)", 1.0, "-", DES, "UTEX_BG11", H, "Nutrient dosing", group=G)
add("period", "Simulation period", "annual", "-", DES, "NONE", H, "annual / summer / winter / month / 24h / 7d / 30d", group=G)
add("start_doy", "Start day of year for 24h/7d/30d runs", 213, "day", DES, "NONE", H, "Short runs (213 = 1 Aug)", group=G)
add("period_month", "Month for monthly run", 8, "-", DES, "NONE", H, "Monthly run", group=G)

# ---------------- HVAC / CONDENSATE ----------------
G = "HVAC & condensate"
add("cond_mode", "Condensate calculation mode", "psychrometric", "-", DES, "NONE", H, "'measured' uses the measured L/h; 'psychrometric' uses coil air states", group=G)
add("cond_meas_lph", "Measured condensate rate while AC operates", None, "L/h", MEA, "NONE", H, "Measured Mode (highest confidence)", warn="Enter the measured value from the 3-day collection test", group=G)
add("ac_tr", "AC nominal cooling capacity", 2.0, "TR", DES, "NONE", M, "Coil air flow, capacity check, HVAC power", warn="Set to the actual target unit; Jeddah 2024 study did not report unit capacity", group=G)
add("kw_per_tr", "kW per ton of refrigeration", 3.517, "kW/TR", LIT, "ASHRAE_F", H, "Unit conversion (definition)", group=G)
add("evap_cfm_tr", "Evaporator air flow per TR", 400.0, "cfm/TR", DES, "NONE", LM, "Coil dry-air mass flow", warn="Common HVAC design convention (~400 cfm/ton); use nameplate/measured flow", group=G)
add("oa_frac", "Outdoor-air fraction at coil inlet", 0.10, "-", DES, "NONE", L, "Coil inlet humidity (mixing)", warn="Split units are often recirculating with infiltration; measure or use Measured Mode", group=G)
add("t_in", "Indoor (return) air temperature", 24.0, "C", DES, "NONE", M, "Coil inlet state", group=G)
add("rh_in", "Indoor (return) relative humidity", 55.0, "%", DES, "NONE", L, "Coil inlet state", warn="Indoor humidity in Jeddah buildings is load-dependent; measure it", group=G)
add("t_coil", "Coil leaving air dry-bulb", 13.0, "C", DES, "NONE", LM, "Coil leaving humidity ratio", group=G)
add("rh_coil", "Coil leaving air relative humidity", 95.0, "%", DES, "NONE", LM, "Coil leaving humidity ratio", group=G)
add("sched_on", "AC schedule start hour", 0, "h", DES, "NONE", M, "Operating hours", group=G)
add("sched_off", "AC schedule end hour", 24, "h", DES, "NONE", M, "Operating hours", group=G)
add("t_bal", "Load model: balance temperature (RTF = min_rtf)", 18.0, "C", DES, "NONE", L, "Runtime fraction vs outdoor temperature", warn="Simple linear bin-type load assumption, not a building load simulation", group=G)
add("t_des", "Load model: temperature at RTF = 1", 44.0, "C", DES, "NONE", L, "Runtime fraction vs outdoor temperature", group=G)
add("rtf_min", "Load model: minimum runtime fraction", 0.30, "-", DES, "NONE", L, "Runtime fraction", group=G)
add("cop_rated", "AC COP at 35 C outdoor (rating point)", 3.2, "W/W", DES, "NONE", LM, "HVAC power before precooling", warn="Replace with the unit's nameplate/datasheet value (Manufacturer Data)", group=G)
add("t_evap", "Evaporating temperature (Carnot-fraction cross-check)", 7.0, "C", DES, "NONE", LM, "Physical COP cross-check only", group=G)
add("cond_approach", "Condensing temperature minus condenser inlet air", 12.0, "K", DES, "NONE", LM, "Physical COP cross-check only", group=G)
add("cond_cfm_tr", "Condenser air flow per TR", 1000.0, "cfm/TR", DES, "NONE", LM, "Air mass through evaporative media", warn="Use the outdoor-unit datasheet", group=G)
add("slope_pct_per_K", "Compressor power reduction per K of condenser inlet air pre-cooling", 1.525, "%/K", PED, "IBRAHIM2017", M, "Sensitivity Approximation (linearised from 6.1% at ~4 C)", cond="1.5 TR split unit, KFUPM, Saudi Arabia", warn="Linearisation of one experiment; not a general law. Capacity gain (COP +21.4%) is NOT credited.", group=G)
add("hvac_method", "HVAC saving method", "empirical", "-", DES, "NONE", H, "'empirical' (Ibrahim 2017 slope) or 'carnot' (physical cross-check)", group=G)

# ---------------- EVAPORATIVE MEDIA ----------------
G = "Evaporative media"
add("media_on", "Evaporative media installed", True, "-", DES, "NONE", H, "Condenser pre-cooling module", group=G)
add("media_eff", "Media saturation effectiveness", 0.55, "-", PED, "AHMED2025", M, "Media cooling limit", cond="100 mm cellulose pad, 1 TR split, Chennai hot-humid; average 0.55 (max 0.63)", warn="Effectiveness depends on face velocity and pad depth", group=G)
add("media_eff_cons", "Media effectiveness - conservative", 0.43, "-", MAN, "EVAPCO", M, "Conservative scenario", cond="3-inch pad at 600 fpm", group=G)
add("media_eff_opt", "Media effectiveness - optimistic", 0.74, "-", MAN, "EVAPCO", M, "Optimistic scenario", cond="6-inch pad at 600 fpm (best tested)", group=G)
add("media_dp_pa", "Media air-side pressure drop", 25.0, "Pa", MAN, "EVAPCO", M, "Condenser fan power penalty", cond="4-inch pad, 600 fpm: 0.102 in. H2O", warn="Penalty applies whenever the pad is installed, wet or dry", group=G)
add("fan_eff", "Condenser fan total efficiency", 0.30, "-", DES, "NONE", L, "Fan power penalty", group=G)
add("media_face_v", "Air face velocity through the media", 1.5, "m/s", DES, "NONE", M, "Scales the EVAPCO pressure drop (dp ~ v^2 from 3.05 m/s)", warn="Lower velocity = larger pad area, lower pressure drop", group=G)
add("media_v_ref", "Face velocity of the EVAPCO pressure-drop data (600 fpm)", 3.048, "m/s", MAN, "EVAPCO", M, "Pressure-drop scaling reference", group=G)

# ---------------- TANK & HYDRAULICS ----------------
G = "Tank & overflow"
add("tank_L", "Clean condensate tank volume", 60.0, "L", DES, "NONE", H, "Tank water balance", group=G)
add("ovf_level", "Overflow lip level (fraction of tank volume)", 0.80, "-", DES, "NONE", H, "Overflow start", group=G)
add("tank_init", "Initial tank level (fraction)", 0.50, "-", DES, "NONE", H, "Initial condition", group=G)
add("prefilter_loss", "Pre-filter loss fraction", 0.0, "-", DES, "NONE", M, "Water balance", warn="Set >0 only if measured", group=G)
add("ovf_head", "Overflow line elevation difference (lip to orifice)", 1.0, "m", DES, "NONE", H, "Gravity head", group=G)
add("pipe_L", "Overflow pipe length", 3.0, "m", DES, "NONE", H, "Friction loss", group=G)
add("pipe_D", "Overflow pipe inner diameter", 0.0127, "m", DES, "NONE", H, "Friction loss", group=G)
add("pipe_rough", "Pipe absolute roughness (smooth plastic)", 1.5e-6, "m", LIT, "FLUIDS", M, "Darcy-Weisbach friction factor", group=G)
add("n_elbows", "Number of 90-deg elbows", 4, "-", DES, "NONE", H, "Minor losses", group=G)
add("k_elbow", "Elbow loss coefficient", 0.9, "-", LIT, "FLUIDS", LM, "Minor losses", group=G)
add("k_entr", "Entrance loss coefficient", 0.5, "-", LIT, "FLUIDS", M, "Minor losses", group=G)
add("orifice_d", "Flow-restrictor orifice diameter", 0.003, "m", DES, "NONE", H, "Overflow capacity", group=G)
add("cd", "Orifice discharge coefficient (sharp edged)", 0.61, "-", LIT, "FLUIDS", M, "Orifice flow", group=G)
add("orifice_dmin", "Minimum orifice diameter before clogging risk", 0.002, "m", DES, "NONE", L, "Clogging flag (design rule, verify with filter mesh)", group=G)
add("rho_w", "Water density (25 C)", 997.0, "kg/m3", LIT, "FLUIDS", H, "Hydraulics", group=G)
add("mu_w", "Water dynamic viscosity (25 C)", 8.9e-4, "Pa.s", LIT, "FLUIDS", H, "Reynolds number", group=G)

# ---------------- REACTOR ----------------
G = "Photobioreactor"
add("pbr_H", "Panel height", 1.0, "m", DES, "NONE", H, "Geometry", group=G)
add("pbr_W", "Panel width", 0.5, "m", DES, "NONE", H, "Geometry", group=G)
add("pbr_t", "Panel thickness = optical path length", 0.04, "m", DES, "GABRIELYAN2022", M, "Geometry; 40 mm matches the published flat-panel reference", group=G)
add("wall_tau", "Panel wall light transmittance", 0.90, "-", DES, "NONE", LM, "Light reaching culture", warn="Use acrylic/polycarbonate datasheet value; fouling reduces it", group=G)
add("alpha_sol", "Panel solar absorptance (thermal)", 0.80, "-", DES, "NONE", L, "Reactor heat gain", warn="Must be calibrated with the 5-minute temperature log", group=G)
add("u_face", "Heat-loss coefficient per face", 15.0, "W/m2K", DES, "NONE", L, "Reactor temperature", warn="Must be calibrated with measured panel temperature", group=G)
add("x0", "Initial biomass concentration", 0.30, "g/L", DES, "NONE", M, "Initial condition", group=G)
add("ph", "Culture pH (controlled/measured)", 7.0, "-", DES, "NONE", M, "pH response", warn="pH is an input, not simulated (no carbonate chemistry model)", group=G)
add("vvm", "Aeration rate", 0.20, "L gas/L culture/min", PED, "GABRIELYAN2022", M, "Gas supply, evaporation", cond="0.2 vvm in 40 mm flat panels", group=G)
add("circ_lpm", "Circulation pump flow", 5.0, "L/min", DES, "NONE", M, "Pump energy", group=G)
add("circ_head", "Circulation pump head", 1.5, "m", DES, "NONE", M, "Pump energy", group=G)
add("pump_eff", "Small pump wire-to-water efficiency", 0.25, "-", DES, "NONE", L, "Pump energy", warn="Use pump curve", group=G)
add("pump_min_w", "Minimum pump electrical power", 5.0, "W", DES, "NONE", L, "Pump energy floor", group=G)
add("circ_hours", "Circulation pump hours per day", 24.0, "h/day", DES, "NONE", H, "Pump energy", group=G)
add("dil_rate", "Dilution (harvest) rate", 0.20, "1/day", DES, "NONE", M, "Harvest volume and HRT", group=G)
add("harvest_hour", "Daily harvest hour", 17, "h", DES, "NONE", H, "Harvest timing", group=G)
add("sample_L", "Sampling volume", 0.10, "L/day", DES, "NONE", H, "Makeup demand", group=G)
add("blowdown_L", "Periodic blowdown volume", 0.0, "L/week", DES, "NONE", H, "Makeup demand", group=G)
add("cool_on", "Evaporative panel cooling with clean condensate", False, "-", DES, "NONE", H, "Optional reactor temperature control", group=G)
add("cool_set", "Panel cooling set-point", 35.0, "C", DES, "NONE", M, "Optional reactor temperature control", group=G)
add("light_on", "Supplementary LED lighting", False, "-", DES, "NONE", H, "Optional", group=G)
add("led_ppfd", "LED PPFD at panel", 200.0, "umol/m2/s", DES, "NONE", M, "Optional lighting", group=G)
add("led_eff", "LED photon efficacy", 2.5, "umol/J", DES, "NONE", LM, "Lighting energy", warn="Use LED datasheet", group=G)
add("led_hours", "LED hours per day (night)", 6.0, "h/day", DES, "NONE", H, "Lighting", group=G)

# ---------------- STRAIN & GROWTH ----------------
G = "Strain & growth"
add("strain_mode", "Strain mode", "literature", "-", DES, "NONE", H, "'literature' = Species-Level Reference; 'local' = KAUST candidate (Estimated)", group=G)
add("temp_profile", "Temperature-response profile", "UTEX1230", "-", DES, "NONE", M, "'UTEX1230' (measured points) or 'THERMO_CTMI' (thermotolerant literature)", group=G)
add("y_ph", "Biomass yield on absorbed photons", 0.75, "g/mol photons", PED, "ZIJFFERS2010", M, "Light-limited growth (Pirt)", strain="Chlorella sorokiniana (species level)", cond="37 C, pH 6.7, 930 umol/m2/s, 12.5-21.5 mm panels, continuous", warn="Measured at <=930 umol/m2/s; outdoor peaks are higher", group=G)
add("m_s", "Maintenance photon requirement", 0.0068, "mol photons/g/h", PED, "ZIJFFERS2010", M, "Respiration/maintenance (day and night)", strain="C. sorokiniana", group=G)
add("i_valid", "Highest PPFD at which the yield was measured", 930.0, "umol/m2/s", PED, "ZIJFFERS2010", M, "Above this, only a user-set fraction of photons is credited", group=G)
add("hl_use", "Fraction of photons above the validated PPFD credited to growth", 0.5, "-", DES, "NONE", L, "High-light efficiency (no published value for this geometry)", warn="0 = conservative, 1 = optimistic", group=G)
add("k_abs", "Biomass-specific light absorption coefficient", 0.15, "m2/g", DES, "NONE", L, "Beer-Lambert absorbed fraction and dark-zone indicator", warn="No verified value found during audit; measure absorbance vs dry weight", group=G)
add("mu_max", "Maximum specific growth rate (36 C, pH 7)", 5.83, "1/day", PED, "HUESEMANN2018", M, "Upper cap on growth", strain="C. sorokiniana DOE 1412", cond="Indoor, light-saturated, 36 C", group=G)
add("ph_pts", "pH response points (pH: relative mu_max)", [[6,1.0],[7,0.985],[8,0.826],[9,0.711]], "-", PED, "HUESEMANN2018", M, "pH multiplier (interpolated; held at edges outside 6-9 with warning)", strain="C. sorokiniana DOE 1412", cond="36 C; mu_max 5.92/5.83/4.89/4.21 d-1 at pH 6/7/8/9", group=G)
add("t_pts_utex1230", "Temperature response points UTEX 1230 (T: relative final dry weight)", [[25,0.847],[30,1.0],[35,0.700],[40,0.404],[45,0.0]], "-", PED, "SILVA2025", M, "Temperature multiplier (interpolated)", strain="C. sorokiniana UTEX 1230", cond="200 umol/m2/s, batch 9 days; ratios of final dry weight (6.19 g/L at 30 C = 1)", warn="Ratios of final dry weight, not specific growth rates; below 25 C held at 0.847 (no data at this light)", group=G)
add("ctmi_tmin", "Thermotolerant profile Tmin", 10.0, "C", DES, "NONE", L, "CTMI lower bound", warn="No verified Tmin found; affects only cool months", group=G)
add("ctmi_topt", "Thermotolerant profile Topt", 37.0, "C", PED, "LI2013", LM, "CTMI optimum", strain="C. sorokiniana (heat-resistant strain, heterotrophic)", cond="Heterotrophic glucose culture", warn="Heterotrophic optimum used for a phototrophic system", group=G)
add("ctmi_tmax", "Thermotolerant profile Tmax", 42.0, "C", PED, "LI2013", LM, "CTMI upper limit", strain="C. sorokiniana", cond="Species range 38-42 C (Kessler 1985)", group=G)
add("t_range_lo", "Suitable reactor temperature range - low (Target 3)", 25.0, "C", CAL, "SILVA2025", M, "Validation target 3", warn="Derived: relative growth >= ~0.7 for UTEX 1230", group=G)
add("t_range_hi", "Suitable reactor temperature range - high (Target 3)", 35.0, "C", CAL, "SILVA2025", M, "Validation target 3", group=G)

# ---------------- STOICHIOMETRY / CARBON / O2 ----------------
G = "Carbon & oxygen"
add("cf", "Biomass carbon fraction", 0.50, "g C/g DW", LIT, "CHISTI2007", LM, "Carbon-content method (CO2 = X*Cf*44/12)", warn="Literature assumption; replace with CHN measurement (Measured Input)", group=G)
add("cf_meas", "Measured biomass carbon fraction (CHN)", None, "g C/g DW", MEA, "NONE", H, "Overrides cf when entered", group=G)
add("stoich_factor", "Species stoichiometry factor (CO2 per g biomass)", 1.88, "g CO2/g DW", PED, "GABRIELYAN2022", M, "Cross-check method (not added)", strain="C. sorokiniana IPPAS C-1", cond="Derived from formula CO0.48H1.83N0.11P0.01", warn="Not independent of the carbon-content method (same formula basis)", group=G)
add("stoich_doi2014_co2", "Team reference: CO2 per g biomass (DOI 10.1016/j.biortech.2014.05.118)", 1.83, "g CO2/g DW", LIT, "DOI2014", L, "Shown for comparison only - NOT VERIFIED", warn="Could not be read from the original paper; 1.83 equals 0.50*44/12 exactly (Chisti 2007), so it is not an independent check", group=G)
add("stoich_doi2014_o2", "Team reference: O2 per g biomass (DOI 10.1016/j.biortech.2014.05.118)", 1.9, "g O2/g DW", LIT, "DOI2014", L, "Shown for comparison only - NOT VERIFIED", group=G)
add("formula", "Biomass elemental formula per C-mol (CHxOyNzPw)", {"H":1.83,"O":0.48,"N":0.11,"P":0.01}, "-", LIT, "CHISTI2007", LM, "N, P content; O2 stoichiometry", warn="Generic microalgal formula, not measured for KAUST 111", group=G)
add("ash", "Ash fraction of dry weight", 0.0, "-", DES, "NONE", L, "Converts ash-free formula to dry weight", warn="Measure ash; default 0 overstates C, N, P, O2 per g DW slightly", group=G)
add("n_source", "Nitrogen source", "nitrate", "-", DES, "UTEX_BG11", H, "O2 stoichiometry (BG-11 uses NaNO3)", group=G)
add("pq", "Photosynthetic quotient (PQ method)", 1.36, "mol O2/mol CO2", LIT, "WILLIAMS1991", LM, "Cross-check O2 method (not added)", warn="High-precision range 1.0-1.36; nitrate assimilation pushes PQ to the upper end", group=G)
add("co2_source", "Carbon source", "ambient", "-", DES, "NONE", H, "'ambient', 'enriched', 'bicarbonate', 'flue', 'other'", group=G)
add("co2_ppm", "Ambient CO2 concentration", 426.07, "ppm", PED, "NOAA_CO2", H, "Ambient-air carbon supply", cond="Mauna Loa monthly mean, Sep 2026", warn="Background value; urban Jeddah air is likely higher; local measurement recommended", group=G)
add("co2_enriched_pct", "CO2 in enriched air / flue gas", 1.5, "% v/v", PED, "GABRIELYAN2022", M, "Enriched-air option", cond="Optimum gas mix for C. sorokiniana IPPAS C-1", group=G)
add("eta_transfer", "Gas-to-liquid CO2 transfer (utilisation) efficiency", 0.35, "-", PED, "GABRIELYAN2022", LM, "CO2 transferable", cond="CUE at 1.5% CO2, 0.2 vvm, 40 mm panel", warn="Measured for enriched gas; for ambient air it is a Design Input to measure (inlet/outlet CO2)", group=G)
add("bicarb_g_day", "Sodium bicarbonate dose", 0.0, "g NaHCO3/day", DES, "NONE", H, "Bicarbonate option", group=G)
add("eta_bicarb", "Bicarbonate carbon availability", 1.0, "-", DES, "NONE", L, "Upper bound (all dosed carbon available)", group=G)
add("other_co2_g_day", "Other CO2 source", 0.0, "g CO2/day", DES, "NONE", H, "'other' option", group=G)
add("do_meas", "Measured dissolved oxygen", None, "mg/L", MEA, "NONE", H, "DO warning only (no kLa model)", group=G)
add("do_warn", "DO level flagged as high", 30.0, "mg/L", LIT, "KAZBAR", LM, "DO warning threshold", strain="Chlorella vulgaris", warn="Not strain-specific; indicative only", group=G)
add("biomass_fate", "Biomass fate", "harvested", "-", DES, "NONE", H, "harvested/stored/product/composted/digested/discarded", group=G)
add("longterm_storage_proven", "Long-term carbon storage pathway proven", False, "-", DES, "NONE", H, "Permanent sequestration reported only if True", group=G)

# ---------------- ENERGY ----------------
G = "Energy"
add("air_w_per_lpm", "Air pump specific power", 18.0/35.0, "W per L/min", MAN, "HAILEA", LM, "Air pump energy", cond="Hailea ACO-208: 18 W at 35 L/min", warn="Rated at free flow; real back-pressure lowers flow", group=G)
add("sensor_w", "Sensors power", 1.5, "W", DES, "NONE", LM, "Control energy", group=G)
add("ctrl_w", "Controller (ESP32) power", 1.0, "W", DES, "NONE", LM, "Control energy", group=G)
add("pv_on", "Solar PV included", False, "-", DES, "NONE", H, "PV production reported separately", group=G)
add("pv_kwp", "PV size", 0.1, "kWp", DES, "NONE", H, "PV production", group=G)
add("pv_pr", "PV performance ratio", 0.75, "-", DES, "NONE", LM, "PV production", group=G)
add("grid_ef", "Saudi grid emission factor", 0.568, "kg CO2/kWh", LSD, "DNA2021", M, "Electricity carbon (operational only)", cond="2021 update", group=G)

# ---------------- ECONOMICS ----------------
G = "Economics"
add("tariff", "Electricity tariff (government sector)", 0.32, "SAR/kWh", LSD, "ECRA2018", M, "Electricity cost and saving", warn="ECRA 2018 decision via Saudi Gazette; confirm on the latest SERA/SEC tariff page before use", group=G)
add("water_tariff", "Water tariff for displaced tap water", None, "SAR/m3", DES, "NONE", L, "Water reuse value (blank = not valued)", group=G)
for k, n in [("capex_tank","Tank"),("capex_pbr","Transparent reactor panel"),("capex_pipes","Pipes"),("capex_valves","Valves"),
             ("capex_filters","Filters"),("capex_circpump","Circulation pump"),("capex_airpump","Air pump"),("capex_sensors","Sensors"),
             ("capex_ctrl","Controller"),("capex_media","Evaporative media"),("capex_pan","Drain pan"),("capex_pv","Solar PV"),
             ("capex_install","Installation"),("capex_frame","Structure/frame")]:
    add(k, f"CAPEX - {n}", None, "SAR", DES, "NONE", L, "CAPEX (blank = not priced)", warn="Enter a dated quotation; no prices were invented", group=G)
for k, n, u in [("opex_nutrient_sar_kg","BG-11 chemicals price","SAR/kg"),("opex_cleaning","Cleaning","SAR/yr"),("opex_filters","Filter replacement","SAR/yr"),
                ("opex_harvest","Harvesting","SAR/yr"),("opex_maint","Maintenance","SAR/yr"),("opex_labour","Labour","SAR/yr")]:
    add(k, f"OPEX - {n}", None, u, DES, "NONE", L, "OPEX (blank = not priced)", group=G)
add("biomass_price", "Biomass price (documented product & market only)", None, "SAR/kg", DES, "NONE", L, "Biomass revenue (default 0)", warn="Revenue stays 0 unless product, market and a dated price source are entered", group=G)
add("eval_years", "Evaluation period for break-even CAPEX", 5, "years", DES, "NONE", H, "Allowable CAPEX", group=G)

# ---------------- VALIDATION TARGETS ----------------
G = "Validation targets"
add("vt1_margin", "Target 1: condensate must cover reactor need with margin", 0.20, "-", DES, "PROJECT", H, "Validation Target 1 (100% + 20%)", group=G)
add("vt2_ratio", "Target 2: growth in conditioned condensate vs control", 0.80, "-", DES, "PROJECT", H, "Validation Target 2", group=G)
add("vt2_meas", "Measured growth ratio (condensate/control)", None, "-", MEA, "NONE", H, "Target 2 (experiment only)", group=G)
add("vt3_frac", "Target 3: share of operating time within strain range", 0.90, "-", DES, "PROJECT", H, "Validation Target 3", group=G)

# ---------------- REFERENCE DATA (not model inputs) ----------------
G = "Reference data"
add("ref_jed_split_L_yr", "Jeddah split AC annual condensate", 20614, "L/yr", LSD, "ALGHAMDI2024", M, "Order-of-magnitude check only", cond="Southern Jeddah 2019; 8 h/day collection extrapolated to 24 h; unit capacity NOT reported", warn="Do not scale to a specific tonnage", group=G)
add("ref_jed_window_L_yr", "Jeddah window AC annual condensate", 8725, "L/yr", LSD, "ALGHAMDI2024", M, "Order-of-magnitude check only", group=G)
add("ref_jed_split_peak", "Jeddah split AC peak month (Oct)", 2274, "L/month", LSD, "ALGHAMDI2024", M, "Seasonality check", group=G)
add("ref_jed_split_low", "Jeddah split AC low month (Feb)", 1292, "L/month", LSD, "ALGHAMDI2024", M, "Seasonality check", group=G)
add("ref_cond_tds_max", "Condensate TDS (maximum observed)", 203, "mg/L", LSD, "ALGHAMDI2024", M, "Corrosion/scaling comparison", cond="Window AC, December", group=G)
add("ref_cond_ec_max", "Condensate EC (maximum observed)", 405, "uS/cm", LSD, "ALGHAMDI2024", M, "Corrosion/scaling comparison", group=G)
add("ref_tap_tds", "Jeddah household tap water TDS (mean)", 194.17, "mg/L", LSD, "HUSSEIN2012", M, "Corrosion/scaling comparison", cond="113 samples from storage tanks", group=G)
add("ref_tap_ec", "Jeddah household tap water EC (mean)", 320.57, "uS/cm", LSD, "HUSSEIN2012", M, "Comparison", group=G)
add("ref_tap_hard", "Jeddah household tap water total hardness (mean)", 43.66, "mg/L", LSD, "HUSSEIN2012", M, "Comparison", group=G)
add("ref_tap_cl", "Jeddah household tap water chloride (mean)", 85.66, "mg/L", LSD, "HUSSEIN2012", M, "Comparison", group=G)
add("ref_bd_tds", "Condensate TDS, Bangladesh (preprint)", "190-240", "mg/L", PED, "KHAN2023", LM, "Comparison only", group=G)
add("ref_ahmed_pad_water", "Pad water demand vs condensate (1 TR)", "pad 1.3-1.7 kg/h; condensate 0.6-0.92 kg/h", "kg/h", PED, "AHMED2025", M, "Shows pad can be water-limited", group=G)

out = dict(research_date=RD, evidence_types=[LSD,PED,LIT,DES,MEA,MAN,CAL],
           confidence_scale={"Measured Input":H, LSD:HM, PED:M, LIT:LM, DES:L, MAN:M, CAL:"inherits weakest input"},
           citations=S, ledger=E)
p = os.path.join(os.path.dirname(__file__), "..", "sources.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"wrote {len(E)} ledger entries, {len(S)} citations -> {os.path.abspath(p)}")
