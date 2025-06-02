#!/bin/bash
set -e

echo 'Attente de la base de données...'

# Configuration de la connexion PostgreSQL avec mot de passe
export PGPASSWORD=postgres

# Fonction pour vérifier la connexion à la base de données
wait_for_postgres() {
    echo "Vérification de la connexion à la base de données..."
    local host=${DB_HOST:-localhost}
    local port=${DB_PORT:-5432}
    local user=${DB_USER:-postgres}
    
    for i in {1..30}; do
        if pg_isready -h "$host" -p "$port" -U "$user" >/dev/null 2>&1; then
            echo "Base de données prête !"
            return 0
        fi
        echo "En attente de la base de données... $i/30"
        sleep 2
    done
    
    echo "Impossible de se connecter à la base de données après 30 tentatives"
    return 1
}

# Vérifier si nous sommes en mode développement local ou Docker
if [ "$ENVIRONMENT" = "docker" ]; then
    # En mode Docker, attendre la base de données
    wait_for_postgres
    
    # Vérifier si la base de données existe, sinon la créer
    echo "Vérification de l'existence de la base de données..."
    if ! psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -lqt | cut -d \| -f 1 | grep -qw medisecure; then
        echo "Création de la base de données medisecure..."
        psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -c "CREATE DATABASE medisecure;" || echo "Base de données existe déjà"
    fi
    
    # Exécuter le script d'initialisation si il existe
    # if [ -f "/app/init.sql" ]; then
    #     echo 'Initialisation de la base de données...'
    #     psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d medisecure -f /app/init.sql || echo "Initialisation échouée, mais on continue"
    # fi
else
    echo "Mode développement local détecté"
fi

echo "Vérification de l'existence de l'utilisateur admin..."
if psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d medisecure -t -c "SELECT EXISTS(SELECT 1 FROM users WHERE email='admin@medisecure.com');" | grep -q 't'; then
    echo "Utilisateur admin trouvé dans la base de données."
else
    echo "ERREUR: Utilisateur admin NON TROUVÉ dans la base de données."
    # Optionally, exit here if admin user is critical for startup
    # exit 1
fi

# Définir les variables d'environnement par défaut
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export ENVIRONMENT=${ENVIRONMENT:-development}

echo "=== Démarrage de MediSecure API ==="
echo "Host: $HOST"
echo "Port: $PORT"
echo "Environment: $ENVIRONMENT"

# Démarrer l'API
echo 'Démarrage de l API...'
exec uvicorn api.main:app --host "$HOST" --port "$PORT" --reload