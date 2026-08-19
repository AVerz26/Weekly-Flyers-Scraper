import re
import unicodedata
from typing import Tuple, Optional

# Termos promocionais e ruídos a serem removidos dos nomes
NOISE_TERMS = [
    r'\bsuper\s+oferta\b', r'\boferta\s+especial\b', r'\bpreco\s+especial\b', r'\bpreço\s+especial\b',
    r'\boferta\b', r'\bofertaco\b', r'\bofertaça\b', r'\bimperdivel\b', r'\bimperdível\b',
    r'\bpromocao\b', r'\bpromoção\b', r'\bpreco\s+baixo\b', r'\bpreço\s+baixo\b',
    r'\bapenas\b', r'\bso\s+hoje\b', r'\bsó\s+hoje\b', r'\bgelada\b', r'\bgeladinha\b',
    r'\bleve\s+\d+\s+pague\s+\d+\b', r'\ba\s+partir\s+de\b', r'\bcada\b', r'\bunidade\b',
    r'\bun\b', r'\bund\b', r'\bde:\b', r'\bpor:\b', r'\bgratis\b', r'\bgrátis\b',
    r'\bnovidade\b', r'\beconomia\b', r'\bdesconto\b', r'\bshow\b', r'\bcompre\b',
    r'\bganhe\b', r'\batencao\b', r'\batenção\b', r'\bclube\b', r'\bapp\b', r'\bsuper\b',
    r'\bpct\b', r'\bpacote\b', r'\bpeca\b', r'\bpeça\b', r'\bcaixa\b', r'\bcx\b'
]

# Dicionário de padronização de marcas populares no Brasil
BRAND_MAPPING = {
    'coca cola': 'Coca-Cola',
    'coca-cola': 'Coca-Cola',
    'coca': 'Coca-Cola',
    'heineken': 'Heineken',
    'heinek': 'Heineken',
    'amstel': 'Amstel',
    'brahma': 'Brahma',
    'skol': 'Skol',
    'antarctica': 'Antarctica',
    'antartica': 'Antarctica',
    'budweiser': 'Budweiser',
    'bud': 'Budweiser',
    'spaten': 'Spaten',
    'corona': 'Corona',
    'stella artois': 'Stella Artois',
    'stella': 'Stella Artois',
    'eisenbahn': 'Eisenbahn',
    'eisebahn': 'Eisenbahn',
    'itaipava': 'Itaipava',
    'petra': 'Petra',
    'bohemia': 'Bohemia',
    'crystal': 'Crystal',
    'ypê': 'Ypê',
    'ype': 'Ypê',
    'omo': 'Omo',
    'comfort': 'Comfort',
    'downy': 'Downy',
    'tixan': 'Tixan Ypê',
    'tixan ype': 'Tixan Ypê',
    'brilhante': 'Brilhante',
    'minuano': 'Minuano',
    'bombril': 'Bombril',
    'bom bril': 'Bombril',
    'veja': 'Veja',
    'tio joao': 'Tio João',
    'tio joão': 'Tio João',
    'camil': 'Camil',
    'prato fino': 'Prato Fino',
    'kicaldo': 'Kicaldo',
    'namorado': 'Namorado',
    'donana': 'Donana',
    'piracanjuba': 'Piracanjuba',
    'itambe': 'Itambé',
    'itambé': 'Itambé',
    'parmalat': 'Parmalat',
    'elegê': 'Elegê',
    'elege': 'Elegê',
    'lider': 'Líder',
    'líder': 'Líder',
    'tirol': 'Tirol',
    'nestle': 'Nestlé',
    'nestlé': 'Nestlé',
    'sadia': 'Sadia',
    'perdigao': 'Perdigão',
    'perdigão': 'Perdigão',
    'seara': 'Seara',
    'friboi': 'Friboi',
    'swift': 'Swift',
    'aurora': 'Aurora',
    'pellegrino': 'Pellegrino',
    'bauducco': 'Bauducco',
    'marilan': 'Marilan',
    'mabel': 'Mabel',
    'piraque': 'Piraquê',
    'piraquê': 'Piraquê',
    'wickbold': 'Wickbold',
    'pullman': 'Pullman',
    'plusvita': 'Plusvita',
    'seven boys': 'Seven Boys',
    'fugini': 'Fugini',
    'pomarola': 'Pomarola',
    'elefante': 'Elefante',
    'tarantella': 'Tarantella',
    'qualy': 'Qualy',
    'doriana': 'Doriana',
    'delicia': 'Delícia',
    'delícia': 'Delícia',
    'coamo': 'Coamo',
    'soya': 'Soya',
    'lisa': 'Lisa',
    'concordia': 'Concórdia',
    'concórdia': 'Concórdia',
    'gallo': 'Gallo',
    'andorinha': 'Andorinha',
    'borges': 'Borges',
    'melitta': 'Melitta',
    'pilao': 'Pilão',
    'pilão': 'Pilão',
    'tres coracoes': '3 Corações',
    'três corações': '3 Corações',
    'caboclo': 'Caboclo',
    'nescafe': 'Nescafé',
    'nescafé': 'Nescafé',
    'toddy': 'Toddy',
    'nescau': 'Nescau',
    'tang': 'Tang',
    'camp': 'Camp',
    'del valle': 'Del Valle',
    'maguary': 'Maguary',
    'ades': 'Ades',
    'colgate': 'Colgate',
    'sorriso': 'Sorriso',
    'oral-b': 'Oral-B',
    'oral b': 'Oral-B',
    'pantene': 'Pantene',
    'head & shoulders': 'Head & Shoulders',
    'head shoulders': 'Head & Shoulders',
    'elseve': 'Elseve',
    'dove': 'Dove',
    'rexona': 'Rexona',
    'nivea': 'Nivea',
    'nívea': 'Nivea',
    'palmolive': 'Palmolive',
    'lux': 'Lux',
    'pampers': 'Pampers',
    'huggies': 'Huggies',
    'cremer': 'Cremer',
    'personal': 'Personal',
    'neve': 'Neve',
    'milli': 'Milli',
    'cotton': 'Cotton',
    'duetto': 'Duetto'
}

def remove_accents(text: str) -> str:
    """Remove acentos para normalização comparativa."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def extract_unit_measure(text: str) -> Tuple[str, str]:
    """
    Extrai peso/volume padronizado (ex: '350ml', '1kg', '500g', '2L', '1.5L', 'Pack c/ 12').
    Retorna (texto_sem_unidade, unidade_padronizada).
    """
    if not text:
        return "", ""

    unit_found = ""
    clean = text

    # Padrão: 350 ml, 350ml, 1,5 l, 1.5l, 2 litros, 500 g, 500g, 1 kg, 1kg, 5kg
    patterns = [
        (r'(\d+[\.,]?\d*)\s*(?:lts?|litros?|l)\b', r'\1L'),
        (r'(\d+)\s*(?:mls?|ml)\b', r'\1ml'),
        (r'(\d+[\.,]?\d*)\s*(?:kgs?|kilos?|kg)\b', r'\1kg'),
        (r'(\d+)\s*(?:grs?|gramas?|g)\b', r'\1g'),
        (r'(\d+)\s*(?:unidades?|unids?|und?|un)\b', r'\1un'),
        (r'(?:pack|pct|cx|caixa)\s*(?:c\/|com)?\s*(\d+)', r'Pack c/\1')
    ]

    for pat, rep in patterns:
        match = re.search(pat, clean, re.IGNORECASE)
        if match:
            # Padroniza vírgula para ponto em medidas (ex: 1,5L -> 1.5L)
            raw_val = match.group(0)
            norm_val = re.sub(pat, rep, raw_val, flags=re.IGNORECASE).replace(',', '.')
            unit_found = norm_val
            clean = re.sub(pat, ' ', clean, flags=re.IGNORECASE)
            break

    return clean.strip(), unit_found

def detect_brand(text: str) -> Tuple[str, str]:
    """Identifica marca conhecida e retorna (texto_sem_marca, marca_padronizada)."""
    if not text:
        return text, ""

    text_no_accents = remove_accents(text).lower()
    
    # Ordena marcas por tamanho decrescente para priorizar compostas
    sorted_brands = sorted(BRAND_MAPPING.keys(), key=len, reverse=True)
    
    for brand_key in sorted_brands:
        brand_no_acc = remove_accents(brand_key).lower()
        # Busca como palavra inteira ou expressão
        pattern = r'\b' + re.escape(brand_no_acc) + r'\b'
        if re.search(pattern, text_no_accents):
            canon_brand = BRAND_MAPPING[brand_key]
            # Remove a marca do texto original
            clean = re.sub(pattern, ' ', text_no_accents, flags=re.IGNORECASE)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean, canon_brand

    return text, ""

def padronizar_produto(item_name: Optional[str], fallback_brand: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Transforma qualquer descrição visual de encarte em um nome canônico estruturado:
    Exemplo:
      "SUPER OFERTA CERVEJA HEINEKEN LATAO 350 ML GELADA" -> 
      ("Cerveja Heineken 350ml", "Heineken", "350ml")

    Retorna: (produto_padronizado, marca, embalagem)
    """
    if not item_name:
        return "Produto Não Identificado", "", ""

    raw = str(item_name).strip()
    clean = raw

    # 1. Remove ruídos e termos promocionais
    for noise in NOISE_TERMS:
        clean = re.sub(noise, ' ', clean, flags=re.IGNORECASE)

    # 2. Extrai unidade/medida
    clean, embalagem = extract_unit_measure(clean)

    # 3. Detecta marca
    clean_no_brand, brand = detect_brand(clean)
    if not brand and fallback_brand:
        brand = BRAND_MAPPING.get(fallback_brand.lower().strip(), fallback_brand.strip().title())

    # 4. Limpa pontuações extras e múltiplos espaços
    clean_core = re.sub(r'[\(\)\[\]\{\}\-\–\—\:\,\.\/\\\|\*\+\#\$\!\?]', ' ', clean_no_brand)
    clean_core = re.sub(r'\s+', ' ', clean_core).strip()

    # Normalização de tipos e substantivos principais
    clean_core = re.sub(r'\b(cervejas?|cerv|latas?|latao|latão)\b', 'Cerveja', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(refrigerantes?|refrigera)\b', 'Refrigerante', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(arroz\s+tipo\s*1|arroz\s+tp\s*1|arroz\s+tp1)\b', 'Arroz Branco Tipo 1', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(feijao\s+carioca|feijão\s+carioca)\b', 'Feijão Carioca', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(leite\s+uht|leite\s+longa\s+vida)\b', 'Leite Integral', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(oleo\s+de\s+soja|óleo\s+de\s+soja|oleo\s+soja)\b', 'Óleo de Soja', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(acucar\s+cristal|açúcar\s+cristal)\b', 'Açúcar Cristal', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(cafe\s+em\s+po|café\s+em\s+pó|cafe\s+torrado)\b', 'Café Tradicional', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(sabao\s+em\s+po|sabão\s+em\s+pó|sabao\s+po|sabao)\b', 'Sabão em Pó', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(amaciante\s+de\s+roupas?|amaciante\s+concentrado)\b', 'Amaciante', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(detergente\s+liquido|detergente\s+líquido)\b', 'Detergente Líquido', clean_core, flags=re.IGNORECASE)
    clean_core = re.sub(r'\b(papel\s+higienico|papel\s+higiênico)\b', 'Papel Higiênico', clean_core, flags=re.IGNORECASE)

    # Limpeza de palavras duplicadas e formatação
    raw_words = clean_core.split()
    unique_words = []
    seen_lower = set()

    for w in raw_words:
        w_cap = w.capitalize()
        w_low = w.lower()
        if len(w) > 1 and w_low not in ['de', 'do', 'da', 'dos', 'das', 'em', 'com', 'para', 'tipo', 'tp']:
            if w_low not in seen_lower:
                seen_lower.add(w_low)
                unique_words.append(w_cap)

    core_name = " ".join(unique_words[:4])

    if not core_name:
        core_name = re.sub(r'\s+', ' ', raw).title()[:30]

    # Monta o nome canônico: [Produto Core] [Marca] [Embalagem]
    parts = []
    if core_name:
        parts.append(core_name)
    if brand and brand.lower() not in core_name.lower():
        parts.append(brand)
    if embalagem and embalagem.lower() not in core_name.lower():
        parts.append(embalagem)

    canonical_name = " ".join(parts).strip()
    if not canonical_name:
        canonical_name = raw.strip()

    return canonical_name, brand or "", embalagem or ""
