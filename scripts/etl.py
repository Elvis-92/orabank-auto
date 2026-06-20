import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# --- CONFIGURATION ---
DB_CONFIG = {
    "host": "localhost",
    "database": "orabank_db",
    "user": "postgres",
    "password": "27109",
}

TYPES_VALIDES = ["virement", "retrait", "depot"]
DEVISES_VALIDES = ["XOF", "EUR", "USD"]


def connecter_db():
    """Établit la connexion à PostgreSQL et retourne connection + curseur."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    return conn, cursor


def valider_transaction(row, ids_vus):
    """
    Valide une transaction et retourne la liste des erreurs détectées.
    row = une ligne du CSV (Series pandas)
    ids_vus = ensemble des ids déjà traités (pour détecter les doublons)
    """
    erreurs = []

    # Règle 1 — Montant manquant
    if pd.isna(row["montant"]):
        erreurs.append("Montant manquant")

    # Règle 2 — Montant non numérique
    else:
        try:
            montant = float(row["montant"])
        except (ValueError, TypeError):
            erreurs.append("Montant non numérique")
            montant = None

        # Règle 3 — Montant négatif
        if montant is not None and montant < 0:
            erreurs.append("Montant négatif")

    # Règle 4 — Type de transaction invalide
    if str(row["type"]).strip() not in TYPES_VALIDES:
        erreurs.append(f"Type invalide : {row['type']}")

    # Règle 5 — Compte émetteur manquant
    if pd.isna(row["compte_emetteur"]) or str(row["compte_emetteur"]).strip() == "":
        erreurs.append("Compte émetteur manquant")

    # Règle 6 — Compte bénéficiaire manquant
    if (
        pd.isna(row["compte_beneficiaire"])
        or str(row["compte_beneficiaire"]).strip() == ""
    ):
        erreurs.append("Compte bénéficiaire manquant")

    # Règle 7 — Virement vers soi-même
    if str(row["compte_emetteur"]) == str(row["compte_beneficiaire"]):
        erreurs.append("Émetteur identique au bénéficiaire")

    # Règle 8 — Doublon par contenu
    signature = (
        str(row["montant"]),
        str(row["compte_emetteur"]),
        str(row["compte_beneficiaire"]),
        str(row["date"]),
    )
    if signature in ids_vus:
        erreurs.append(
            f"Transaction dupliquée : contenu identique à une transaction existante"
        )

    return erreurs


def traiter_csv(chemin_csv):
    """
    Lit le CSV, valide chaque transaction,
    insère les valides en base et logue les erreurs.
    """
    print(f"\n{'='*50}")
    print(f"  ORABANK — Pipeline ETL")
    print(f"  Démarré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    print(f"{'='*50}\n")

    # --- EXTRACT ---
    print("📂 Lecture du fichier CSV...")
    df = pd.read_csv(chemin_csv)
    print(f"   {len(df)} transactions trouvées.\n")

    # --- TRANSFORM ---
    print("🔍 Validation des transactions...")
    transactions_valides = []
    erreurs_detectees = []
    ids_vus = set()

    for _, row in df.iterrows():
        erreurs = valider_transaction(row, ids_vus)
        ids_vus.add(
            (
                str(row["montant"]),
                str(row["compte_emetteur"]),
                str(row["compte_beneficiaire"]),
                str(row["date"]),
            )
        )

        if erreurs:
            for motif in erreurs:
                erreurs_detectees.append(
                    {
                        "transaction_id": int(row["id"]),
                        "motif": motif,
                        "donnee_brute": str(row.to_dict()),
                    }
                )
            print(f"   ❌ Transaction #{int(row['id'])} rejetée — {', '.join(erreurs)}")
        else:
            transactions_valides.append(
                {
                    "id": int(row["id"]),
                    "date": row["date"],
                    "montant": float(row["montant"]),
                    "devise": row["devise"],
                    "type": row["type"],
                    "compte_emetteur": row["compte_emetteur"],
                    "compte_beneficiaire": row["compte_beneficiaire"],
                    "statut": row["statut"],
                }
            )
            print(f"   ✅ Transaction #{int(row['id'])} valide")

    # --- LOAD ---
    print(f"\n💾 Insertion en base PostgreSQL...")
    conn, cursor = connecter_db()

    # Insertion des transactions valides
    if transactions_valides:
        execute_values(
            cursor,
            """
            INSERT INTO transactions
                (id, date, montant, devise, type,
                 compte_emetteur, compte_beneficiaire, statut)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """,
            [
                (
                    t["id"],
                    t["date"],
                    t["montant"],
                    t["devise"],
                    t["type"],
                    t["compte_emetteur"],
                    t["compte_beneficiaire"],
                    t["statut"],
                )
                for t in transactions_valides
            ],
        )

    # Insertion des erreurs
    if erreurs_detectees:
        execute_values(
            cursor,
            """
            INSERT INTO erreurs (transaction_id, motif, donnee_brute)
            VALUES %s
            ON CONFLICT (transaction_id, motif) DO NOTHING
        """,
            [
                (e["transaction_id"], e["motif"], e["donnee_brute"])
                for e in erreurs_detectees
            ],
        )

    conn.commit()
    cursor.close()
    conn.close()

    # --- RAPPORT FINAL ---
    print(f"\n{'='*50}")
    print(f"  RAPPORT D'EXÉCUTION")
    print(f"{'='*50}")
    print(f"  Total traité     : {len(df)}")
    print(f"  ✅ Valides        : {len(transactions_valides)}")
    print(f"  ❌ Erreurs        : {len(erreurs_detectees)}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    traiter_csv("data/transactions.csv")
