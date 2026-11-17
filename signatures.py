"""User supplied chart with tier limits. Uniform clusters; not live verified."""
import re

ORES = [('Ice',4300),('Aluminum',4285),('Iron',4270),('Silicon',4255),
        ('Copper',4240),('Corundum',4225),('Quartz',4210),('Tin',4195),
        ('Hephaestanite',4180),('Torite',3900),('Agricium',3885),('Tungsten',3870),
        ('Titanium',3855),('Aslarite',3840),('Laranite',3825),('Bexalite',3600),
        ('Gold',3585),('Borase',3570),('Taranite',3555),('Beryl',3540),
        ('Lindinium',3400),('Riccite',3385),('Ouratite',3370),('Savrilium',3200),
        ('Stileron',3185),('Quantainium',3170)]

TIERS = {
    'Legendary': (2, '#ffad24', 'Lendario'),
    'Epic': (3, '#cc5aff', 'Epico'),
    'Rare': (4, '#219bff', 'Raro'),
    'Uncommon': (5, '#21c8ac', 'Incomum'),
    'Common': (6, '#91a4b4', 'Comum'),
}
def tier_for(base):
    return ('Legendary' if base <= 3200 else 'Epic' if base <= 3400
            else 'Rare' if base <= 3600 else 'Uncommon' if base <= 3900 else 'Common')

def identify(value):
    return [(ore,n) for ore,base in ORES
            for n in range(1, TIERS[tier_for(base)][0]+1) if base*n == value]

def candidates(value):
    matches=[]
    for ore,base in ORES:
        tier=tier_for(base)
        limit,color,label=TIERS[tier]
        if value % base == 0 and 1 <= value//base <= limit:
            matches.append(dict(name=ore, count=value//base, color=color, tier=label, kind='ore'))
    for name,base,limit,color in [('ROC',4000,7,'#56dca8'),
                                 ('MANUAL (FPS)',3000,10,'#78c6e0'),
                                 ('DEBRIS',2000,15,'#b5a17a')]:
        if value % base == 0 and 1 <= value//base <= limit:
            matches.append(dict(name=name,count=value//base,color=color,tier=name,kind='other'))
    return matches

def parse_rs(text):
    # Never turn distances (15.1km, 599m) or decimals into signatures.
    text = text.strip()
    if not re.fullmatch(r'(?:\d{4,5}|\d{1,2}[., ]\d{3})', text):
        return None
    value = int(re.sub(r'[., ]', '', text))
    return value if 2000 <= value <= 30000 else None

class DisplaySignal:
    """Show the first valid OCR value and hold it across brief gaps."""
    def __init__(self, hold_seconds=2.5):
        self.value = None
        self.last_seen = float('-inf')
        self.hold_seconds = hold_seconds

    def feed(self, value, now):
        if value is not None:
            self.value = value
            self.last_seen = now
        elif now - self.last_seen >= self.hold_seconds:
            self.value = None
        return self.value
