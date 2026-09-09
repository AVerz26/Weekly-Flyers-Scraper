import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config import DATA_DIR

DB_PATH = DATA_DIR / "flyers_database.db"

def get_connection() -> sqlite3.Connection:
    """Retorna conexão com o banco de dados SQLite."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados SQLite caso não existam."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mode TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            total_items INTEGER DEFAULT 0,
            excel_file TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            supermercado TEXT NOT NULL,
            categoria TEXT NOT NULL,
            item_original TEXT NOT NULL,
            produto_padronizado TEXT NOT NULL,
            marca TEXT,
            embalagem TEXT,
            valor REAL NOT NULL,
            data_postagem TEXT,
            link_imagem TEXT,
            post_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_offers_canonical ON offers(produto_padronizado);
        CREATE INDEX IF NOT EXISTS idx_offers_supermercado ON offers(supermercado);
        CREATE INDEX IF NOT EXISTS idx_offers_categoria ON offers(categoria);
        CREATE INDEX IF NOT EXISTS idx_offers_run_id ON offers(run_id);
    """)
    
    conn.commit()
    conn.close()

def save_run_and_offers(
    mode: str,
    provider: str,
    model: str,
    excel_file: str,
    offers_list: List[Dict[str, Any]]
) -> int:
    """Salva a execução e todas as ofertas extraídas no banco de dados SQLite."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO runs (timestamp, mode, provider, model, total_items, excel_file)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, mode, provider, model, len(offers_list), excel_file))
    
    run_id = cursor.lastrowid
    
    for of in offers_list:
        cursor.execute("""
            INSERT INTO offers (
                run_id, supermercado, categoria, item_original, 
                produto_padronizado, marca, embalagem, valor, 
                data_postagem, link_imagem, post_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            of.get("supermercado", "Supermercado"),
            of.get("categoria", "Outros"),
            of.get("item", of.get("item_original", "")),
            of.get("produto_padronizado", of.get("item", "")),
            of.get("marca", ""),
            of.get("embalagem", ""),
            float(of.get("valor", 0.0)),
            of.get("data_postagem", "-"),
            of.get("link", of.get("link_imagem", "")),
            of.get("post_url", "")
        ))
        
    conn.commit()
    conn.close()
    return run_id

def get_price_comparison(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_markets: int = 1
) -> List[Dict[str, Any]]:
    """
    Agrupa ofertas por produto padronizado e compara preços entre supermercados.
    Calcula: menor preço, maior preço, média, economia (R$ e %) e supermercado mais barato.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        WITH latest_offers AS (
            SELECT 
                id,
                run_id,
                supermercado,
                categoria,
                item_original,
                produto_padronizado,
                marca,
                embalagem,
                valor,
                data_postagem,
                link_imagem,
                post_url,
                created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY produto_padronizado, supermercado 
                    ORDER BY id DESC
                ) as rn
            FROM offers
        )
        SELECT 
            produto_padronizado,
            categoria,
            marca,
            embalagem,
            MIN(valor) as menor_preco,
            MAX(valor) as maior_preco,
            AVG(valor) as preco_medio,
            COUNT(DISTINCT supermercado) as qtd_mercados,
            COUNT(id) as total_ofertas
        FROM latest_offers
        WHERE rn = 1
    """
    params = []
    
    if category:
        query += " AND categoria = ?"
        params.append(category)
        
    if search:
        query += " AND (produto_padronizado LIKE ? OR item_original LIKE ? OR marca LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += """
        GROUP BY produto_padronizado
        HAVING qtd_mercados >= ?
        ORDER BY qtd_mercados DESC, menor_preco ASC
    """
    params.append(min_markets)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        prod_name = r["produto_padronizado"]
        menor = r["menor_preco"]
        maior = r["maior_preco"]
        medio = r["preco_medio"]
        economia_reais = round(maior - menor, 2)
        economia_pct = round(((maior - menor) / maior * 100), 1) if maior > 0 else 0.0
        
        # Busca a oferta mais recente deste produto por supermercado
        cursor.execute("""
            WITH latest_offers AS (
                SELECT 
                    supermercado, valor, data_postagem, link_imagem, post_url, item_original,
                    ROW_NUMBER() OVER (
                        PARTITION BY supermercado 
                        ORDER BY id DESC
                    ) as rn
                FROM offers
                WHERE produto_padronizado = ?
            )
            SELECT supermercado, valor, data_postagem, link_imagem, post_url, item_original
            FROM latest_offers
            WHERE rn = 1
            ORDER BY valor ASC
        """, (prod_name,))
        
        market_rows = cursor.fetchall()
        mercados_detalhes = []
        supermercado_mais_barato = market_rows[0]["supermercado"] if market_rows else ""
        
        for m in market_rows:
            mercados_detalhes.append({
                "supermercado": m["supermercado"],
                "valor": m["valor"],
                "data": m["data_postagem"],
                "imagem": m["link_imagem"],
                "post_url": m["post_url"],
                "item_original": m["item_original"],
                "is_cheapest": (m["valor"] == menor)
            })
            
        results.append({
            "produto_padronizado": prod_name,
            "categoria": r["categoria"],
            "marca": r["marca"] or "",
            "embalagem": r["embalagem"] or "",
            "menor_preco": menor,
            "maior_preco": maior,
            "preco_medio": round(medio, 2),
            "economia_reais": economia_reais,
            "economia_pct": economia_pct,
            "qtd_mercados": r["qtd_mercados"],
            "total_ofertas": r["total_ofertas"],
            "supermercado_mais_barato": supermercado_mais_barato,
            "mercados": mercados_detalhes
        })
        
    conn.close()
    return results

def get_database_stats() -> Dict[str, Any]:
    """Retorna estatísticas gerais do banco de dados SQLite."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM offers")
    total_ofertas = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT produto_padronizado) FROM offers")
    total_produtos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT supermercado) FROM offers")
    total_mercados = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM runs")
    total_execucoes = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(created_at) FROM offers")
    ultima_atualizacao = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_ofertas": total_ofertas,
        "total_produtos_unicos": total_produtos,
        "total_supermercados": total_mercados,
        "total_execucoes": total_execucoes,
        "ultima_atualizacao": ultima_atualizacao
    }

def get_distinct_products_summary(
    category: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retorna a lista de produtos padronizados únicos com contagem de ofertas,
    supermercados, faixa de preço e categoria para seletores e autocomplete.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            produto_padronizado,
            categoria,
            marca,
            embalagem,
            MIN(valor) as menor_preco,
            MAX(valor) as maior_preco,
            AVG(valor) as preco_medio,
            COUNT(DISTINCT supermercado) as qtd_mercados,
            COUNT(id) as total_ofertas,
            MAX(created_at) as ultima_atualizacao
        FROM offers
        WHERE 1=1
    """
    params = []
    
    if category:
        query += " AND categoria = ?"
        params.append(category)
        
    if search:
        query += " AND (produto_padronizado LIKE ? OR item_original LIKE ? OR marca LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    query += """
        GROUP BY produto_padronizado
        ORDER BY total_ofertas DESC, produto_padronizado ASC
    """
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    products = []
    for r in rows:
        products.append({
            "produto_padronizado": r["produto_padronizado"],
            "categoria": r["categoria"] or "Outros",
            "marca": r["marca"] or "",
            "embalagem": r["embalagem"] or "",
            "menor_preco": round(r["menor_preco"], 2) if r["menor_preco"] is not None else 0.0,
            "maior_preco": round(r["maior_preco"], 2) if r["maior_preco"] is not None else 0.0,
            "preco_medio": round(r["preco_medio"], 2) if r["preco_medio"] is not None else 0.0,
            "qtd_mercados": r["qtd_mercados"],
            "total_ofertas": r["total_ofertas"],
            "ultima_atualizacao": r["ultima_atualizacao"] or ""
        })
        
    conn.close()
    return products

def parse_date_tuple(data_postagem: Optional[str], created_at: Optional[str]) -> tuple:
    """Normaliza data para (iso_date 'YYYY-MM-DD', display_date 'DD/MM/YYYY')."""
    if data_postagem and data_postagem != "-":
        data_clean = data_postagem.strip()
        if len(data_clean) == 10 and data_clean[2] == "/" and data_clean[5] == "/":
            d, m, y = data_clean.split("/")
            return f"{y}-{m}-{d}", data_clean
        elif len(data_clean) >= 10 and data_clean[4] == "-" and data_clean[7] == "-":
            y, m, d = data_clean[:10].split("-")
            return f"{y}-{m}-{d}", f"{d}/{m}/{y}"
            
    if created_at:
        c_date = created_at.strip().split()[0]
        if len(c_date) >= 10 and c_date[4] == "-" and c_date[7] == "-":
            y, m, d = c_date[:10].split("-")
            return f"{y}-{m}-{d}", f"{d}/{m}/{y}"
            
    return "1970-01-01", "-"

def get_product_price_history(product_name: str) -> List[Dict[str, Any]]:
    """Retorna o histórico de preços de um produto ao longo do tempo (lista simples)."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.id, o.supermercado, o.categoria, o.valor, o.data_postagem, 
               o.created_at, o.link_imagem, o.item_original, o.marca, o.embalagem, o.post_url
        FROM offers o
        WHERE o.produto_padronizado = ?
        ORDER BY o.created_at DESC
    """, (product_name,))
    
    rows = cursor.fetchall()
    history = [dict(r) for r in rows]
    conn.close()
    return history

def get_product_price_history_analytics(product_name: str) -> Dict[str, Any]:
    """
    Retorna o histórico cronológico completo, séries temporais para gráficos Chart.js,
    estatísticas analíticas e KPIs para um produto específico.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.id, o.supermercado, o.categoria, o.valor, o.data_postagem, 
               o.created_at, o.link_imagem, o.item_original, o.marca, o.embalagem, o.post_url
        FROM offers o
        WHERE o.produto_padronizado = ?
        ORDER BY o.created_at ASC
    """, (product_name,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {
            "produto_padronizado": product_name,
            "categoria": "",
            "marca": "",
            "embalagem": "",
            "stats": {},
            "timeline": [],
            "chart_data": {
                "dates": [],
                "datasets": [],
                "average_series": []
            }
        }
        
    records = []
    supermercados_set = set()
    category = rows[0]["categoria"] or "Outros"
    brand = rows[0]["marca"] or ""
    pack = rows[0]["embalagem"] or ""
    
    for r in rows:
        iso_date, display_date = parse_date_tuple(r["data_postagem"], r["created_at"])
        item_dict = {
            "id": r["id"],
            "supermercado": r["supermercado"],
            "categoria": r["categoria"] or category,
            "valor": round(float(r["valor"]), 2),
            "data_postagem": r["data_postagem"] or "-",
            "created_at": r["created_at"],
            "iso_date": iso_date,
            "display_date": display_date,
            "link_imagem": r["link_imagem"] or "",
            "post_url": r["post_url"] or "",
            "item_original": r["item_original"] or product_name,
            "marca": r["marca"] or brand,
            "embalagem": r["embalagem"] or pack
        }
        records.append(item_dict)
        supermercados_set.add(r["supermercado"])
        if not brand and r["marca"]:
            brand = r["marca"]
        if not pack and r["embalagem"]:
            pack = r["embalagem"]
            
    # Ordena cronologicamente por iso_date, depois por created_at
    records.sort(key=lambda x: (x["iso_date"], x["created_at"]))
    
    # Cálculos estatísticos
    precos = [rec["valor"] for rec in records]
    menor_preco = min(precos)
    maior_preco = max(precos)
    preco_medio = round(sum(precos) / len(precos), 2)
    
    # Registro com menor e maior preço
    rec_menor = next((rec for rec in records if rec["valor"] == menor_preco), records[0])
    rec_maior = next((rec for rec in records if rec["valor"] == maior_preco), records[0])
    rec_recente = records[-1]
    
    # Variação em relação à média
    variacao_vs_medio = round(((rec_recente["valor"] - preco_medio) / preco_medio * 100), 1) if preco_medio > 0 else 0.0
    
    stats = {
        "menor_preco": menor_preco,
        "menor_mercado": rec_menor["supermercado"],
        "menor_data": rec_menor["display_date"],
        "maior_preco": maior_preco,
        "maior_mercado": rec_maior["supermercado"],
        "maior_data": rec_maior["display_date"],
        "preco_medio": preco_medio,
        "preco_recente": rec_recente["valor"],
        "recente_mercado": rec_recente["supermercado"],
        "recente_data": rec_recente["display_date"],
        "variacao_vs_medio_pct": variacao_vs_medio,
        "total_registros": len(records),
        "qtd_mercados": len(supermercados_set),
        "supermercados": sorted(list(supermercados_set))
    }
    
    # Estruturação para Chart.js
    # Obter todas as datas únicas ordenadas
    unique_dates_map = {}
    for rec in records:
        key = rec["iso_date"]
        if key not in unique_dates_map:
            unique_dates_map[key] = rec["display_date"]
            
    sorted_iso_dates = sorted(unique_dates_map.keys())
    date_labels = [unique_dates_map[d] for d in sorted_iso_dates]
    
    # Para cada supermercado, mapear valor por data (usando o último valor registrado se houver mais de um na mesma data)
    datasets = []
    for mkt in sorted(list(supermercados_set)):
        mkt_records = [r for r in records if r["supermercado"] == mkt]
        date_to_val = {}
        for r in mkt_records:
            date_to_val[r["iso_date"]] = r["valor"]
            
        data_points = []
        for d in sorted_iso_dates:
            data_points.append(date_to_val.get(d, None))
            
        datasets.append({
            "label": mkt,
            "data": data_points,
            "raw_points": [
                {"date": d, "display_date": unique_dates_map[d], "valor": date_to_val.get(d, None)} 
                for d in sorted_iso_dates
            ]
        })
        
    # Média diária geral
    average_series = []
    for d in sorted_iso_dates:
        vals = [r["valor"] for r in records if r["iso_date"] == d]
        if vals:
            average_series.append(round(sum(vals) / len(vals), 2))
        else:
            average_series.append(None)
            
    # Tabela com ordem decrescente (mais recente primeiro)
    timeline_desc = sorted(records, key=lambda x: (x["iso_date"], x["created_at"]), reverse=True)
    
    # Adicionar variação percentual individual vs média para cada registro da tabela
    for item in timeline_desc:
        diff = round(item["valor"] - preco_medio, 2)
        diff_pct = round((diff / preco_medio * 100), 1) if preco_medio > 0 else 0.0
        item["diff_vs_avg"] = diff
        item["diff_vs_avg_pct"] = diff_pct
        
    return {
        "produto_padronizado": product_name,
        "categoria": category,
        "marca": brand,
        "embalagem": pack,
        "stats": stats,
        "timeline": timeline_desc,
        "chart_data": {
            "iso_dates": sorted_iso_dates,
            "date_labels": date_labels,
            "datasets": datasets,
            "average_series": average_series
        }
    }
