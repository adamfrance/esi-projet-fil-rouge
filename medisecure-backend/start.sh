# medisecure-backend/start.sh
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
        psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -c "CREATE DATABASE medisecure;"
    fi
    
    # Exécuter le script d'initialisation si il existe
    if [ -f "/app/init.sql" ]; then
        echo 'Initialisation de la base de données...'
        psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d medisecure -f /app/init.sql
        
        if [ $? -eq 0 ]; then
            echo "Base de données initialisée avec succès"
        else
            echo "Avertissement : Des erreurs sont survenues lors de l'initialisation de la base de données, mais l'exécution continue."
        fi
    fi
else
    echo "Mode développement local détecté, pas d'attente de la base de données Docker"
fi

# Vérifier si l'utilisateur admin existe
if [ "$ENVIRONMENT" = "docker" ]; then
    ADMIN_EXISTS=$(psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d medisecure -c "SELECT COUNT(*) FROM users WHERE email = 'admin@medisecure.com'" -t | tr -d ' ' 2>/dev/null || echo "0")
    
    if [ "$ADMIN_EXISTS" = "1" ]; then
        echo 'Utilisateur administrateur trouvé:'
        echo 'Email: admin@medisecure.com'
        echo 'Mot de passe: Admin123!'
    else
        echo 'AVERTISSEMENT: Utilisateur administrateur non trouvé!'
        echo 'Cela peut être dû à des erreurs dans le script d'\''initialisation.'
    fi
fi

# Définir les variables d'environnement par défaut si elles ne sont pas définies
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export ENVIRONMENT=${ENVIRONMENT:-development}

echo "=== Démarrage de MediSecure API ==="
echo "Host: $HOST"
echo "Port: $PORT"
echo "Environment: $ENVIRONMENT"
echo "Database URL: ${DATABASE_URL:-Non définie}"

# Démarrer l'API avec les bonnes variables d'environnement
echo 'Démarrage de l API...'
exec uvicorn api.main:app --host "$HOST" --port "$PORT" --reload