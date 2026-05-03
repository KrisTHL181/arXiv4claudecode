"""arXiv category taxonomy — ~180 categories across 8 groups."""

from arxiv_cli.models import Category, CategoryGroup

# Full taxonomy from https://arxiv.org/category_taxonomy
_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "cs": [
        ("cs.AI", "Artificial Intelligence", "AI, machine learning, reasoning, knowledge representation"),
        ("cs.AR", "Hardware Architecture", "Processor, memory, and storage architectures"),
        ("cs.CC", "Computational Complexity", "Models of computation, complexity classes"),
        ("cs.CE", "Computational Engineering, Finance, and Science", "Computational methods in engineering and science"),
        ("cs.CG", "Computational Geometry", "Geometric algorithms and data structures"),
        ("cs.CL", "Computation and Language", "NLP, speech, language models"),
        ("cs.CR", "Cryptography and Security", "Encryption, network security, formal methods for security"),
        ("cs.CV", "Computer Vision and Pattern Recognition", "Image and video analysis, object recognition"),
        ("cs.CY", "Computers and Society", "Social impact of computing, ethics, policy"),
        ("cs.DB", "Databases", "Database systems, query processing, data management"),
        ("cs.DC", "Distributed, Parallel, and Cluster Computing", "Distributed systems, cloud computing"),
        ("cs.DL", "Digital Libraries", "Digital libraries, information retrieval, preservation"),
        ("cs.DM", "Discrete Mathematics", "Combinatorics, graph theory, discrete optimization"),
        ("cs.DS", "Data Structures and Algorithms", "Algorithm design, complexity analysis"),
        ("cs.ET", "Emerging Technologies", "Post-CMOS, quantum computing, bio-inspired computing"),
        ("cs.FL", "Formal Languages and Automata Theory", "Automata, formal languages, grammars"),
        ("cs.GL", "General Literature", "General surveys, bibliographies"),
        ("cs.GR", "Graphics", "Computer graphics, rendering, visualization"),
        ("cs.GT", "Computer Science and Game Theory", "Algorithmic game theory, mechanism design"),
        ("cs.HC", "Human-Computer Interaction", "UI/UX, input devices, interaction techniques"),
        ("cs.IR", "Information Retrieval", "Search engines, text retrieval, ranking"),
        ("cs.IT", "Information Theory", "Shannon theory, coding, compression"),
        ("cs.LG", "Machine Learning", "All aspects of machine learning"),
        ("cs.LO", "Logic in Computer Science", "Formal logic, automated reasoning, type theory"),
        ("cs.MA", "Multiagent Systems", "Distributed AI, coordination, cooperation"),
        ("cs.MM", "Multimedia", "Audio, video, haptic data processing and delivery"),
        ("cs.MS", "Mathematical Software", "Software for mathematical computation"),
        ("cs.NA", "Numerical Analysis", "Numerical methods, algorithms, and analysis"),
        ("cs.NE", "Neural and Evolutionary Computing", "Neural networks, genetic algorithms"),
        ("cs.NI", "Networking and Internet Architecture", "Network protocols, architecture, performance"),
        ("cs.OH", "Other Computer Science", "Work not fitting other CS categories"),
        ("cs.OS", "Operating Systems", "OS design, kernels, virtualization"),
        ("cs.PF", "Performance", "Performance analysis and modeling"),
        ("cs.PL", "Programming Languages", "Language design, compilers, runtime systems"),
        ("cs.RO", "Robotics", "Robot control, planning, perception"),
        ("cs.SC", "Symbolic Computation", "Algebraic computation, term rewriting"),
        ("cs.SD", "Sound", "Audio processing, music information retrieval"),
        ("cs.SE", "Software Engineering", "Software design, testing, maintenance"),
        ("cs.SI", "Social and Information Networks", "Social network analysis, graph mining"),
        ("cs.SY", "Systems and Control", "Control theory, cyber-physical systems"),
    ],
    "econ": [
        ("econ.EM", "Econometrics", "Statistical methods in economics"),
        ("econ.GN", "General Economics", "General economics research"),
        ("econ.TH", "Theoretical Economics", "Economic theory, game theory in economics"),
    ],
    "eess": [
        ("eess.AS", "Audio and Speech Processing", "Speech recognition, audio analysis"),
        ("eess.IV", "Image and Video Processing", "Image/video coding, enhancement, analysis"),
        ("eess.SP", "Signal Processing", "Statistical signal processing, estimation, detection"),
        ("eess.SY", "Systems and Control", "Control systems, autonomous systems"),
    ],
    "math": [
        ("math.AC", "Commutative Algebra", "Rings, ideals, modules"),
        ("math.AG", "Algebraic Geometry", "Varieties, schemes, moduli spaces"),
        ("math.AP", "Analysis of PDEs", "Partial differential equations and their analysis"),
        ("math.AT", "Algebraic Topology", "Homotopy, homology, classifying spaces"),
        ("math.CA", "Classical Analysis and ODEs", "Real and complex analysis, ordinary differential equations"),
        ("math.CO", "Combinatorics", "Enumerative, extremal, and algebraic combinatorics"),
        ("math.CT", "Category Theory", "Categories, functors, universal properties"),
        ("math.CV", "Complex Variables", "Complex analysis, analytic functions"),
        ("math.DG", "Differential Geometry", "Manifolds, connections, curvature"),
        ("math.DS", "Dynamical Systems", "Ergodic theory, chaos, Hamiltonian systems"),
        ("math.FA", "Functional Analysis", "Banach/Hilbert spaces, operator theory"),
        ("math.GM", "General Mathematics", "Broad or elementary mathematical expositions"),
        ("math.GN", "General Topology", "Point-set topology, topological spaces"),
        ("math.GR", "Group Theory", "Group structure, representation, combinatorial group theory"),
        ("math.GT", "Geometric Topology", "Knot theory, 3-manifolds, low-dimensional topology"),
        ("math.HO", "History and Overview", "Historical studies, surveys, biographies"),
        ("math.IT", "Information Theory", "Mathematical aspects of information theory"),
        ("math.KT", "K-Theory and Homology", "Algebraic K-theory, cyclic homology"),
        ("math.LO", "Logic", "Model theory, set theory, computability"),
        ("math.MG", "Metric Geometry", "Distance geometry, metric spaces"),
        ("math.MP", "Mathematical Physics", "Rigorous results in mathematical physics"),
        ("math.NA", "Numerical Analysis", "Numerical methods and their analysis"),
        ("math.NT", "Number Theory", "Prime numbers, Diophantine equations, modular forms"),
        ("math.OA", "Operator Algebras", "C*-algebras, von Neumann algebras"),
        ("math.OC", "Optimization and Control", "Convex optimization, optimal control"),
        ("math.PR", "Probability", "Stochastic processes, random walks, limit theorems"),
        ("math.QA", "Quantum Algebra", "Quantum groups, Hopf algebras, noncommutative geometry"),
        ("math.RA", "Rings and Algebras", "Noncommutative algebra, representation theory"),
        ("math.RT", "Representation Theory", "Representations of groups and algebras"),
        ("math.SG", "Symplectic Geometry", "Symplectic manifolds, Poisson geometry"),
        ("math.SP", "Spectral Theory", "Spectra of operators, scattering theory"),
        ("math.ST", "Statistics Theory", "Mathematical foundations of statistics"),
    ],
    "physics": [
        ("astro-ph.CO", "Cosmology and Nongalactic Astrophysics", "Dark matter, dark energy, large-scale structure"),
        ("astro-ph.EP", "Earth and Planetary Astrophysics", "Exoplanets, solar system dynamics"),
        ("astro-ph.GA", "Astrophysics of Galaxies", "Galaxy formation, evolution, dynamics"),
        ("astro-ph.HE", "High Energy Astrophysical Phenomena", "Black holes, neutron stars, gamma-ray bursts"),
        ("astro-ph.IM", "Instrumentation and Methods for Astrophysics", "Telescopes, detectors, data analysis methods"),
        ("astro-ph.SR", "Solar and Stellar Astrophysics", "Stars, stellar evolution, the Sun"),
        ("cond-mat.dis-nn", "Disordered Systems and Neural Networks", "Spin glasses, random systems, neural networks"),
        ("cond-mat.mes-hall", "Mesoscale and Nanoscale Physics", "Quantum dots, nanowires, 2D materials"),
        ("cond-mat.mtrl-sci", "Materials Science", "Structure, properties, synthesis of materials"),
        ("cond-mat.other", "Other Condensed Matter", "Work not fitting other cond-mat categories"),
        ("cond-mat.quant-gas", "Quantum Gases", "Ultracold atoms, BEC, degenerate Fermi gases"),
        ("cond-mat.soft", "Soft Condensed Matter", "Polymers, colloids, liquid crystals, biomaterials"),
        ("cond-mat.stat-mech", "Statistical Mechanics", "Equilibrium and non-equilibrium statistical physics"),
        ("cond-mat.str-el", "Strongly Correlated Electrons", "Magnetism, superconductivity, Mott insulators"),
        ("cond-mat.supr-con", "Superconductivity", "Superconducting materials and phenomena"),
        ("gr-qc", "General Relativity and Quantum Cosmology", "Classical general relativity, quantum gravity"),
        ("hep-ex", "High Energy Physics - Experiment", "Experimental particle physics results"),
        ("hep-lat", "High Energy Physics - Lattice", "Lattice gauge theory, lattice QCD"),
        ("hep-ph", "High Energy Physics - Phenomenology", "Phenomenological particle physics models"),
        ("hep-th", "High Energy Physics - Theory", "Theoretical particle physics, string theory"),
        ("math-ph", "Mathematical Physics", "Rigorous mathematical structures in physics"),
        ("nlin.AO", "Adaptation and Self-Organizing Systems", "Complex systems, pattern formation"),
        ("nlin.CD", "Chaotic Dynamics", "Deterministic chaos, fractals"),
        ("nlin.CG", "Cellular Automata and Lattice Gases", "Discrete dynamical systems on lattices"),
        ("nlin.PS", "Pattern Formation and Solitons", "Spatial/temporal patterns, solitons"),
        ("nlin.SI", "Exactly Solvable and Integrable Systems", "Integrable PDEs, inverse scattering"),
        ("nucl-ex", "Nuclear Experiment", "Experimental nuclear physics"),
        ("nucl-th", "Nuclear Theory", "Theoretical nuclear structure and reactions"),
        ("physics.acc-ph", "Accelerator Physics", "Particle accelerators, beam dynamics"),
        ("physics.ao-ph", "Atmospheric and Oceanic Physics", "Climate, meteorology, ocean dynamics"),
        ("physics.app-ph", "Applied Physics", "Device physics, instrumentation"),
        ("physics.atm-clus", "Atomic and Molecular Clusters", "Cluster physics, nanoparticles"),
        ("physics.atom-ph", "Atomic Physics", "Atomic structure, interactions, spectroscopy"),
        ("physics.bio-ph", "Biological Physics", "Physics of biological systems"),
        ("physics.chem-ph", "Chemical Physics", "Quantum chemistry, molecular dynamics"),
        ("physics.class-ph", "Classical Physics", "Classical mechanics, electromagnetism"),
        ("physics.comp-ph", "Computational Physics", "Numerical simulation in physics"),
        ("physics.data-an", "Data Analysis, Statistics and Probability", "Data analysis methods in physics"),
        ("physics.ed-ph", "Physics Education", "Teaching and learning physics"),
        ("physics.flu-dyn", "Fluid Dynamics", "Fluid flow, turbulence, aerodynamics"),
        ("physics.gen-ph", "General Physics", "Broad or speculative physics topics"),
        ("physics.geo-ph", "Geophysics", "Earth physics, seismology"),
        ("physics.hist-ph", "History and Philosophy of Physics", "Historical studies of physics"),
        ("physics.ins-det", "Instrumentation and Detectors", "Scientific instruments and detectors"),
        ("physics.med-ph", "Medical Physics", "Physics applied to medicine"),
        ("physics.optics", "Optics", "Light, lasers, photonics"),
        ("physics.plasm-ph", "Plasma Physics", "Plasma theory, fusion, space plasmas"),
        ("physics.pop-ph", "Popular Physics", "Physics for general audiences"),
        ("physics.soc-ph", "Physics and Society", "Social and policy aspects of physics"),
        ("physics.space-ph", "Space Physics", "Heliosphere, magnetosphere, space weather"),
        ("quant-ph", "Quantum Physics", "Quantum mechanics, quantum information, entanglement"),
    ],
    "q-bio": [
        ("q-bio.BM", "Biomolecules", "Structure, function, and dynamics of biomolecules"),
        ("q-bio.CB", "Cell Behavior", "Cellular processes, signaling, motility"),
        ("q-bio.GN", "Genomics", "Genome analysis, sequencing, gene regulation"),
        ("q-bio.MN", "Molecular Networks", "Gene regulatory networks, metabolic pathways"),
        ("q-bio.NC", "Neurons and Cognition", "Neural systems, cognition, brain function"),
        ("q-bio.OT", "Other Quantitative Biology", "Topics not fitting other q-bio categories"),
        ("q-bio.PE", "Populations and Evolution", "Population genetics, evolutionary dynamics"),
        ("q-bio.QM", "Quantitative Methods", "Statistical and computational methods in biology"),
        ("q-bio.SC", "Subcellular Processes", "Intracellular transport, organelle function"),
        ("q-bio.TO", "Tissues and Organs", "Multicellular organization, organ function"),
    ],
    "q-fin": [
        ("q-fin.CP", "Computational Finance", "Numerical methods in finance"),
        ("q-fin.EC", "Economics", "Microeconomics, macroeconomics as related to finance"),
        ("q-fin.GN", "General Finance", "Broad or introductory finance topics"),
        ("q-fin.MF", "Mathematical Finance", "Stochastic calculus, derivative pricing"),
        ("q-fin.PM", "Portfolio Management", "Asset allocation, risk management"),
        ("q-fin.PR", "Pricing of Securities", "Option pricing, fixed income"),
        ("q-fin.RM", "Risk Management", "Credit risk, market risk, operational risk"),
        ("q-fin.ST", "Statistical Finance", "Empirical finance, econometric models"),
        ("q-fin.TR", "Trading and Market Microstructure", "Market design, order execution"),
    ],
    "stat": [
        ("stat.AP", "Applications", "Applied statistics across disciplines"),
        ("stat.CO", "Computation", "Statistical computing, algorithms, software"),
        ("stat.ME", "Methodology", "Statistical methods and procedures"),
        ("stat.ML", "Machine Learning", "Statistical learning theory and methods"),
        ("stat.OT", "Other Statistics", "Work not fitting other statistics categories"),
        ("stat.TH", "Statistics Theory", "Theoretical foundations of statistics"),
    ],
}

_GROUP_NAMES: dict[str, str] = {
    "cs": "Computer Science",
    "econ": "Economics",
    "eess": "Electrical Engineering and Systems Science",
    "math": "Mathematics",
    "physics": "Physics",
    "q-bio": "Quantitative Biology",
    "q-fin": "Quantitative Finance",
    "stat": "Statistics",
}

# Build the lookup structures
_ALL_GROUPS: list[CategoryGroup] = []
_ALL_CATEGORIES_BY_ID: dict[str, Category] = {}

for gid, gname in _GROUP_NAMES.items():
    cats = []
    for cid, cname, cdesc in _CATEGORIES.get(gid, []):
        cat = Category(id=cid, name=cname, group=gid, description=cdesc)
        cats.append(cat)
        _ALL_CATEGORIES_BY_ID[cid] = cat
    _ALL_GROUPS.append(CategoryGroup(id=gid, name=gname, categories=cats))


def get_all_groups() -> list[CategoryGroup]:
    """Return all arXiv category groups with their categories."""
    return _ALL_GROUPS


def get_group(group_id: str) -> CategoryGroup | None:
    """Return a single category group by its ID (e.g., 'cs', 'math')."""
    for g in _ALL_GROUPS:
        if g.id == group_id:
            return g
    return None


def get_category(cat_id: str) -> Category | None:
    """Return a single category by its ID (e.g., 'cs.AI')."""
    return _ALL_CATEGORIES_BY_ID.get(cat_id)


def get_all_category_ids() -> list[str]:
    """Return all valid arXiv category IDs."""
    return list(_ALL_CATEGORIES_BY_ID.keys())


def is_valid_category(cat_id: str) -> bool:
    """Check if a category ID is valid."""
    return cat_id in _ALL_CATEGORIES_BY_ID
