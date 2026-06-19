CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    montant NUMERIC(15, 2) NOT NULL,
    devise VARCHAR(10) NOT NULL,
    type VARCHAR(50) NOT NULL,
    compte_emetteur VARCHAR(20) NOT NULL,
    compte_beneficiaire VARCHAR(20) NOT NULL,
    statut VARCHAR(20) NOT NULL,
    insere_le TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS erreurs (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER,
    motif VARCHAR(255) NOT NULL,
    donnee_brute TEXT,
    detecte_le TIMESTAMP DEFAULT NOW()
);
