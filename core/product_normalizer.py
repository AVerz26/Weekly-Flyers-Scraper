"""
Módulo de Normalização e Padronização Canônica de Produtos
Garante que descrições de produtos de supermercados diferentes fiquem no mesmo formato canônico
para permitir agrupamento e comparação direta de preços.
"""

import re
import unicodedata

# Termos que devem ser removidos por serem ruído promocional / variações que atrapalham comparação
NOISE_TERMS = [
    r'\bfatiad[oa]s?\b',
    r'\bem peda[cç]os?\b',
    r'\bem postas?\b',
    r'\ba v[aá]cuo\b',
    r'\bcongelad[oa]s?\b',
    r'\bresfriad[oa]s?\b',
    r'\btemperad[oa]s?\b',
    r'\bdesossad[oa]s?\b',
    r'\bcom dorsal\b',
    r'\bsem dorsal\b',
    r'\bbandeja\b',
    r'\bcada\b',
    r'\bunidade\b',
    r'\bunid\.?\b',
    r'\bo quilo\b',
    r'\bo kg\b',
    r'\bpor kg\b',
    r'\bpor quilo\b',
    r'\bqualidade premium\b',
    r'\btipo exporta[cç][aã]o\b',
    r'\boferta\b',
    r'\bespecial\b',
    r'\bpromocional\b',
    r'\bselecionad[oa]s?\b',
    r'\btradicional\b',
    r'\bpet\b',
    r'\btp\b',
    r'\btetra pak\b',
    r'\blata\b',
    r'\bgarrafa\b',
    r'\brefil\b',
    r'\bpacote\b',
    r'\bpct\.?\b',
    r'\bleve mais pague menos\b',
]

# Sinônimos e correções de categorias comuns
SYNONYMS = [
    (r'\bmussarela\b', 'Queijo Mussarela'),
    (r'\bqueijo tipo mussarela\b', 'Queijo Mussarela'),
    (r'\bqueijo tipo prato\b', 'Queijo Prato'),
    (r'\bleite uht\b', 'Leite'),
    (r'\bleite longa vida\b', 'Leite'),
    (r'\bfeijao carioca\b', 'Feijão Carioca'),
    (r'\bfeijao preto\b', 'Feijão Preto'),
    (r'\barroz branco\b', 'Arroz'),
    (r'\bcerveja pilsen\b', 'Cerveja'),
    (r'\brefrigerante coca cola\b', 'Coca-Cola'),
    (r'\bcoca cola\b', 'Coca-Cola'),
    (r'\bcha mate\b', 'Chá Mate'),
    (r'\bleite condensado semidesnatado\b', 'Leite Condensado'),
    (r'\bleite condensado semi desnatado\b', 'Leite Condensado'),
    (r'\bcreme de leite leve\b', 'Creme de Leite'),
]

def clean_noise(text: str) -> str:
    """Remove termos descritivos que atrapalham o matching."""
    res = text
    for pattern in NOISE_TERMS:
        res = re.sub(pattern, '', res, flags=re.IGNORECASE)
    return res

def standardize_units(text: str) -> str:
    """Padroniza unidades de medida: 1 kg -> 1kg, 1 Litro -> 1L, 350 ML -> 350ml."""
    # kg
    text = re.sub(r'(\d+[\.,]?\d*)\s*(?:quilos?|kilos?|kgs?|kg\b)', r'\1kg', text, flags=re.IGNORECASE)
    # g
    text = re.sub(r'(\d+[\.,]?\d*)\s*(?:gramas?|grs?|g\b)', r'\1g', text, flags=re.IGNORECASE)
    # L
    text = re.sub(r'(\d+[\.,]?\d*)\s*(?:litros?|lts?|l\b)', r'\1L', text, flags=re.IGNORECASE)
    # ml
    text = re.sub(r'(\d+[\.,]?\d*)\s*(?:mililitros?|mls?|ml\b)', r'\1ml', text, flags=re.IGNORECASE)
    return text

def normalize_product_name(name: str) -> str:
    """
    Normaliza o nome do produto para formato canônico padronizado.
    Ex: "Mussarela Fatiada Sadia 150g" -> "Queijo Mussarela Sadia 150g"
        "Picanha Bovina a vácuo kg" -> "Picanha Bovina kg"
        "Arroz Branco Tipo 1 5kg Camil" -> "Arroz Tipo 1 Camil 5kg"
    """
    if not name or not isinstance(name, str):
        return ""

    s = name.strip()
    
    # Padroniza unidades primeiro
    s = standardize_units(s)

    # Remove ruídos
    s = clean_noise(s)

    # Normaliza espaços múltiplos
    s = re.sub(r'\s+', ' ', s).strip()

    # Aplica sinônimos se aplicável
    for pattern, replacement in SYNONYMS:
        if re.search(pattern, s, re.IGNORECASE):
            s = re.sub(pattern, replacement, s, count=1, flags=re.IGNORECASE)

    # Remove pontuações soltas
    s = re.sub(r'[\(\)\[\]\{\}\/\\,\-\:]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Capitalização adequada (Title Case inteligente mantendo unidades como 5kg, 1L, 350ml, kg)
    words = s.split()
    formatted_words = []
    for w in words:
        # Se for unidade tipo 5kg, 350ml, 1L, 500g ou apenas kg, g, ml, l
        if re.match(r'^\d+(?:[\.,]\d+)?(?:kg|g|ml|l|un)$', w, re.IGNORECASE):
            unit_part = re.sub(r'^\d+(?:[\.,]\d+)?', '', w).lower()
            num_part = re.sub(r'[a-zA-Z]+$', '', w)
            if unit_part == 'l':
                formatted_words.append(f"{num_part}L")
            else:
                formatted_words.append(f"{num_part}{unit_part}")
        elif w.lower() in ('kg', 'g', 'ml', 'un'):
            formatted_words.append(w.lower())
        elif w.lower() in ('l', 'lt', 'lts', 'litro', 'litros'):
            formatted_words.append("1L")
        elif w.lower() in ('de', 'do', 'da', 'dos', 'das', 'e', 'em', 'com', 'sem', 'ao', 'tipo'):
            formatted_words.append(w.lower())
        elif w.upper() in ('UHT', 'TP', 'PET', 'PVC', 'S/A', 'SA', 'LTDA'):
            formatted_words.append(w.upper())
        else:
            formatted_words.append(w.capitalize())

    final_name = ' '.join(formatted_words)
    # Garante que a primeira palavra comece com maiúscula
    if final_name:
        final_name = final_name[0].upper() + final_name[1:]

    return final_name
