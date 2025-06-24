# Dockerfile pour le frontend
FROM node:18-alpine

# Update Alpine packages to reduce vulnerabilities
RUN apk update && apk upgrade --no-cache

WORKDIR /app

# Installer les dépendances
COPY package.json .
RUN npm i

# Copier le code source
COPY . .

# Exposer le port
EXPOSE 3000

# Commande de démarrage
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]