"""
Common resource for muscle annotation terms.
"""

# convention: preferred name, preferred id, followed by any other ids and alternative names
muscle_terms = [
    ("acromial part (TA98)", "ILX:0743224"),
    ("anterior end of acromial origin", "None"),
    ("brachioradialis", "UBERON:0011011", "ILX:0724973"),
    ("biceps femoris", "UBERON:0001374 ", "ILX:0730686"),
    ("deltoid", "UBERON:0001476", "FMA:32521", "ILX:0731247"),
    ("midpoint of deltoid tuberosity", "None"),
    ("muscle", "UBERON:0001630", "ILX:0107218"),
    ("posterior end of acromial origin", "None")
    ]


def get_muscle_term(name : str):
    """
    Find term by matching name to any identifier held for a term.
    Raise exception if name not found.
    :return ( preferred name, preferred id )
    """
    for term in muscle_terms:
        if name in term:
            return ( term[0], term[1] )
    raise NameError("Muscle annotation term '" + name + "' not found.")
