    -- :name create_redirect_table
        CREATE TABLE "redirect"(
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "owner" INTEGER NOT NULL,
        "url" TEXT NOT NULL,
        "createTime" INTEGER,
        "lastUsed" INTEGER,
        "hit" INTEGER DEFAULT 0,
        "namespace" INTEGER NOT NULL,
        "keyword" TEXT,
        FOREIGN KEY(owner) REFERENCES owner(id),
        FOREIGN KEY(namespace) REFERENCES namespace(id)
        );
