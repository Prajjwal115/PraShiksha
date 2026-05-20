-- Prashiksha - MySQL Schema
-- Run this file to initialize the database

CREATE DATABASE IF NOT EXISTS ai_tutor_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_tutor_hub;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    language_pref VARCHAR(10) DEFAULT 'en',  -- 'en', 'hi', 'mr', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Sessions table (one per study session)
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic VARCHAR(255) NOT NULL,
    response_type ENUM('explanation','qa','roadmap','summary','practice') DEFAULT 'explanation',
    status ENUM('active','completed','paused') DEFAULT 'active',
    understanding_level FLOAT DEFAULT 0.5,  -- 0.0 to 1.0
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Messages table (full chat history per session)
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    role ENUM('user','assistant','system') NOT NULL,
    content TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Flashcard quiz attempts
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    topic VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    user_answer TEXT,
    is_correct BOOLEAN DEFAULT FALSE,
    score FLOAT DEFAULT 0.0,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- User progress per topic (cross-session)
CREATE TABLE IF NOT EXISTS user_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic VARCHAR(255) NOT NULL,
    mastery_score FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    sessions_count INT DEFAULT 0,
    last_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_topic (user_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Roadmap steps (for roadmap response type)
CREATE TABLE IF NOT EXISTS roadmap_steps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    step_number INT NOT NULL,
    step_title VARCHAR(255) NOT NULL,
    step_content TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Insert a default demo user
INSERT IGNORE INTO users (name, email, language_pref) VALUES ('Demo Student', 'demo@prashiksha.com', 'en');

SELECT 'Schema created successfully!' AS status;
