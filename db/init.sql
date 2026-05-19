CREATE TABLE IF NOT EXISTS lecturas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temp_ambiente FLOAT NOT NULL,
    temp_corporal FLOAT NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lecturas (temp_ambiente, temp_corporal) VALUES (24.5, 36.6);
