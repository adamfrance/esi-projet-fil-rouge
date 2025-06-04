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

-- Vérification de l'installation
DO $$
BEGIN
  RAISE NOTICE 'Base de données MediSecure initialisée avec succès';
  RAISE NOTICE 'Utilisateur admin créé : admin@medisecure.com / Admin123!';
  RAISE NOTICE 'Médecins créés : doctor1@medisecure.com et doctor2@medisecure.com (mot de passe: Admin123!)';
  RAISE NOTICE 'Patients de test créés';
END $$;