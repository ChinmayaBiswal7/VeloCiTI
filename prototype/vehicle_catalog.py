"""
vehicle_catalog.py - Comprehensive Global & Indian Automotive Vehicle Knowledge Base
Contains visual feature specifications for over 80+ vehicle models across 16 major manufacturers:
- German Luxury: Volkswagen, BMW, Mercedes-Benz, Audi, Porsche
- European: Skoda, Volvo, Land Rover / Range Rover
- Indian Powerhouses: Tata Motors, Mahindra
- Japanese Giants: Toyota, Honda, Maruti Suzuki
- Korean & Global: Hyundai, Kia, MG Motor, Ford
"""

# Grille Architecture Constants
GRILLE_KIDNEY_DUAL        = "KIDNEY_DUAL"          # BMW signature twin kidney
GRILLE_SINGLEFRAME_HEX    = "SINGLEFRAME_HEX"      # Audi hexagonal/octagonal frame
GRILLE_PANAMERICANA_STAR  = "PANAMERICANA_STAR"    # Mercedes 3-pointed star with louvers/vertical
GRILLE_CHROME_LOUVER      = "CHROME_LOUVER"        # Volkswagen horizontal chrome slats
GRILLE_VERTICAL_SLATS     = "VERTICAL_SLATS"       # Mahindra / Jeep upright teeth
GRILLE_PARAMETRIC_JEWEL   = "PARAMETRIC_JEWEL"     # Hyundai dark chrome geometric jewel
GRILLE_TIGER_NOSE         = "TIGER_NOSE"           # Kia indented tiger-nose
GRILLE_BUTTERFLY_RIBBED   = "BUTTERFLY_RIBBED"     # Skoda signature vertical rib butterfly
GRILLE_SOLID_WING         = "SOLID_WING"           # Honda thick chrome upper bar
GRILLE_HONEYCOMB_HEX      = "HONEYCOMB_HEX"        # Maruti / Ford hexagonal honeycomb mesh
GRILLE_HUMANITY_LINE      = "HUMANITY_LINE"        # Tata Motors sleek chrome underline
GRILLE_TRAPEZOID_MASSIVE  = "TRAPEZOID_MASSIVE"    # Toyota Fortuner / Hilux bold trapezoid
GRILLE_STAR_DIAMOND       = "STAR_DIAMOND"         # MG starry sky diamond chrome pins
GRILLE_IRON_MARK          = "IRON_MARK"            # Volvo diagonal slash with iron mark

# Emblem Shapes
EMBLEM_CIRCLE       = "CIRCLE"       # VW, BMW, Mercedes, Nissan
EMBLEM_STAR_3       = "STAR_3"       # Mercedes-Benz 3-pointed star
EMBLEM_FOUR_RINGS   = "FOUR_RINGS"   # Audi interlocking 4 rings
EMBLEM_OVAL         = "OVAL"         # Hyundai, Ford, Toyota
EMBLEM_TWIN_PEAKS   = "TWIN_PEAKS"   # Mahindra new chrome wings
EMBLEM_SHIELD       = "SHIELD"       # Porsche, Skoda, Volvo
EMBLEM_OCTAGON      = "OCTAGON"      # MG Motor
EMBLEM_RECTANGLE    = "RECTANGLE"    # Land Rover green oval/badge
EMBLEM_LETTER_S     = "LETTER_S"     # Suzuki S logo
EMBLEM_LETTER_H     = "LETTER_H"     # Honda bold H


VEHICLE_CATALOG = [
    # =========================================================================
    # VOLKSWAGEN (Germany)
    # =========================================================================
    {
        "make": "Volkswagen",
        "model": "Taigun",
        "series": "Compact SUV / Crossover",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (0.95, 1.30),
        "ground_clearance": "High (205 mm)",
        "grille_type": GRILLE_CHROME_LOUVER,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Silver Grey", "Red", "Yellow", "Black", "Dark Blue"],
        "features": "Circular Center Chrome Emblem, Dual Horizontal Chrome Louvers, Integrated Silver Roof Rails, Distinctive LED DRL Eyebrows, High Bonnet",
        "typical_confidence": 0.95
    },
    {
        "make": "Volkswagen",
        "model": "Virtus",
        "series": "Executive Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.38, 1.85),
        "ground_clearance": "Medium (179 mm)",
        "grille_type": GRILLE_CHROME_LOUVER,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Red", "Carbon Steel Grey", "Black", "Dark Blue", "Yellow"],
        "features": "Circular VW Front Crest, Slim Chrome Upper Grille, Wide Aerodynamic Lower Air Dam, LED Headlamps with L-Shaped DRLs",
        "typical_confidence": 0.93
    },
    {
        "make": "Volkswagen",
        "model": "Tiguan",
        "series": "Premium Mid-Size SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.35),
        "ground_clearance": "High (200 mm)",
        "grille_type": GRILLE_CHROME_LOUVER,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Silver Grey", "Black", "Dark Blue"],
        "features": "Wide Quad-Bar Chrome Grille, IQ.Light Matrix LED Headlamps, Muscular Wheel Arches, Chrome Window Beltline",
        "typical_confidence": 0.92
    },
    {
        "make": "Volkswagen",
        "model": "Polo",
        "series": "Sport Hatchback",
        "body_style": "Hatchback / Compact Car",
        "aspect_ratio": (0.95, 1.25),
        "ground_clearance": "Low-Medium (168 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Red", "Silver Grey", "Dark Blue", "Black"],
        "features": "Clean Horizontal Beltline, Central Circle Emblem, Honeycomb Lower Mesh, Compact Squarish Tail Lamp Profile",
        "typical_confidence": 0.91
    },

    # =========================================================================
    # BMW (Germany)
    # =========================================================================
    {
        "make": "BMW",
        "model": "3 Series / M340i",
        "series": "Luxury Sport Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.42, 1.88),
        "ground_clearance": "Low (140 mm)",
        "grille_type": GRILLE_KIDNEY_DUAL,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["Black", "White", "Dark Blue", "Silver Grey", "Red"],
        "features": "Signature Twin Kidney Grille with Chrome or Shadowline Surround, Twin L-Shaped DRLs (Angel Eyes), Long Hood, Hofmeister Kink",
        "typical_confidence": 0.96
    },
    {
        "make": "BMW",
        "model": "X1 / X3",
        "series": "Luxury Sport Activity Vehicle (SAV)",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.36),
        "ground_clearance": "High (204 mm)",
        "grille_type": GRILLE_KIDNEY_DUAL,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Black", "Dark Blue", "Silver Grey", "Green"],
        "features": "Upright Dominant Kidney Grille, Inverted L LED DRLs, Sculpted Flared Wheel Arches, Integrated Roof Spoiler",
        "typical_confidence": 0.94
    },
    {
        "make": "BMW",
        "model": "X5 / X7",
        "series": "Flagship Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.30),
        "ground_clearance": "High (214 mm)",
        "grille_type": GRILLE_KIDNEY_DUAL,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["Black", "White", "Dark Blue", "Silver Grey"],
        "features": "Massive Illuminated Iconic Glow Kidney Grille, Slim Split Laser Headlamps, Stately Tall Profile, Dual Exhaust Apertures",
        "typical_confidence": 0.95
    },
    {
        "make": "BMW",
        "model": "5 Series",
        "series": "Executive Luxury Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.45, 1.90),
        "ground_clearance": "Low (145 mm)",
        "grille_type": GRILLE_KIDNEY_DUAL,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["Black", "White", "Silver Grey", "Dark Blue"],
        "features": "Wide Stance, Prominent Twin Kidney Grille with Active Air Flaps, Long Wheelbase, Sleek LED Light Bars",
        "typical_confidence": 0.93
    },

    # =========================================================================
    # MERCEDES-BENZ (Germany)
    # =========================================================================
    {
        "make": "Mercedes-Benz",
        "model": "C-Class / E-Class",
        "series": "Luxury Executive Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.40, 1.88),
        "ground_clearance": "Low (145 mm)",
        "grille_type": GRILLE_PANAMERICANA_STAR,
        "emblem_shape": EMBLEM_STAR_3,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red"],
        "features": "Prominent Central 3-Pointed Star Crest, Star-Pattern Diamond Grille or Twin Chrome Louvers, Digital Light Eyebrows, Curved Roofline",
        "typical_confidence": 0.96
    },
    {
        "make": "Mercedes-Benz",
        "model": "GLA / GLB",
        "series": "Compact Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.12, 1.38),
        "ground_clearance": "High (183 mm)",
        "grille_type": GRILLE_PANAMERICANA_STAR,
        "emblem_shape": EMBLEM_STAR_3,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red"],
        "features": "Single Horizontal Louver with Central Star, Simulated Front Underride Guard, Power Domes on Bonnet, Roof Rails",
        "typical_confidence": 0.94
    },
    {
        "make": "Mercedes-Benz",
        "model": "GLC / GLE / GLS",
        "series": "Full-Size Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.32),
        "ground_clearance": "High (201 mm)",
        "grille_type": GRILLE_PANAMERICANA_STAR,
        "emblem_shape": EMBLEM_STAR_3,
        "colors": ["Black", "White", "Silver Grey", "Dark Blue"],
        "features": "Twin-Louver Chrome Grille or Vertical Panamericana AMG Slats, Multi-Beam LED Headlamps, Running Boards, Muscular Stance",
        "typical_confidence": 0.95
    },

    # =========================================================================
    # AUDI (Germany)
    # =========================================================================
    {
        "make": "Audi",
        "model": "A4 / A6",
        "series": "Executive Luxury Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.42, 1.88),
        "ground_clearance": "Low (145 mm)",
        "grille_type": GRILLE_SINGLEFRAME_HEX,
        "emblem_shape": EMBLEM_FOUR_RINGS,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red"],
        "features": "Vast Singleframe Hexagonal Grille, Interlocking 4-Ring Emblem in Upper Center, Matrix LED Segmented DRLs, Sharp Shoulder Crease",
        "typical_confidence": 0.96
    },
    {
        "make": "Audi",
        "model": "Q3 / Q5 / Q7",
        "series": "Quattro Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.34),
        "ground_clearance": "High (200 mm)",
        "grille_type": GRILLE_SINGLEFRAME_HEX,
        "emblem_shape": EMBLEM_FOUR_RINGS,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue"],
        "features": "Octagonal Singleframe Grille with Vertical Chrome Inlays, High Ground Clearance, Four Rings on Grille, OLED Taillight Signatures",
        "typical_confidence": 0.95
    },

    # =========================================================================
    # HYUNDAI (South Korea)
    # =========================================================================
    {
        "make": "Hyundai",
        "model": "Creta",
        "series": "Best-Selling Mid-Size SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.35),
        "ground_clearance": "High (190 mm)",
        "grille_type": GRILLE_PARAMETRIC_JEWEL,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red", "Green"],
        "features": "Parametric Black Chrome Jewel Grille with Hidden DRLs, Split Bumper-Mounted Quad-LED Headlamps, Muscular Cladding, Silver C-Pillar Arch",
        "typical_confidence": 0.95
    },
    {
        "make": "Hyundai",
        "model": "Venue",
        "series": "Compact Urban SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.30),
        "ground_clearance": "High (195 mm)",
        "grille_type": GRILLE_PARAMETRIC_JEWEL,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Silver Grey", "Red", "Black", "Dark Blue"],
        "features": "Dark Chrome Grille with Rectangular Motifs, Connecting Full-Width LED Tail Bar, Split Headlights with Squarish DRL Rings",
        "typical_confidence": 0.92
    },
    {
        "make": "Hyundai",
        "model": "i20",
        "series": "Premium Hatchback",
        "body_style": "Hatchback / Compact Car",
        "aspect_ratio": (0.95, 1.25),
        "ground_clearance": "Low-Medium (170 mm)",
        "grille_type": GRILLE_PARAMETRIC_JEWEL,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Red", "Silver Grey", "Dark Blue", "Black"],
        "features": "Gloss Black Cascading Mesh Grille, Swept-Back Projector Headlamps, Z-Shaped LED Tail Lamps, Low Sleek Aero Stance",
        "typical_confidence": 0.91
    },
    {
        "make": "Hyundai",
        "model": "Verna",
        "series": "Futuristic Fastback Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.40, 1.85),
        "ground_clearance": "Medium (165 mm)",
        "grille_type": GRILLE_PARAMETRIC_JEWEL,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Black", "Silver Grey", "Red", "Dark Blue"],
        "features": "Horizon-to-Horizon Full Width Seamless LED DRL Bar, Parametric Faceted Body Sides, Fastback Sloping Rear Roofline",
        "typical_confidence": 0.94
    },

    # =========================================================================
    # TATA MOTORS (India)
    # =========================================================================
    {
        "make": "Tata Motors",
        "model": "Nexon",
        "series": "Best-Selling Compact SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.32),
        "ground_clearance": "High (208 mm)",
        "grille_type": GRILLE_HUMANITY_LINE,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Dark Blue", "Red", "Silver Grey", "Black", "Purple"],
        "features": "Sequential Bi-Function LED DRLs on Bonnet Edge, Upper Gloss Black Slit, Lower Air Dam with Tri-Arrow Inlays, High Ground Clearance",
        "typical_confidence": 0.95
    },
    {
        "make": "Tata Motors",
        "model": "Harrier / Safari",
        "series": "Flagship OMEGARC SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.28),
        "ground_clearance": "High (205 mm)",
        "grille_type": GRILLE_HUMANITY_LINE,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Black", "Dark Blue", "Silver Grey", "Gold"],
        "features": "End-to-End Connected LED Light Strip, Parametric Grille with Warm Chrome Accents, Muscular Flared Haunches, Imposing Stance",
        "typical_confidence": 0.94
    },
    {
        "make": "Tata Motors",
        "model": "Punch",
        "series": "Micro SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.00, 1.25),
        "ground_clearance": "High (187 mm)",
        "grille_type": GRILLE_HUMANITY_LINE,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["White", "Red", "Dark Blue", "Silver Grey", "Orange"],
        "features": "High Seated Upright Stance, Bold Cladding All Round, Tri-Arrow Lower Bumper Mesh, High Bonnet Line",
        "typical_confidence": 0.91
    },
    {
        "make": "Tata Motors",
        "model": "Altroz",
        "series": "Premium Hatchback",
        "body_style": "Hatchback / Compact Car",
        "aspect_ratio": (0.95, 1.25),
        "ground_clearance": "Medium (165 mm)",
        "grille_type": GRILLE_HUMANITY_LINE,
        "emblem_shape": EMBLEM_CIRCLE,
        "colors": ["Gold", "White", "Silver Grey", "Red", "Dark Blue", "Black"],
        "features": "Shooting Star Roofline, Piano Black Sashing Below Windows, Sweptback Dual-Chamber Headlamps",
        "typical_confidence": 0.90
    },

    # =========================================================================
    # MAHINDRA (India)
    # =========================================================================
    {
        "make": "Mahindra",
        "model": "Thar",
        "series": "Iconic 4x4 Off-Roader",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (0.95, 1.18),
        "ground_clearance": "Very High (226 mm)",
        "grille_type": GRILLE_VERTICAL_SLATS,
        "emblem_shape": EMBLEM_RECTANGLE,
        "colors": ["Black", "Red", "Silver Grey", "White", "Brown_Maroon"],
        "features": "Classic 7-Slot Vertical Front Grille, Round Halogen/LED Headlamps, External Bonnet Latches, Exposed Door Hinges, Boxy Upright Stance",
        "typical_confidence": 0.97
    },
    {
        "make": "Mahindra",
        "model": "Scorpio-N / Scorpio Classic",
        "series": "Rugged Ladder-Frame SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.02, 1.24),
        "ground_clearance": "High (205 mm)",
        "grille_type": GRILLE_VERTICAL_SLATS,
        "emblem_shape": EMBLEM_TWIN_PEAKS,
        "colors": ["Black", "White", "Silver Grey", "Dark Blue", "Red"],
        "features": "Bold Chrome Vertical Slatted Grille with New Twin Peaks Emblem, Dual Barrel LED Projector Headlamps, Sting-Like DRL Surrounds, Tall Boxy Stance",
        "typical_confidence": 0.96
    },
    {
        "make": "Mahindra",
        "model": "XUV700",
        "series": "Premium Tech SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.30),
        "ground_clearance": "High (200 mm)",
        "grille_type": GRILLE_VERTICAL_SLATS,
        "emblem_shape": EMBLEM_TWIN_PEAKS,
        "colors": ["Midnight Black", "White", "Dark Blue", "Silver Grey", "Red"],
        "features": "Distinctive C-Shaped Extended LED DRLs, Vertical Chrome Louvers in Piano Black Grille, Flush Smart Door Handles, Wide Aggressive Track",
        "typical_confidence": 0.95
    },
    {
        "make": "Mahindra",
        "model": "Bolero / Bolero Neo",
        "series": "Utility Workhorse SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (0.95, 1.18),
        "ground_clearance": "High (180 mm)",
        "grille_type": GRILLE_VERTICAL_SLATS,
        "emblem_shape": EMBLEM_TWIN_PEAKS,
        "colors": ["White", "Silver Grey", "Brown_Maroon"],
        "features": "Traditional Squarish Metal Bumpers, Rugged Vertical Slats, High Rectangular Profile, Metal Step Bars",
        "typical_confidence": 0.93
    },

    # =========================================================================
    # TOYOTA (Japan)
    # =========================================================================
    {
        "make": "Toyota",
        "model": "Fortuner / Legender",
        "series": "Dominant Full-Size 4x4 SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.02, 1.24),
        "ground_clearance": "Very High (225 mm)",
        "grille_type": GRILLE_TRAPEZOID_MASSIVE,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Black", "Silver Grey", "Brown_Maroon"],
        "features": "Vast Wave-Pattern Mesh Upper Grille, Catamaran-Style Bumper, Sharp Split Quad-LED Headlamps with Waterfall DRLs, High Imposing Stance",
        "typical_confidence": 0.96
    },
    {
        "make": "Toyota",
        "model": "Innova Crysta / Hycross",
        "series": "Premium Multi-Utility Vehicle (MUV)",
        "body_style": "Passenger Bus / Van",
        "aspect_ratio": (1.15, 1.45),
        "ground_clearance": "High (185 mm)",
        "grille_type": GRILLE_TRAPEZOID_MASSIVE,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["Silver Grey", "White", "Black", "Brown_Maroon"],
        "features": "Prominent Hexagonal Chrome Slatted Grille, Sweptback Angular Headlights, High Roof Van Silhouette, Expansive Quarter Glass",
        "typical_confidence": 0.94
    },
    {
        "make": "Toyota",
        "model": "Urban Cruiser Hyryder",
        "series": "Strong Hybrid SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.34),
        "ground_clearance": "High (208 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Silver Grey", "Red", "Dark Blue", "Black"],
        "features": "Crystal Acrylic Grille with Chrome Garnish, Twin LED Daytime Running Lamps, Flared Wheel Arches, Full Width Tail Garnish",
        "typical_confidence": 0.92
    },

    # =========================================================================
    # MARUTI SUZUKI (India / Japan)
    # =========================================================================
    {
        "make": "Maruti Suzuki",
        "model": "Swift",
        "series": "Iconic Compact Hatchback",
        "body_style": "Hatchback / Compact Car",
        "aspect_ratio": (0.95, 1.25),
        "ground_clearance": "Low-Medium (163 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_LETTER_S,
        "colors": ["Red", "White", "Silver Grey", "Dark Blue", "Orange"],
        "features": "Single-Frame Gloss Black Honeycomb Grille with Center S, Sweptback Projector Headlamps, Blacked-Out A and B Pillars (Floating Roof)",
        "typical_confidence": 0.94
    },
    {
        "make": "Maruti Suzuki",
        "model": "Brezza",
        "series": "Urban Compact SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.32),
        "ground_clearance": "High (200 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_LETTER_S,
        "colors": ["Red", "White", "Silver Grey", "Dark Blue", "Khaki"],
        "features": "Dual-Tone Gunmetal Geometric Grille with Chrome Bar, L-Shaped Twin Projector DRLs, Silver Skid Plates, Cladded Wheel Arches",
        "typical_confidence": 0.93
    },
    {
        "make": "Maruti Suzuki",
        "model": "Baleno",
        "series": "Premium Nexa Hatchback",
        "body_style": "Hatchback / Compact Car",
        "aspect_ratio": (0.98, 1.28),
        "ground_clearance": "Low-Medium (170 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_LETTER_S,
        "colors": ["Dark Blue", "White", "Silver Grey", "Red", "Black"],
        "features": "NEXWave Wave-Pattern Grille with Wide Chrome Wing, Signature 3-Block Matrix LED DRLs, Curvaceous Liquid-Flow Body",
        "typical_confidence": 0.92
    },
    {
        "make": "Maruti Suzuki",
        "model": "Dzire",
        "series": "Compact Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.35, 1.75),
        "ground_clearance": "Medium (163 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_LETTER_S,
        "colors": ["White", "Silver Grey", "Dark Blue", "Red", "Brown_Maroon"],
        "features": "Large Hexagonal Grille with Multi-Horizontal Slats, Chrome Accents around Fog Lamps, Short High Deck Boot Lid",
        "typical_confidence": 0.91
    },
    {
        "make": "Maruti Suzuki",
        "model": "Grand Vitara",
        "series": "AllGrip Hybrid SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.35),
        "ground_clearance": "High (208 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_LETTER_S,
        "colors": ["White", "Dark Blue", "Silver Grey", "Red", "Black"],
        "features": "High Gloss Black Multi-Element Grille with Dark Chrome Bar, 3-Point LED DRLs, Swept Wheel Arches, Full Width LED Light Bar",
        "typical_confidence": 0.93
    },

    # =========================================================================
    # KIA (South Korea)
    # =========================================================================
    {
        "make": "Kia",
        "model": "Seltos",
        "series": "Tech-Loaded Mid-Size SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.35),
        "ground_clearance": "High (190 mm)",
        "grille_type": GRILLE_TIGER_NOSE,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Black", "Silver Grey", "Red", "Dark Blue", "Green"],
        "features": "Signature Knurled Chrome Tiger-Nose Grille, Extended Sweeper LED Lightbar, Crown Jewel LED Headlamps with Ice-Cube Fog Lamps",
        "typical_confidence": 0.95
    },
    {
        "make": "Kia",
        "model": "Sonet",
        "series": "Compact Wild SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.30),
        "ground_clearance": "High (205 mm)",
        "grille_type": GRILLE_TIGER_NOSE,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Red", "Black", "Silver Grey", "Dark Blue"],
        "features": "Geometric Knurled Tiger-Nose Grille with Red Accents, Star Map LED DRLs, Chunky Dual Muffler Design, Roof Rails",
        "typical_confidence": 0.93
    },
    {
        "make": "Kia",
        "model": "Carens",
        "series": "Recreational 6/7 Seater Vehicle",
        "body_style": "Passenger Bus / Van",
        "aspect_ratio": (1.15, 1.42),
        "ground_clearance": "High (195 mm)",
        "grille_type": GRILLE_TIGER_NOSE,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["Dark Blue", "Silver Grey", "White", "Black", "Brown_Maroon"],
        "features": "Digital Tiger Face, Closed Upper Radiator Grille with Star Map LED DRLs, Aerodynamic Low Bumper Air Intake",
        "typical_confidence": 0.92
    },

    # =========================================================================
    # SKODA (Czech Republic)
    # =========================================================================
    {
        "make": "Skoda",
        "model": "Kushaq",
        "series": "European Compact SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.32),
        "ground_clearance": "High (188 mm)",
        "grille_type": GRILLE_BUTTERFLY_RIBBED,
        "emblem_shape": EMBLEM_SHIELD,
        "colors": ["Orange", "White", "Silver Grey", "Red", "Black", "Dark Blue"],
        "features": "Signature Chromed Butterfly Grille with Dual Vertical Ribs, Split Headlamp Design with Sharp Crystalline DRLs, Chunky Skid Plate",
        "typical_confidence": 0.94
    },
    {
        "make": "Skoda",
        "model": "Slavia / Octavia",
        "series": "European Luxury Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.40, 1.86),
        "ground_clearance": "Medium (179 mm)",
        "grille_type": GRILLE_BUTTERFLY_RIBBED,
        "emblem_shape": EMBLEM_SHIELD,
        "colors": ["Dark Blue", "White", "Silver Grey", "Red", "Black"],
        "features": "Vertical Rib Butterfly Grille, L-Shaped Crystalline LED DRLs, Coupe-Like Sloping C-Pillar, Notchback Rear Trunk Opening",
        "typical_confidence": 0.93
    },

    # =========================================================================
    # HONDA (Japan)
    # =========================================================================
    {
        "make": "Honda",
        "model": "City",
        "series": "Legendary Mid-Size Sedan",
        "body_style": "Sedan (Low Stance / Long Profile)",
        "aspect_ratio": (1.40, 1.86),
        "ground_clearance": "Medium (165 mm)",
        "grille_type": GRILLE_SOLID_WING,
        "emblem_shape": EMBLEM_LETTER_H,
        "colors": ["White", "Silver Grey", "Red", "Dark Blue", "Brown_Maroon"],
        "features": "Solid Wing Face Thick Chrome Upper Bar, 9-Array Inline Jewel-Eye LED Headlamps, Z-Shaped 3D Wrap-Around Tail Lamps",
        "typical_confidence": 0.94
    },
    {
        "make": "Honda",
        "model": "Elevate",
        "series": "Global Urban SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.32),
        "ground_clearance": "Very High (220 mm)",
        "grille_type": GRILLE_SOLID_WING,
        "emblem_shape": EMBLEM_LETTER_H,
        "colors": ["White", "Orange", "Silver Grey", "Red", "Black", "Dark Blue"],
        "features": "High Upright Stance, Chunky Hexagonal Grille with Top Chrome Bar Joining Slim LED DRLs, Massive 220mm Ground Clearance",
        "typical_confidence": 0.93
    },

    # =========================================================================
    # MG MOTOR (Morris Garages / SAIC)
    # =========================================================================
    {
        "make": "MG Motor",
        "model": "Hector / Hector Plus",
        "series": "Internet Connected SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.30),
        "ground_clearance": "High (192 mm)",
        "grille_type": GRILLE_STAR_DIAMOND,
        "emblem_shape": EMBLEM_OCTAGON,
        "colors": ["White", "Black", "Silver Grey", "Red", "Brown_Maroon"],
        "features": "Massive Argyle-Inspired Starry Chrome Diamond Grille, Octagonal MG Crest, High Split LED DRLs with Lower Bumper Main Headlamps",
        "typical_confidence": 0.94
    },
    {
        "make": "MG Motor",
        "model": "ZS EV / Astor",
        "series": "Electric / Urban SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.08, 1.32),
        "ground_clearance": "High (180 mm)",
        "grille_type": GRILLE_STAR_DIAMOND,
        "emblem_shape": EMBLEM_OCTAGON,
        "colors": ["White", "Red", "Silver Grey", "Black"],
        "features": "Celestial Diamond Chrome Grille (or Body-Colored Closed EV Grille), Hawk-Eye LED Headlights, Compact European Proportions",
        "typical_confidence": 0.92
    },

    # =========================================================================
    # LAND ROVER / RANGE ROVER (UK)
    # =========================================================================
    {
        "make": "Land Rover",
        "model": "Defender / Range Rover Evoque",
        "series": "Luxury Expedition 4x4",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (0.95, 1.25),
        "ground_clearance": "Very High (228 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_RECTANGLE,
        "colors": ["White", "Black", "Silver Grey", "Green", "Brown_Maroon"],
        "features": "Boxy Monocoque Silhouette, Symmetrical Semi-Circular LED Headlights, Alpine Light Roof Windows, External Rear Spare Wheel",
        "typical_confidence": 0.95
    },

    # =========================================================================
    # VOLVO (Sweden)
    # =========================================================================
    {
        "make": "Volvo",
        "model": "XC40 / XC60 / XC90",
        "series": "Scandinavian Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.05, 1.32),
        "ground_clearance": "High (211 mm)",
        "grille_type": GRILLE_IRON_MARK,
        "emblem_shape": EMBLEM_SHIELD,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red"],
        "features": "Diagonal Iron Mark Slash Across Concave Grille, Thor's Hammer T-Shaped LED DRLs, Sculpted Scandinavian Minimalist Facade",
        "typical_confidence": 0.95
    },

    # =========================================================================
    # PORSCHE (Germany)
    # =========================================================================
    {
        "make": "Porsche",
        "model": "Macan / Cayenne",
        "series": "Performance Luxury SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.10, 1.35),
        "ground_clearance": "High (190 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_SHIELD,
        "colors": ["White", "Black", "Silver Grey", "Dark Blue", "Red"],
        "features": "Four-Point LED Daytime Running Light Pods, Clamshell Hood, Sloping Flyline Roofline, Three-Stage Large Front Air Inlets",
        "typical_confidence": 0.94
    },

    # =========================================================================
    # FORD (USA)
    # =========================================================================
    {
        "make": "Ford",
        "model": "EcoSport / Endeavour",
        "series": "Rugged Terrain SUV",
        "body_style": "SUV / Compact Crossover",
        "aspect_ratio": (1.02, 1.28),
        "ground_clearance": "Very High (210 mm)",
        "grille_type": GRILLE_HONEYCOMB_HEX,
        "emblem_shape": EMBLEM_OVAL,
        "colors": ["White", "Black", "Silver Grey", "Red", "Dark Blue"],
        "features": "Large Trapezoidal Grille with Chrome or Honeycomb Mesh, C-Shaped Fog Lamp Pockets, Chunky Muscular Stance",
        "typical_confidence": 0.93
    }
]

def get_catalog():
    return VEHICLE_CATALOG
