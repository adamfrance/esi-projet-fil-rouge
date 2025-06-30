# Dockerfile pour le frontend
FROM node:18-alpine

# Update Alpine packages to reduce vulnerabilities
RUN apk update && apk upgrade --no-cache

WORKDIR /app

# Copier package.json en premier (pour le cache Docker)
COPY package.json package-lock.json* ./

# Installer les dépendances
RUN npm ci --only=production=false

# Le reste sera copié via le volume mapping
# Pas besoin de COPY . . ici car on utilise des volumes

# Exposer le port
EXPOSE 3000

# Commande de démarrage
CMD ["npm", "run", "dev"]