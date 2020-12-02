"""
Common resource for stomach annotation terms.
"""

# convention: preferred name, preferred id, followed by any other ids and alternative names
stomach_terms = [
    ("Longitudinal muscle layer of stomach", "ILX:0772619"),
    ("mucosa of stomach", "FMA:14907", "UBERON:0001199", "ILX:0736669"),
    ("myenteric nerve plexus", "FMA:63252", "UBERON:0002439", "ILX:0725342"),
    ("serosa of stomach", "FMA:14914", "UBERON:0001201", "ILX:0735818"),
    ("stomach", "FMA:7148", "UBERON:0000945", "ILX:0736697"),
    ("stomach smooth muscle circular layer", "FMA:14911", "UBERON:0008857", "ILX:0726073"),
    ("submucosa of stomach", "FMA:14908", "UBERON:0001200", "ILX:0732950")
]

def get_stomach_term(name : str):
    """
    Find term by matching name to any identifier held for a term.
    Raise exception if name not found.
    :return ( preferred name, preferred id )
    """
    for term in stomach_terms:
        if name in term:
            return ( term[0], term[1] )
    raise NameError("Stomach annotation term '" + name + "' not found.")
