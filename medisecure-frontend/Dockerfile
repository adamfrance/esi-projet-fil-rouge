# Dockerfile pour le frontend
FROM node:18-alpine

# Update Alpine packages to reduce vulnerabilities
RUN apk update && apk upgrade --no-cache

WORKDIR /app

# Copier package.json
COPY package.json ./

# Installer les dépendances (utiliser npm install car pas de package-lock.json)
RUN npm install

# Exposer le port
EXPOSE 3000

# Commande de démarrage
CMD ["npm", "run", "dev"]