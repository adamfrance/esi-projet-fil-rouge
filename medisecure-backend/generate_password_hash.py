# medisecure-backend/generate_password_hash.py
#!/usr/bin/env python
"""
Script pour générer des hash de mots de passe compatibles avec bcrypt.
Utilisation : python generate_password_hash.py
"""

import bcrypt
import sys
from passlib.context import CryptContext

def generate_password_hash(password: str) -> str:
    """
    Génère un hash bcrypt pour un mot de passe donné.
    
    Args:
        password: Le mot de passe à hasher
        
    Returns:
        str: Le hash du mot de passe
    """
    # Méthode 1 : Utiliser bcrypt directement
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_string = hashed.decode('utf-8')
    
    # Méthode 2 : Utiliser passlib (comme dans l'application)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hash_passlib = pwd_context.hash(password)
    
    # Vérifier que les deux méthodes fonctionnent
    verify_bcrypt = bcrypt.checkpw(password.encode('utf-8'), hashed)
    verify_passlib = pwd_context.verify(password, hash_passlib)
    
    print(f"\n=== Génération de hash pour le mot de passe : {password} ===")
    print(f"\nHash avec bcrypt direct : {hash_string}")
    print(f"Vérification bcrypt : {verify_bcrypt}")
    print(f"\nHash avec passlib : {hash_passlib}")
    print(f"Vérification passlib : {verify_passlib}")
    
    print(f"\n=== Hash recommandé pour la base de données ===")
    print(f"{hash_string}")
    
    # Générer le SQL d'update
    print(f"\n=== Commande SQL pour mettre à jour le mot de passe admin ===")
    print(f"UPDATE users SET hashed_password = '{hash_string}' WHERE email = 'admin@medisecure.com';")
    
    return hash_string

def verify_password_hash(password: str, hashed_password: str) -> bool:
    """
    Vérifie qu'un mot de passe correspond à son hash.
    
    Args:
        password: Le mot de passe en clair
        hashed_password: Le hash à vérifier
        
    Returns:
        bool: True si le mot de passe correspond
    """
    try:
        # Méthode 1 : bcrypt
        is_valid_bcrypt = bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        
        # Méthode 2 : passlib
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        is_valid_passlib = pwd_context.verify(password, hashed_password)
        
        print(f"\nVérification du mot de passe '{password}'")
        print(f"Avec bcrypt : {is_valid_bcrypt}")
        print(f"Avec passlib : {is_valid_passlib}")
        
        return is_valid_bcrypt and is_valid_passlib
    except Exception as e:
        print(f"Erreur lors de la vérification : {e}")
        return False

def main():
    """Fonction principale du script."""
    print("=== Générateur de hash de mot de passe pour MediSecure ===\n")
    
    # Générer le hash pour Admin123!
    admin_password = "Admin123!"
    admin_hash = generate_password_hash(admin_password)
    
    # Vérifier le hash existant dans la base
    existing_hash = "$2b$12$kAqB5L8z7JNm0xjHwZ7Ane3cQh/2A8x2yrJvONhBQbvQyh.2cVy3."
    print(f"\n=== Vérification du hash existant dans la base ===")
    verify_password_hash(admin_password, existing_hash)
    
    # Générer des hash pour d'autres utilisateurs de test
    print("\n\n=== Génération de hash pour d'autres utilisateurs ===")
    test_passwords = [
        ("doctor1@medisecure.com", "Doctor123!"),
        ("doctor2@medisecure.com", "Doctor123!"),
        ("nurse1@medisecure.com", "Nurse123!")
    ]
    
    for email, password in test_passwords:
        hash_pwd = generate_password_hash(password)
        print(f"\nUPDATE users SET hashed_password = '{hash_pwd}' WHERE email = '{email}';")

if __name__ == "__main__":
    main()