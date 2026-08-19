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
        
        # Busca todas as ofertas detalhadas deste produto por supermercado
        cursor.execute("""
            SELECT supermercado, valor, data_postagem, link_imagem, post_url, item_original
            FROM offers
            WHERE produto_padronizado = ?
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

def get_product_price_history(product_name: str) -> List[Dict[str, Any]]:
    """Retorna o histórico de preços de um produto ao longo do tempo."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT o.supermercado, o.valor, o.data_postagem, o.created_at, o.link_imagem, o.item_original
        FROM offers o
        WHERE o.produto_padronizado = ?
        ORDER BY o.created_at DESC
    """, (product_name,))
    
    rows = cursor.fetchall()
    history = [dict(r) for r in rows]
    conn.close()
    return history
