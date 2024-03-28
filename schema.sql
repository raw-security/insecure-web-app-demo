CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    account_balance REAL DEFAULT 100.0
);

CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    theme TEXT,
    price REAL NOT NULL,
    owner_id INTEGER,
    created_by INTEGER,

    FOREIGN KEY (owner_id) REFERENCES users(id)
    FOREIGN KEY (created_by) REFERENCES users(id)
);


INSERT INTO users (id, username, password, account_balance) VALUES
    (1, 'admin', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 1000000000.00);

INSERT INTO items (title, description, price, owner_id, created_by) VALUES
    ('Magischer Admin Zauberstab', 'Kann alles.', 1000000.00, 1, 1),
    ('Langweilige Tasse', 'Tasse für alle Anlässe. Perfekt für Kaffee geeignet. Nicht wärmeresistent.', 5.00, NULL, 1),
    ('Zauberwürfel', 'Spielzeug für alle schüchternen Angeber. Extra schwer mit 24 Farben!', 15.99, NULL, 1),
    ('Heiße Kartoffel', 'Jeder will sie haben! Benötigt 15 AAA Batterien (nicht enthalten).', 9.99, NULL, 1);
