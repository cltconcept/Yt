#!/bin/bash

echo "===================================="
echo "  YouTube Pipeline - Démarrage"
echo "===================================="
echo ""

# Vérifier que Docker est lancé
if ! docker info > /dev/null 2>&1; then
    echo "[ERREUR] Docker n'est pas lancé !"
    echo ""
    echo "Veuillez lancer Docker Desktop et réessayer."
    exit 1
fi

# Créer les dossiers data si nécessaires
mkdir -p data/output data/uploads

echo "[1/3] Construction des images Docker..."
docker compose build 2>/dev/null || docker-compose build

echo ""
echo "[2/3] Démarrage des conteneurs..."
docker compose up -d 2>/dev/null || docker-compose up -d

echo ""
echo "[3/3] Vérification..."
sleep 5

echo ""
echo "===================================="
echo "  Application démarrée !"
echo "===================================="
echo ""
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:8000"
echo "  Settings : http://localhost:3000/settings"
echo ""
echo "  Pour voir les logs : docker compose logs -f"
echo "  Pour arrêter       : docker compose down"
echo ""

# Ouvrir le navigateur (Mac)
if command -v open &> /dev/null; then
    open http://localhost:3000
# Ouvrir le navigateur (Linux)
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
fi
