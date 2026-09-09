import re
import unicodedata
from typing import Tuple, Optional

# Termos promocionais, ruídos de marketing, preços OCR e falsas marcas a serem descartados
NOISE_TERMS = [
    r'\bde\s+\d+[\.,]?\d*\s+por\s+r?\$?\s*\d+[\.,]?\d*\b',
    r'\br\$\s*\d+[\.,]?\d*\b',
    r'\br\s+\d{1,3}\s+\d{2}\b',
    r'\br\s+\d+[\.,]\d+\b',
    r'\bgenerica\b', r'\bgenérica\b', r'\bgenerico\b', r'\bgenérico\b',
    r'\bdiversos\b', r'\bdiversas\b', r'\bdiversos\/as\b',
    r'\bn\/a\b', r'\bnull\b', r'\bnone\b',
    r'\bsuper\s+oferta\b', r'\boferta\s+especial\b', r'\bpreco\s+especial\b', r'\bpreço\s+especial\b',
    r'\boferta\b', r'\bofertaco\b', r'\bofertaça\b', r'\bimperdivel\b', r'\bimperdível\b',
    r'\bpromocao\b', r'\bpromoção\b', r'\bpreco\s+baixo\b', r'\bpreço\s+baixo\b',
    r'\bapenas\b', r'\bso\s+hoje\b', r'\bsó\s+hoje\b', r'\bgelada\b', r'\bgeladinha\b',
    r'\bleve\s+\d+\s+pague\s+\d+\b', r'\ba\s+partir\s+de\b', r'\bcada\b', r'\bunidade\b',
    r'\bun\b', r'\bund\b', r'\bde:\b', r'\bpor:\b', r'\bgratis\b', r'\bgrátis\b',
    r'\bnovidade\b', r'\beconomia\b', r'\bdesconto\b', r'\bshow\b', r'\bcompre\b',
    r'\bganhe\b', r'\batencao\b', r'\batenção\b', r'\bclube\b', r'\bapp\b', r'\bsuper\b',
    r'\bpct\b', r'\bpacote\b', r'\bpeca\b', r'\bpeça\b', r'\bcaixa\b', r'\bcx\b',
    r'\bbandeja\b', r'\ba\s+vacuo\b', r'\ba\s+vácuo\b', r'\bqualidade\b', r'\bselecionad[oa]s?\b',
    r'\bpremium\b', r'\bhortifruti\b', r'\baçougue\b', r'\bacougue\b', r'\bpadaria\b',
    r'\bfatiad[oa]s?\b', r'\bem\s+postas?\b', r'\bem\s+pedacos?\b', r'\bem\s+pedaços?\b',
    r'\bdesossad[oa]s?\b', r'\bcom\s+dorsal\b', r'\bsem\s+dorsal\b'
]

# Falsas marcas frequentemente retornadas por OCR/IA
JUNK_BRANDS = {
    'diversos', 'diversas', 'diversos/as', 'generica', 'generico', 'genericas', 'genericos',
    'n/a', 'na', 'null', 'none', 'outros', 'outra', 'marca', 'padrao', 'padrão',
    'sem marca', 'varias', 'várias', 'varios', 'vários', 'nacional', 'tradicional',
    'importado', 'importada', 'quilo', 'kg', 'un', 'unidade', 'bandeja', 'pacote'
}

def is_junk_brand(b: Optional[str]) -> bool:
    """Verifica se o termo de marca é na verdade um ruído ou placeholder genérico."""
    if not b:
        return True
    clean = remove_accents(str(b)).lower().strip()
    if not clean or len(clean) <= 1:
        return True
    if clean in JUNK_BRANDS:
        return True
    junk_roots = [
        'gener', 'genr', 'diver', 'outr', 'n/a', 'null', 'none',
        'padra', 'padr', 'sem marca', 'varia', 'qualid', 'selec',
        'marca', 'import', 'kg', 'quilo', 'unid', 'pct', 'pacote', 'caixa'
    ]
    return any(r in clean for r in junk_roots)

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
    'zupp': 'Zupp',
    'tio joao': 'Tio João',
    'tio joão': 'Tio João',
    'camil': 'Camil',
    'prato fino': 'Prato Fino',
    'kicaldo': 'Kicaldo',
    'namorado': 'Namorado',
    'donana': 'Donana',
    'barralcool': 'Barralcool',
    'barrálcool': 'Barralcool',
    'uniao': 'União',
    'união': 'União',
    'itajobi': 'Itajobi',
    'piracanjuba': 'Piracanjuba',
    'itambe': 'Itambé',
    'itambé': 'Itambé',
    'italac': 'Italac',
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
    'nutribraz': 'Nutribraz',
    'excelencia': 'Excelência',
    'excelência': 'Excelência',
    'sulbeef': 'Sulbeef',
    'bauducco': 'Bauducco',
    'marilan': 'Marilan',
    'mabel': 'Mabel',
    'piraque': 'Piraquê',
    'piraquê': 'Piraquê',
    'wickbold': 'Wickbold',
    'pullman': 'Pullman',
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
    'colgate': 'Colgate',
    'sorriso': 'Sorriso',
    'oral-b': 'Oral-B',
    'oral b': 'Oral-B',
    'pantene': 'Pantene',
    'head & shoulders': 'Head & Shoulders',
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
    'duetto': 'Duetto',
    'paratudo': 'Paratudo',
    'dolly': 'Dolly'
}

def remove_accents(text: str) -> str:
    """Remove acentos para normalização comparativa."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def extract_unit_measure(text: str) -> Tuple[str, str]:
    """
    Extrai peso/volume padronizado (ex: '350ml', '1kg', '500g', '2L', '1.5L', 'c/ 30').
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
        (r'(\d+[\.,]?\d*)\s*(?:kgs?|kilos?|quilos?|kg)\b', r'\1kg'),
        (r'(\d+)\s*(?:grs?|gramas?|g)\b', r'\1g'),
        (r'(?:c\/|com)?\s*(\d+)\s*(?:unidades?|unids?|und?|ovos?|rolos?)\b', r'c/ \1'),
        (r'(\d+)\s*(?:unidades?|unids?|und?|un)\b', r'\1un'),
        (r'(?:pack|pct|cx|caixa)\s*(?:c\/|com)?\s*(\d+)', r'Pack c/ \1')
    ]

    for pat, rep in patterns:
        match = re.search(pat, clean, re.IGNORECASE)
        if match:
            raw_val = match.group(0)
            norm_val = re.sub(pat, rep, raw_val, flags=re.IGNORECASE).replace(',', '.')
            unit_found = norm_val
            clean = re.sub(pat, ' ', clean, flags=re.IGNORECASE)
            break

    # Se ainda tiver indicação de peso por quilo / kg isolado
    if not unit_found:
        if re.search(r'\b(?:kg|quilo|o quilo|por kg|kilo)\b', clean, re.IGNORECASE):
            unit_found = "Kg"
            clean = re.sub(r'\b(?:kg|quilo|o quilo|por kg|kilo)\b', ' ', clean, flags=re.IGNORECASE)

    return clean.strip(), unit_found

def detect_brand(text: str) -> Tuple[str, str]:
    """Identifica marca conhecida e retorna (texto_sem_marca, marca_padronizada)."""
    if not text:
        return text, ""

    text_no_accents = remove_accents(text).lower()
    sorted_brands = sorted(BRAND_MAPPING.keys(), key=len, reverse=True)
    
    for brand_key in sorted_brands:
        brand_no_acc = remove_accents(brand_key).lower()
        pattern = r'\b' + re.escape(brand_no_acc) + r'\b'
        if re.search(pattern, text_no_accents):
            canon_brand = BRAND_MAPPING[brand_key]
            clean = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean, canon_brand

    return text, ""

# Dicionário Canônico Especializado para Padronização Direta de Alimentos Brasileiros
CANONICAL_FOODS = [
    # Hortifruti
    (r'\babacate\b', 'Abacate Kg'),
    (r'\babacaxi\s+perola|\babacaxi\b', 'Abacaxi Pérola un'),
    (r'\balho\s+roxo|\balho\s+nacional|\balho\b', 'Alho Kg'),
    (r'\bbanana\s+nanica\b', 'Banana Nanica Kg'),
    (r'\bbanana\s+prata\b', 'Banana Prata Kg'),
    (r'\bbanana\s+da\s+terra\b', 'Banana da Terra Kg'),
    (r'\bbanana\s+maca|\bbanana\s+maçã\b', 'Banana Maçã Kg'),
    (r'\bbatata\s+doce\b', 'Batata Doce Kg'),
    (r'\bbatata\s+monalisa|\bbatata\s+inglesa|\bbatata\s+lavada|\bbatata\b', 'Batata Inglesa Kg'),
    (r'\bbeterraba\b', 'Beterraba Kg'),
    (r'\bbrocolis\s+ou\s+couve|\bbrocolis|\bbrócolis\b', 'Brócolis un'),
    (r'\bcouve\s*flor|\bcouve-flor\b', 'Couve-Flor un'),
    (r'\bcebola\s+roxa\b', 'Cebola Roxa Kg'),
    (r'\bcebola\s+nacional|\bcebola\s+branca|\bcebola\b', 'Cebola Nacional Kg'),
    (r'\bcenoura\b', 'Cenoura Kg'),
    (r'\bchuchu\b', 'Chuchu Kg'),
    (r'\blaranja\s+pera|\blaranja\s+pêra|\blaranja\b', 'Laranja Pera Kg'),
    (r'\blimao\s+taiti|\blimão\s+taiti|\blimao\s+tahiti|\blimão\b', 'Limão Taiti Kg'),
    (r'\bmaca\s+gala|\bmaçã\s+gala|\bmaca\s+nacional|\bmaçã\b', 'Maçã Gala Kg'),
    (r'\bmaca\s+fuji|\bmaçã\s+fuji\b', 'Maçã Fuji Kg'),
    (r'\bmamao\s+formosa|\bmamão\s+formosa|\bmamao\b|\bmamão\b', 'Mamão Formosa Kg'),
    (r'\bmamao\s+papaya|\bmamão\s+papaya\b', 'Mamão Papaya un'),
    (r'\bmanga\s+palmer\b', 'Manga Palmer Kg'),
    (r'\bmanga\s+tommy\b', 'Manga Tommy Kg'),
    (r'\bmelancia\b', 'Melancia Kg'),
    (r'\bmelao\s+amarelo|\bmelão\s+amarelo|\bmelao|\bmelão\b', 'Melão Amarelo Kg'),
    (r'\bovos?\s+brancos?\b', 'Ovos Brancos c/ 30'),
    (r'\bovos?\s+vermelhos?\b', 'Ovos Vermelhos c/ 30'),
    (r'\bpimentao\s+verde|\bpimentão\s+verde|\bpimentao|\bpimentão\b', 'Pimentão Verde Kg'),
    (r'\brepolho\s+verde|\brepolho\b', 'Repolho Verde Kg'),
    (r'\btomate\s+italiano\b', 'Tomate Italiano Kg'),
    (r'\btomate\s+longa\s+vida|\btomate\s+molho|\btomate\s+salada|\btomate\b', 'Tomate Longa Vida Kg'),
    (r'\buva\s+niagara|\buva\s+niágara|\buva\b', 'Uva Niagara 500g'),

    # Carnes, Aves e Embutidos
    (r'\bacem\s+com\s+osso|\bacém\s+com\s+osso|\bacem\s+osso|\bacém\s+osso|\bacem\s+bovino|\bacém\s+bovino|\bacem|\bacém\b', 'Acém Bovino c/ Osso kg'),
    (r'\balcatra\s+com\s+maminha|\balcatra\s+bovina|\balcatra\b', 'Alcatra Bovina kg'),
    (r'\bbacon\s+manta|\bbacon\s+em\s+manta|\bbacon\b', 'Bacon em Manta kg'),
    (r'\bbisteca\s+contra\s*file|\bbisteca\s+contra\s*filé|\bbisteca\s+bovina\b', 'Bisteca Contrafilé Bovina kg'),
    (r'\bbisteca\s+suina|\bbisteca\s+suína|\bbisteca\s+de\s+porco\b', 'Bisteca Suína kg'),
    (r'\bcarne\s+moida|\bcarne\s+moída\b', 'Carne Moída Bovina kg'),
    (r'\bcontra\s*file|\bcontra\s*filé|\bcontrafile|\bcontrafilé\b', 'Contrafilé Bovino kg'),
    (r'\bcostela\s+ripa|\bcostela\s+bovina\s+ripa\b', 'Costela Bovina Ripa kg'),
    (r'\bcostela\s+minga|\bcostela\s+bovina\s+minga\b', 'Costela Bovina Minga kg'),
    (r'\bcostela\s+bovina\b', 'Costela Bovina kg'),
    (r'\bcostelinha\s+suina|\bcostelinha\s+suína\b', 'Costelinha Suína kg'),
    (r'\bcoxa\s+e\s+sobrecoxa|\bcoxa\s+com\s+sobrecoxa\b', 'Coxa e Sobrecoxa de Frango kg'),
    (r'\bcoxinha\s+da\s+asa\b', 'Coxinha da Asa de Frango kg'),
    (r'\bcoxao\s+duro|\bcoxão\s+duro\b', 'Coxão Duro Bovino kg'),
    (r'\bcoxao\s+mole|\bcoxão\s+mole\b', 'Coxão Mole Bovino kg'),
    (r'\bfile\s+de\s+peito|\bfilé\s+de\s+peito|\bpeito\s+de\s+frango|\bfile\s+peito|\bfilé\s+peito\b', 'Filé de Peito de Frango kg'),
    (r'\bfrango\s+inteiro|\bfrango\s+congelado\b', 'Frango Inteiro kg'),
    (r'\bfraldinha\s+bovina|\bfraldinha\b', 'Fraldinha Bovina kg'),
    (r'\blinguica\s+calabresa|\blinguiça\s+calabresa|\bcalabresa\b', 'Linguiça Calabresa kg'),
    (r'\blinguica\s+toscana|\blinguiça\s+toscana|\blinguica\s+mista|\blinguiça\s+mista|\blinguica|\blinguiça\b', 'Linguiça Toscana kg'),
    (r'\bmaminha\s+bovina|\bmaminha\b', 'Maminha Bovina kg'),
    (r'\bmusculo\s+com\s+osso|\bmúsculo\s+com\s+osso|\bmusculo\s+osso|\bmúsculo\s+osso|\bmusculo|\bmúsculo\b', 'Músculo Bovino c/ Osso kg'),
    (r'\bpaleta\s+bovina|\bpaleta\b', 'Paleta Bovina kg'),
    (r'\bpaleta\s+suina|\bpaleta\s+suína\b', 'Paleta Suína kg'),
    (r'\bpatinho\s+bovino|\bpatinho\b', 'Patinho Bovino kg'),
    (r'\bpernil\s+suino|\bpernil\s+suíno|\bpernil\b', 'Pernil Suíno kg'),
    (r'\bpicanha\s+bovina|\bpicanha\b', 'Picanha Bovina kg'),
    (r'\bsalsicha\s+hot\s*dog|\bsalsicha\b', 'Salsicha Hot Dog kg'),
    (r'\bsobrecoxa\s+de\s+frango|\bsobrecoxa\b', 'Sobrecoxa de Frango kg'),

    # Mercearia e Laticínios
    (r'\barroz\s+branco\s+tipo\s*1|\barroz\s+tipo\s*1|\barroz\s+tp\s*1|\barroz\b', 'Arroz Branco Tipo 1 5kg'),
    (r'\bfeijao\s+carioca|\bfeijão\s+carioca|\bfeijao\s+tipo\s*1|\bfeijão\s+tipo\s*1|\bfeijao|\bfeijão\b', 'Feijão Carioca 1kg'),
    (r'\bacucar\s+cristal|\baçúcar\s+cristal|\bacucar\b|\baçúcar\b', 'Açúcar Cristal 2kg'),
    (r'\bacucar\s+refinado|\baçúcar\s+refinado\b', 'Açúcar Refinado 1kg'),
    (r'\bcafe\s+tradicional|\bcafé\s+tradicional|\bcafe\s+torrado|\bcafé\s+torrado|\bcafe|\bcafé\b', 'Café Tradicional 500g'),
    (r'\boleo\s+de\s+soja|\bóleo\s+de\s+soja|\boleo\s+soja|\bóleo\s+soja|\boleo|\bóleo\b', 'Óleo de Soja 900ml'),
    (r'\bleite\s+integral\s+uht|\bleite\s+integral|\bleite\s+uht|\bleite\s+longa\s+vida\b', 'Leite Integral 1L'),
    (r'\bleite\s+condensado\b', 'Leite Condensado 395g'),
    (r'\bcreme\s+de\s+leite\b', 'Creme de Leite 200g'),
    (r'\bfarinha\s+de\s+trigo\s+tipo\s*1|\bfarinha\s+de\s+trigo|\bfarinha\s+trigo\b', 'Farinha de Trigo Tipo 1 1kg'),
    (r'\bmacarrao\s+espaguete|\bmacarrão\s+espaguete|\bmacarrao|\bmacarrão\b', 'Macarrão Espaguete 500g'),
    (r'\bmolho\s+de\s+tomate\b', 'Molho de Tomate 300g'),
    (r'\bqueijo\s+mussarela|\bqueijo\s+tipo\s+mussarela|\bmussarela\b', 'Queijo Mussarela kg'),
    (r'\bqueijo\s+prato|\bqueijo\s+tipo\s+prato\b', 'Queijo Prato kg'),
    (r'\bpresunto\s+cozido|\bpresunto\b', 'Presunto Cozido kg'),
    (r'\bmanteiga\s+com\s+sal|\bmanteiga\b', 'Manteiga c/ Sal 200g'),
    (r'\bmargarina\s+com\s+sal|\bmargarina\b', 'Margarina c/ Sal 500g'),

    # Limpeza e Higiene
    (r'\bdetergente\s+liquido|\bdetergente\s+líquido|\bdetergente\b', 'Detergente Líquido 500ml'),
    (r'\bsabao\s+em\s+po|\bsabão\s+em\s+pó\b', 'Sabão em Pó 1.6kg'),
    (r'\bamaciante\s+de\s+roupas?|\bamaciante\b', 'Amaciante 2L'),
    (r'\bpapel\s+higienico|\bpapel\s+higiênico\b', 'Papel Higiênico Folha Dupla c/ 12'),
    (r'\bdesinfetante\b', 'Desinfetante 2L'),

    # Bebidas
    (r'\brefrigerante\s+coca\s*cola|\bcoca\s*cola\s*2l|\bcoca\s*cola\b', 'Refrigerante Coca-Cola 2L'),
    (r'\bguarana\s+antarctica|\bguaraná\s+antarctica\b', 'Refrigerante Guaraná Antarctica 2L'),
    (r'\bcerveja\s+heineken\b', 'Cerveja Heineken 350ml'),
    (r'\bcerveja\s+amstel\b', 'Cerveja Amstel 350ml'),
    (r'\bcerveja\s+brahma\b', 'Cerveja Brahma 350ml'),
    (r'\bcerveja\s+spaten\b', 'Cerveja Spaten 350ml'),
    (r'\bcerveja\s+skol\b', 'Cerveja Skol 350ml'),
    (r'\bcerveja\s+corona\b', 'Cerveja Corona 330ml'),
    (r'\bcerveja\s+budweiser\b', 'Cerveja Budweiser 350ml')
]

def format_title_portuguese(text: str) -> str:
    """Aplica capitalização correta respeitando preposições da língua portuguesa."""
    if not text:
        return ""
    words = text.strip().split()
    low_words = {'de', 'da', 'do', 'dos', 'das', 'em', 'com', 'para', 'c/', 's/', 'e', 'a', 'o', 'as', 'os'}
    
    formatted = []
    for i, w in enumerate(words):
        w_lower = w.lower()
        if i > 0 and w_lower in low_words:
            formatted.append(w_lower)
        elif w_lower in ['kg', 'g', 'l', 'ml', 'un']:
            formatted.append(w.upper() if w_lower == 'l' else w.capitalize() if w_lower == 'kg' else w_lower)
        else:
            formatted.append(w.capitalize())
    return " ".join(formatted)

def padronizar_produto(item_name: Optional[str], fallback_brand: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Transforma qualquer descrição visual de encarte em um nome canônico estruturado e limpo:
    Exemplo:
      "SUPER OFERTA CERVEJA HEINEKEN LATAO 350 ML GELADA" -> 
      ("Cerveja Heineken 350ml", "Heineken", "350ml")
      "BANANA NANICA KG DIVERSOS" ->
      ("Banana Nanica Kg", "", "Kg")
      "ARROZ REI 5KG" ->
      ("Arroz Rei 5kg", "Rei", "5kg")

    Retorna: (produto_padronizado, marca, embalagem)
    """
    if not item_name:
        return "Produto Não Identificado", "", ""

    raw = str(item_name).strip()
    clean = raw

    # 1. Remove ruídos e termos promocionais
    for noise in NOISE_TERMS:
        clean = re.sub(noise, ' ', clean, flags=re.IGNORECASE)

    # 2. Extrai unidade/medida explícita
    clean, embalagem = extract_unit_measure(clean)

    # 3. Detecta marca real conhecida
    clean_no_brand, brand = detect_brand(clean)
    
    # 4. Higieniza marca de fallback (ignora termos genéricos como "diversos", "n/a", etc.)
    if is_junk_brand(brand):
        brand = ""
    if not brand and fallback_brand and not is_junk_brand(fallback_brand):
        fb_clean = fallback_brand.strip().lower()
        brand = BRAND_MAPPING.get(fb_clean, fallback_brand.strip().title())

    # 5. Remove caracteres especiais e ruídos de pontuação
    clean_core = re.sub(r'[\(\)\[\]\{\}\-\–\—\:\,\.\/\\\|\*\+\#\$\!\?]', ' ', clean_no_brand)
    clean_core = re.sub(r'\s+', ' ', clean_core).strip()
    
    # Remove palavras de lixo e marcas falsas de clean_core
    words_core = clean_core.split()
    clean_words = [w for w in words_core if not is_junk_brand(w)]
    clean_core = " ".join(clean_words).strip()

    # 6. Verifica se o produto corresponde a um alimento canônico padronizado
    text_no_acc = remove_accents(clean_core or clean).lower()
    canonical_match = None

    for pattern, canon_title in CANONICAL_FOODS:
        if re.search(pattern, text_no_acc):
            canonical_match = canon_title
            break

    if canonical_match:
        # Se for alimento canônico e tiver marca específica válida (ex: "Arroz Tio João"), combina harmoniosamente
        if brand and brand.lower() not in canonical_match.lower() and not is_junk_brand(brand) and brand.lower() not in ['kg', 'g', 'l', 'ml']:
            # Se tiver medida no canônico, insere a marca antes da medida
            unit_in_canon = re.search(r'(\d+[\.,]?\d*\s*(?:kg|g|l|ml|un|c\/\s*\d+)|kg|un)$', canonical_match, re.IGNORECASE)
            if unit_in_canon:
                u_str = unit_in_canon.group(0)
                base = canonical_match[:unit_in_canon.start()].strip()
                canonical_name = f"{base} {brand} {u_str}".strip()
            else:
                canonical_name = f"{canonical_match} {brand}".strip()
        else:
            canonical_name = canonical_match

        # Extrai a embalagem do próprio nome canônico se ainda não extraída
        if not embalagem:
            _, emb_canon = extract_unit_measure(canonical_name)
            if emb_canon:
                embalagem = emb_canon

        return canonical_name, (brand if brand and not is_junk_brand(brand) else ""), embalagem or ""

    # 7. Fallback inteligente para produtos não mapeados no dicionário de alimentos
    # Formata em Title Case correto
    core_name = format_title_portuguese(clean_core)
    if not core_name:
        core_name = format_title_portuguese(raw[:35])

    parts = []
    if core_name:
        parts.append(core_name)
    if brand and not is_junk_brand(brand) and brand.lower() not in core_name.lower():
        parts.append(brand)
    if embalagem and embalagem.lower() not in core_name.lower():
        parts.append(embalagem)

    final_name = " ".join(parts).strip()
    return final_name, (brand if brand and not is_junk_brand(brand) else ""), embalagem or ""
