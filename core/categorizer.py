import re
from typing import Optional

def categorizar_produto(item: Optional[str]) -> str:
    """
    Categoriza um produto a partir de seu nome e descrição utilizando
    regras heurísticas especializadas no varejo brasileiro de supermercados.
    """
    if not item:
        return "Outros"
        
    item_str = str(item).lower().strip()

    # Normalizações e sinônimos contextuais
    if any(x in item_str for x in ['tomadoro', 'tom. sofruta', 'extrato', 'pomarola', 'elefante', 'tarantella', 'fugini']):
        item_str += ' molho tomate'
    if any(x in item_str for x in ['mão de queijo', 'pão de queijo', 'culibá', 'forno de minas']):
        item_str += ' pão de queijo'
    if any(x in item_str for x in ['ameiga', 'rólas', 'dowsy', 'concentrado', 'ypê', 'ype', 'comfort', 'downy', 'fofo', 'baby soft']):
        item_str += ' amaciante'
    if any(x in item_str for x in ['bão forma', 'badeco', 'bisnaguinha', 'pullman', 'wickbold', 'plusvita', 'seven boys']):
        item_str += ' pão forma'
    if any(x in item_str for x in ['suko', 'refreskant', 'kapo', 'del valle', 'ades', 'gatorade', 'powerade', 'tampico', 'tang', 'camp']):
        item_str += ' suco bebida'
    if any(x in item_str for x in ['cerv', 'latão', 'lata', 'multipack', 'pack', 'long neck', 'barril']):
        item_str += ' cerveja'

    # --- 1. PADARIA E CONGELADOS (Alta Prioridade para compostos) ---
    if any(x in item_str for x in ['pão de queijo', 'pao de queijo', 'culibá', 'mão de queijo']):
        return 'Padaria / Congelados'
    if any(x in item_str for x in ['pão', 'pao', 'pullman', 'rap 10', 'torrada', 'croissant', 'baguete', 'bisnaguinha', 'pão forma']):
        return 'Padaria / Pães'
    if any(x in item_str for x in ['pizza', 'lasanha congelada', 'batata congelada', 'batata palito', 'hamburguer congelado', 'sorvete', 'açai', 'açaí', 'picolé']):
        return 'Congelados e Sobremesas'

    # --- 2. BEBIDAS (ALCOÓLICAS E NÃO ALCOÓLICAS) ---
    if any(x in item_str for x in ['cerveja', 'brahma', 'skol', 'heineken', 'original', 'eisebahn', 'eisenbahn', 'antarctica', 'budweiser', 'amstel', 'corona', 'stella', 'spaten', 'itaipava', 'petra', 'bohemia']):
        return 'Bebidas / Cervejas'
    if any(x in item_str for x in ['coca-cola', 'coca cola', 'refrigerante', 'refrigera', 'sukita', 'fanta', 'sprite', 'guarana', 'kuat', 'pepsi', 'schweppes', 'dolly']):
        return 'Bebidas / Refrigerantes'
    if any(x in item_str for x in ['suco', 'bebida', 'isotônico', 'nectar', 'água de coco', 'agua de coco', 'cha', 'chá', 'energetico', 'energético', 'red bull', 'monster']):
        return 'Bebidas / Sucos e Diversos'
    if any(x in item_str for x in ['campari', 'vinho', 'vodka', 'gin', 'whisky', 'whiskey', 'cachaça', 'rum', 'espumante', 'licor', 'tequila', 'conhaque']):
        return 'Bebidas / Alcoólicos Diversos'
    if any(x in item_str for x in ['leite', 'iogurte', 'queijo', 'manteiga', 'requeijão', 'mussarela', 'prato', 'ricota', 'parmesão', 'coalhada', 'danone', 'itambé', 'piracanjuba', 'parmalat', 'vigor', 'tirol', 'betânia']):
        return 'Laticínios / Leites e Derivados'

    # --- 2. CARNES E PROTEÍNAS ---
    if any(x in item_str for x in ['costela', 'corte', 'coxão', 'alcatra', 'fraldinha', 'maminha', 'bananinha', 'costela bovina', 'corte grill', 'carne moída', 'patinho', 'contra filé', 'bisteca', 'cupim', 'picanha', 'acém', 'musculo', 'lagarto', 'paleta']):
        return 'Carnes / Bovina'
    if any(x in item_str for x in ['coxa', 'sobrecoxa', 'frango', 'asa', 'peito fgo', 'galinha', 'tulipa', 'coração frango', 'sassami', 'filezinho']):
        return 'Carnes / Aves'
    if any(x in item_str for x in ['pernil', 'suína', 'suino', 'suina', 'linguiça', 'linguica', 'salsicha', 'hambúrguer', 'hamburguer', 'bacon', 'calabresa', 'costelinha suina', 'lombo', 'salame', 'presunto', 'mortadela', 'nuggets']):
        return 'Carnes / Suína e Embutidos'
    if any(x in item_str for x in ['tilápia', 'peixe', 'file feira', 'salmão', 'bacalhau', 'camarão', 'sardinha', 'atum', 'pescada', 'merluza', 'pintado', 'pacu']):
        return 'Carnes / Peixes'

    # --- 3. MERCEARIA E DESPENSA ---
    if 'arroz' in item_str:
        return 'Mercearia / Arroz'
    if any(x in item_str for x in ['feijão', 'feijao', 'feijo', 'grão', 'lentilha', 'grão de bico', 'milho verde', 'ervilha', 'azeitona', 'palmito']):
        return 'Mercearia / Grãos e Conservas'
    if any(x in item_str for x in ['óleo', 'oleo', 'azeite', 'gallo', 'soya', 'lisa', 'concórdia', 'andorinha', 'borges']):
        return 'Mercearia / Óleos e Azeites'
    if any(x in item_str for x in ['açúcar', 'acucar', 'doce dia', 'uniao', 'união', 'adocante', 'adoçante']):
        return 'Mercearia / Açúcar'
    if any(x in item_str for x in ['café', 'cafe', 'pilão', 'melitta', 'caboclo', 'tres corações', 'três corações', 'nescafé', 'nescafe', 'soluvel']):
        return 'Mercearia / Café'
    if any(x in item_str for x in ['trigo', 'farinha', 'vitoriosa', 'alvalade', 'flocão', 'flocao', 'sinha', 'sinhá', 'fubá', 'fuba', 'tapioca', 'amido', 'maizena', 'fermento']):
        return 'Mercearia / Farináceos'
    if any(x in item_str for x in ['molho tomate', 'molho', 'extrato', 'ketchup', 'mostarda', 'maionese', 'shoyu', 'temperos', 'caldo']):
        return 'Mercearia / Molhos e Condimentos'
    if any(x in item_str for x in ['macarrão', 'macarrao', 'massa', 'espaguete', 'miojo', 'parafuso', 'lasanha']):
        return 'Mercearia / Massas'
    if any(x in item_str for x in ['biscoito', 'rosquinha', 'mabel', 'belma', 'liane', 'marilan', 'chocolate', 'kinder', 'bombom', 'bolacha', 'wafer', 'bala', 'goma', 'bolo', 'achocolatado', 'toddy', 'nescau']):
        return 'Mercearia / Biscoitos e Doces'

    # --- 4. PADARIA E CONGELADOS ---
    if 'pão de queijo' in item_str:
        return 'Padaria / Congelados'
    if any(x in item_str for x in ['pão', 'pao', 'pullman', 'rap 10', 'torrada', 'croissant', 'baguete', 'bisnaguinha']):
        return 'Padaria / Pães'
    if any(x in item_str for x in ['pizza', 'lasanha congelada', 'batata congelada', 'batata palito', 'hamburguer congelado', 'sorvete', 'açai', 'açaí', 'picolé']):
        return 'Congelados e Sobremesas'

    # --- 5. LIMPEZA E HIGIENE ---
    if any(x in item_str for x in ['amaciante', 'desinfetante', 'desenfetante', 'bak', 'limpador', 'multiuso', 'veja', 'lustra', 'cloro', 'água sanitária', 'agua sanitaria', 'inseticida', 'saco lixo']):
        return 'Limpeza / Cuidados com a Casa'
    if any(x in item_str for x in ['sabão', 'sabao', 'tixan', 'detergente', 'minuano', 'bom bril', 'brilho', 'omo', 'ypê', 'esponja', 'lava roupas', 'lava louças']):
        return 'Limpeza / Lavanderia e Louça'
    if any(x in item_str for x in ['papel higiênico', 'papel higienico', 'neve', 'cotton', 'atualle', 'milli', 'guardanapo', 'papel toalha']):
        return 'Higiene / Papelaria'
    if any(x in item_str for x in ['shampoo', 'condicionador', 'elseve', 'desodorante', 'dove', 'fralda', 'sabonete', 'cremer', 'creme dental', 'colgate', 'absorvente', 'pantene', 'rexona', 'oral-b']):
        return 'Higiene / Cuidados Pessoais'

    # --- 6. HORTIFRUTI E OUTROS ---
    if any(x in item_str for x in ['alface', 'cheiro verde', 'alho', 'cebola', 'maçã', 'maca', 'limão', 'limao', 'abacate', 'batata', 'banana', 'caqui', 'tomate', 'laranja', 'melancia', 'cenoura', 'mamão', 'mamao', 'abacaxi', 'manga', 'uva', 'melão', 'ovos', 'ovo']):
        return 'Hortifruti / Ovos'
    if any(x in item_str for x in ['ração', 'racao', 'cão', 'gato', 'pet', 'vitamax', 'pedigree', 'whiskas', 'friskies']):
        return 'Pet Shop'
    if any(x in item_str for x in ['ventilador', 'mondial', 'copo', 'aruba', 'panela', 'pote', 'prato', 'talher', 'cadeira', 'lampada', 'lâmpada', 'churrasqueira']):
        return 'Bazar / Eletro'

    return 'Outros'
