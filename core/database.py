import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from core.config import DATA_DIR

DB_PATH = DATA_DIR / "offers.db"

def get_db_connection() -> sqlite3.Connection:
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados e cria índices necessários."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de Ofertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash_dedup TEXT UNIQUE NOT NULL,
            supermercado TEXT NOT NULL,
            categoria TEXT NOT NULL,
            item TEXT NOT NULL,
            valor REAL NOT NULL,
            data_postagem TEXT,
            link TEXT,
            post_url TEXT,
            run_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índices para consultas rápidas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_supermercado ON offers(supermercado)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_categoria ON offers(categoria)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_data_postagem ON offers(data_postagem)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_hash ON offers(hash_dedup)")

    # Tabela de Histórico de Execuções
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_scraped INTEGER DEFAULT 0,
            total_new INTEGER DEFAULT 0,
            total_duplicates INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            date_mode TEXT,
            error_message TEXT
        )
    """)

    conn.commit()
    conn.close()

def compute_offer_hash(supermercado: str, item: str, valor: float, data_postagem: Optional[str]) -> str:
    """
    Gera um hash único para identificar a oferta e evitar duplicatas.
    Usa supermercado + item normalizado + valor formatado + data da postagem.
    """
    s_norm = (supermercado or "").strip().lower()
    i_norm = "".join((item or "").strip().lower().split()) # Remove espaços extras
    v_norm = f"{float(valor):.2f}"
    d_norm = (data_postagem or "").strip()
    
    raw_key = f"{s_norm}|{i_norm}|{v_norm}|{d_norm}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def save_offers(records: List[Dict[str, Any]], run_id: Optional[str] = None) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Salva uma lista de ofertas no banco de dados com deduplicação.
    Retorna uma tupla: (total_novas_inseridas, total_duplicadas_ignoradas, lista_de_novos_registros).
    """
    if not records:
        return 0, 0, []

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    novas_ofertas: List[Dict[str, Any]] = []
    total_novas = 0
    total_duplicadas = 0

    if not run_id:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

    for rec in records:
        supermercado = rec.get("supermercado", "").strip()
        categoria = rec.get("categoria", "Geral").strip()
        item = rec.get("item", "").strip()
        try:
            valor = float(rec.get("valor", 0))
        except (ValueError, TypeError):
            continue

        data_postagem = rec.get("data_postagem", "")
        link = rec.get("link", "")
        post_url = rec.get("post_url", "")

        if not supermercado or not item or valor <= 0:
            continue

        hash_dedup = compute_offer_hash(supermercado, item, valor, data_postagem)

        # Tenta inserir no banco. Se o hash já existir (UNIQUE constraint), ignora.
        try:
            cursor.execute("""
                INSERT INTO offers (
                    hash_dedup, supermercado, categoria, item, valor, 
                    data_postagem, link, post_url, run_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hash_dedup, supermercado, categoria, item, valor, 
                data_postagem, link, post_url, run_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            total_novas += 1
            rec_copy = dict(rec)
            rec_copy["id"] = cursor.lastrowid
            rec_copy["hash_dedup"] = hash_dedup
            novas_ofertas.append(rec_copy)
        except sqlite3.IntegrityError:
            # Já existia no banco (duplicada)
            total_duplicadas += 1

    # Registra a execução na tabela scrape_runs
    try:
        cursor.execute("""
            INSERT INTO scrape_runs (
                run_id, created_at, total_scraped, total_new, total_duplicates, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(records),
            total_novas,
            total_duplicadas,
            "completed"
        ))
    except Exception:
        pass

    conn.commit()
    conn.close()

    return total_novas, total_duplicadas, novas_ofertas

def get_db_stats() -> Dict[str, Any]:
    """Retorna estatísticas resumidas do banco de dados."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM offers")
    total_offers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT supermercado) FROM offers")
    total_supermercados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT categoria) FROM offers")
    total_categorias = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM scrape_runs")
    total_runs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT supermercado, COUNT(*) as count 
        FROM offers 
        GROUP BY supermercado 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_mercados = [{"supermercado": row["supermercado"], "count": row["count"]} for row in cursor.fetchall()]

    cursor.execute("""
        SELECT run_id, created_at, total_scraped, total_new, total_duplicates, status 
        FROM scrape_runs 
        ORDER BY id DESC 
        LIMIT 10
    """)
    recent_runs = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_offers": total_offers,
        "total_supermercados": total_supermercados,
        "total_categorias": total_categorias,
        "total_runs": total_runs,
        "top_supermercados": top_mercados,
        "recent_runs": recent_runs,
        "db_size_kb": round(DB_PATH.stat().st_size / 1024, 1) if DB_PATH.exists() else 0
    }

def get_recent_offers(
    limit: int = 100, 
    offset: int = 0, 
    supermercado: Optional[str] = None, 
    categoria: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Consulta ofertas salvas no banco com filtros e paginação."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM offers WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM offers WHERE 1=1"
    params = []

    if supermercado:
        query += " AND supermercado = ?"
        count_query += " AND supermercado = ?"
        params.append(supermercado)

    if categoria:
        query += " AND categoria = ?"
        count_query += " AND categoria = ?"
        params.append(categoria)

    if search:
        query += " AND (item LIKE ? OR supermercado LIKE ?)"
        count_query += " AND (item LIKE ? OR supermercado LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    items = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items
    }
