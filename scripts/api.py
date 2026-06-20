from flask import Flask, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "database": "orabank_db",
    "user": "postgres",
    "password": "27109",
}


def connecter_db():
    """Connexion PostgreSQL avec RealDictCursor."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cursor


@app.route("/api/rapport", methods=["GET"])
def rapport():
    """Retourne les statistiques globales du pipeline ETL."""
    conn, cursor = connecter_db()

    cursor.execute("SELECT COUNT(*) as total FROM transactions;")
    total_valides = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM erreurs;")
    total_erreurs = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return jsonify(
        {
            "total_traite": total_valides + total_erreurs,
            "total_valides": total_valides,
            "total_erreurs": total_erreurs,
            "taux_erreur": round(
                (total_erreurs / (total_valides + total_erreurs)) * 100, 2
            ),
        }
    )


@app.route("/api/erreurs", methods=["GET"])
def liste_erreurs():
    """Retourne le détail de toutes les erreurs détectées."""
    conn, cursor = connecter_db()

    cursor.execute("""
        SELECT
            id,
            transaction_id,
            motif,
            detecte_le
        FROM erreurs
        ORDER BY transaction_id ASC;
    """)

    erreurs = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([dict(e) for e in erreurs])


@app.route("/api/transactions", methods=["GET"])
def liste_transactions():
    """Retourne toutes les transactions valides."""
    conn, cursor = connecter_db()

    cursor.execute("""
        SELECT
            id,
            date,
            montant,
            devise,
            type,
            compte_emetteur,
            compte_beneficiaire,
            statut
        FROM transactions
        ORDER BY date ASC;
    """)

    transactions = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([dict(t) for t in transactions])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
