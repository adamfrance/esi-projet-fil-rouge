-- medisecure-backend/init.sql
-- Script d'initialisation de la base de données MediSecure

-- Suppression des types et tables existants pour une réinitialisation propre
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS patients CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TYPE IF EXISTS appointmentstatus CASCADE;
DROP TYPE IF EXISTS userrole CASCADE;

-- Création des types enum
CREATE TYPE userrole AS ENUM ('ADMIN', 'DOCTOR', 'NURSE', 'PATIENT', 'RECEPTIONIST');
CREATE TYPE appointmentstatus AS ENUM ('scheduled', 'confirmed', 'cancelled', 'completed', 'missed');

-- Création de la table users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  hashed_password VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  role userrole NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Création de la table patients
CREATE TABLE patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  date_of_birth DATE NOT NULL,
  gender VARCHAR(50) NOT NULL,
  address VARCHAR(200),
  city VARCHAR(100),
  postal_code VARCHAR(20),
  country VARCHAR(100),
  phone_number VARCHAR(20),
  email VARCHAR(255),
  blood_type VARCHAR(10),
  allergies JSONB DEFAULT '{}',
  chronic_diseases JSONB DEFAULT '{}',
  current_medications JSONB DEFAULT '{}',
  has_consent BOOLEAN DEFAULT TRUE,
  consent_date TIMESTAMP,
  gdpr_consent BOOLEAN DEFAULT TRUE,
  insurance_provider VARCHAR(100),
  insurance_id VARCHAR(100),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- Création de la table appointments
CREATE TABLE appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
  doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  status appointmentstatus DEFAULT 'scheduled',
  reason VARCHAR(255),
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  CONSTRAINT check_appointment_times CHECK (end_time > start_time)
);

-- Création des index pour améliorer les performances
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_patients_email ON patients(email);
CREATE INDEX idx_patients_user_id ON patients(user_id);
CREATE INDEX idx_appointments_patient_id ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor_id ON appointments(doctor_id);
CREATE INDEX idx_appointments_start_time ON appointments(start_time);
CREATE INDEX idx_appointments_status ON appointments(status);

-- Création des triggers pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_patients_updated_at
  BEFORE UPDATE ON patients
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_appointments_updated_at
  BEFORE UPDATE ON appointments
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Insertion de l'utilisateur admin avec le bon hash de mot de passe
-- Le hash correspond au mot de passe "Admin123!"
INSERT INTO users (id, email, hashed_password, first_name, last_name, role, is_active, created_at, updated_at)
VALUES (
  '00000000-0000-0000-0000-000000000000'::UUID,
  'admin@medisecure.com',
  '$2b$12$kAqB5L8z7JNm0xjHwZ7Ane3cQh/2A8x2yrJvONhBQbvQyh.2cVy3.',  -- Hash correct pour "Admin123!"
  'Admin',
  'Utilisateur',
  'ADMIN',
  TRUE,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);

-- Insertion de médecins de test
INSERT INTO users (id, email, hashed_password, first_name, last_name, role, is_active)
VALUES 
  ('11111111-1111-1111-1111-111111111111'::UUID, 'doctor1@medisecure.com', '$2b$12$kAqB5L8z7JNm0xjHwZ7Ane3cQh/2A8x2yrJvONhBQbvQyh.2cVy3.', 'Jean', 'Dupont', 'DOCTOR', TRUE),
  ('22222222-2222-2222-2222-222222222222'::UUID, 'doctor2@medisecure.com', '$2b$12$kAqB5L8z7JNm0xjHwZ7Ane3cQh/2A8x2yrJvONhBQbvQyh.2cVy3.', 'Marie', 'Martin', 'DOCTOR', TRUE);

-- Insertion de patients de test
INSERT INTO patients (id, first_name, last_name, date_of_birth, gender, address, city, postal_code, country, phone_number, email, has_consent, gdpr_consent)
VALUES 
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::UUID, 'Sophie', 'Bernard', '1985-06-15', 'female', '10 rue de la Paix', 'Paris', '75001', 'France', '0612345678', 'sophie.bernard@example.com', TRUE, TRUE),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::UUID, 'Pierre', 'Durand', '1975-03-22', 'male', '25 avenue Victor Hugo', 'Lyon', '69001', 'France', '0698765432', 'pierre.durand@example.com', TRUE, TRUE);

-- Insertion de clients/patients supplémentaires avec informations complètes et noms diversifiés
INSERT INTO patients (id, first_name, last_name, date_of_birth, gender, address, city, postal_code, country, phone_number, email, blood_type, has_consent, gdpr_consent, insurance_provider, insurance_id, notes)
VALUES 
  ('a1b2c3d4-e5f6-4789-a123-456789abcdef'::UUID, 'Amina', 'Ben-Ahmed', '1992-11-08', 'female', '15 boulevard Saint-Michel', 'Marseille', '13001', 'France', '0654321098', 'amina.benahmed@example.com', 'A+', TRUE, TRUE, 'CPAM Marseille', 'MAR123456789', 'Patiente suivie pour hypertension légère'),
  ('b2c3d4e5-f6a7-4890-b234-567890bcdef1'::UUID, 'Kwame', 'Asante', '1968-04-30', 'male', '8 rue des Lilas', 'Toulouse', '31000', 'France', '0567890123', 'kwame.asante@example.com', 'O-', TRUE, TRUE, 'Mutuelle Générale', 'TOU987654321', 'Diabétique de type 2, contrôles réguliers'),
  ('c3d4e5f6-a7b8-4901-c345-678901cdef12'::UUID, 'Li', 'Wei', '1987-09-14', 'female', '42 avenue de la République', 'Nice', '06000', 'France', '0678901234', 'li.wei@example.com', 'B+', TRUE, TRUE, 'Harmonie Mutuelle', 'NIC456789123', 'Allergie aux pénicillines'),
  ('d4e5f6a7-b8c9-4012-d456-789012def123'::UUID, 'Fatou', 'Diallo', '1995-12-03', 'female', '7 place de la Mairie', 'Bordeaux', '33000', 'France', '0689012345', 'fatou.diallo@example.com', 'AB+', TRUE, TRUE, 'MGEN', 'BOR789123456', 'Sportive, suivi préventif');

-- Insertion de rendez-vous pour les patients existants et nouveaux
INSERT INTO appointments (id, patient_id, doctor_id, start_time, end_time, status, reason, notes)
VALUES 
  -- Rendez-vous pour Sophie Bernard (aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)
  ('e5f6a7b8-c9d0-4123-e567-890123ef1234'::UUID, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-02 09:00:00', '2025-07-02 09:30:00', 'scheduled', 'Consultation générale', 'Contrôle de routine'),
  ('f6a7b8c9-d0e1-4234-f678-901234f12345'::UUID, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-15 14:30:00', '2025-07-15 15:00:00', 'confirmed', 'Suivi spécialisé', 'Résultats d analyses sanguines'),
  ('a7b8c9d0-e1f2-4345-a789-012345a12456'::UUID, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-06-15 10:00:00', '2025-06-15 10:30:00', 'completed', 'Visite de contrôle', 'Tension artérielle normale'),
  
  -- Rendez-vous pour Pierre Durand (bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb)
  ('b8c9d0e1-f2a3-4456-b890-123456b12567'::UUID, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-03 11:00:00', '2025-07-03 11:30:00', 'scheduled', 'Consultation cardiologique', 'ECG de contrôle programmé'),
  ('c9d0e1f2-a3b4-4567-c901-234567c12678'::UUID, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-20 16:00:00', '2025-07-20 16:30:00', 'scheduled', 'Renouvellement ordonnance', 'Prescription médicaments chroniques'),
  ('d0e1f2a3-b4c5-4678-d012-345678d12789'::UUID, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-06-01 08:30:00', '2025-06-01 09:00:00', 'completed', 'Bilan annuel', 'Excellent état général'),
  
  -- Rendez-vous pour Amina Ben-Ahmed (a1b2c3d4-e5f6-4789-a123-456789abcdef)
  ('e1f2a3b4-c5d6-4789-e123-456789e1289a'::UUID, 'a1b2c3d4-e5f6-4789-a123-456789abcdef'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-05 13:30:00', '2025-07-05 14:00:00', 'confirmed', 'Suivi hypertension', 'Mesure tension et ajustement traitement'),
  ('f2a3b4c5-d6e7-4890-f234-567890f1390b'::UUID, 'a1b2c3d4-e5f6-4789-a123-456789abcdef'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-25 10:30:00', '2025-07-25 11:00:00', 'scheduled', 'Consultation spécialisée', 'Évaluation cardiovasculaire'),
  ('a3b4c5d6-e7f8-4901-a345-678901a1401c'::UUID, 'a1b2c3d4-e5f6-4789-a123-456789abcdef'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-05-20 15:00:00', '2025-05-20 15:30:00', 'completed', 'Première consultation', 'Diagnostic hypertension légère'),
  
  -- Rendez-vous pour Kwame Asante (b2c3d4e5-f6a7-4890-b234-567890bcdef1)
  ('b4c5d6e7-f8a9-4012-b456-789012b1512d'::UUID, 'b2c3d4e5-f6a7-4890-b234-567890bcdef1'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-08 09:30:00', '2025-07-08 10:00:00', 'scheduled', 'Contrôle diabète', 'Surveillance glycémie et HbA1c'),
  ('c5d6e7f8-a9b0-4123-c567-890123c1623e'::UUID, 'b2c3d4e5-f6a7-4890-b234-567890bcdef1'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-22 14:00:00', '2025-07-22 14:30:00', 'confirmed', 'Suivi podologique', 'Examen des pieds - prévention complications'),
  ('d6e7f8a9-b0c1-4234-d678-901234d1734f'::UUID, 'b2c3d4e5-f6a7-4890-b234-567890bcdef1'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-06-10 11:30:00', '2025-06-10 12:00:00', 'completed', 'Bilan trimestriel', 'Diabète bien équilibré'),
  
  -- Rendez-vous pour Li Wei (c3d4e5f6-a7b8-4901-c345-678901cdef12)
  ('e7f8a9b0-c1d2-4345-e789-012345e18450'::UUID, 'c3d4e5f6-a7b8-4901-c345-678901cdef12'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-10 08:00:00', '2025-07-10 08:30:00', 'scheduled', 'Consultation allergologie', 'Test allergie nouveaux médicaments'),
  ('f8a9b0c1-d2e3-4456-f890-123456f19561'::UUID, 'c3d4e5f6-a7b8-4901-c345-678901cdef12'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-28 16:30:00', '2025-07-28 17:00:00', 'scheduled', 'Suivi gynécologique', 'Consultation de routine annuelle'),
  ('a9b0c1d2-e3f4-4567-a901-234567a10672'::UUID, 'c3d4e5f6-a7b8-4901-c345-678901cdef12'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-06-05 13:00:00', '2025-06-05 13:30:00', 'completed', 'Urgence allergie', 'Réaction allergique médicamenteuse - traitée'),
  
  -- Rendez-vous pour Fatou Diallo (d4e5f6a7-b8c9-4012-d456-789012def123)
  ('b0c1d2e3-f4a5-4678-b012-345678b11783'::UUID, 'd4e5f6a7-b8c9-4012-d456-789012def123'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-07-12 17:00:00', '2025-07-12 17:30:00', 'confirmed', 'Médecine du sport', 'Bilan cardiologique pour compétition'),
  ('c1d2e3f4-a5b6-4789-c123-456789c12894'::UUID, 'd4e5f6a7-b8c9-4012-d456-789012def123'::UUID, '11111111-1111-1111-1111-111111111111'::UUID, '2025-07-30 10:00:00', '2025-07-30 10:30:00', 'scheduled', 'Vaccination voyage', 'Préparation voyage Asie du Sud-Est'),
  ('d2e3f4a5-b6c7-4890-d234-567890d139a5'::UUID, 'd4e5f6a7-b8c9-4012-d456-789012def123'::UUID, '22222222-2222-2222-2222-222222222222'::UUID, '2025-06-25 12:00:00', '2025-06-25 12:30:00', 'completed', 'Visite médicale', 'Certificat médical sport obtenu');
-- Vérification de l'installation
DO $$
BEGIN
  RAISE NOTICE 'Base de données MediSecure initialisée avec succès';
  RAISE NOTICE 'Utilisateur admin créé : admin@medisecure.com / Admin123!';
  RAISE NOTICE 'Médecins créés : doctor1@medisecure.com et doctor2@medisecure.com (mot de passe: Admin123!)';
  RAISE NOTICE 'Patients de test créés';
END $$;