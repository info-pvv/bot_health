# migrations/versions/002_add_updated_at.py
migration = {
    'id': '002_add_updated_at',
    'description': 'Add updated_at column to users table',
    'up': [
        """
        ALTER TABLE users 
        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """,
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        """
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users 
        FOR EACH ROW 
        EXECUTE FUNCTION update_updated_at_column();
        """
    ],
    'down': [
        "DROP TRIGGER IF EXISTS update_users_updated_at ON users;",
        "DROP FUNCTION IF EXISTS update_updated_at_column;",
        "ALTER TABLE users DROP COLUMN IF EXISTS updated_at;"
    ]
}