# Dockerfile - Ambiente di sviluppo Expo per l'app mobile Alvea (SDK 54).
#
# L'immagine contiene Node.js e gli strumenti Expo/EAS. Il codice del progetto
# viene montato come volume (vedi docker-compose.yml), quindi le dipendenze
# vengono installate al primo avvio dal comando del servizio.
FROM node:20

# EAS CLI (build/update/login) ed Expo CLI preinstallati.
RUN npm install -g eas-cli expo

WORKDIR /workspace/app

EXPOSE 8081 19000 19001 19006

CMD ["npx", "expo", "start", "--tunnel"]
