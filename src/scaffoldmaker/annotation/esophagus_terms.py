"""
Common resource for esophagus annotation terms.
"""

# convention: preferred name, preferred id, followed by any other ids and alternative names
esophagus_terms = [
    ( "abdominal part of esophagus", "UBERON:0035177", "FMA:9397", "ILX:0735274"),
    ( "cervical part of esophagus", "UBERON:0035450", "FMA:9395", "ILX:0734725"),
    ( "esophagus", "UBERON:0001043", "FMA:7131", "ILX:0735017"),
    ( "gastroesophageal sphincter", "UBERON:0004550", "FMA:14915", "ILX:0736896"),
    ( "thoracic part of esophagus", "UBERON:0035216", "FMA:9396", "ILX:0732442"),
    ( "upper esophageal sphincter", "UBERON:0007268", "FMA:265203", "ILX:0724033")
    ]

def get_esophagus_term(name : str):
    """
    Find term by matching name to any identifier held for a term.
    Raise exception if name not found.
    :return ( preferred name, preferred id )
    """
    for term in esophagus_terms:
        if name in term:
            return ( term[0], term[1] )
    raise NameError("Esophagus annotation term '" + name + "' not found.")
