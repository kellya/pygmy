    -- :name create_owner_table
        CREATE TABLE "owner"(
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "username" TEXT NOT NULL UNIQUE,
        "email" TEXT
        );
