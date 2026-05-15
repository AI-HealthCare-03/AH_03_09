from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(40) NOT NULL,
    "hashed_password" VARCHAR(128) NOT NULL,
    "name" VARCHAR(20) NOT NULL,
    "gender" VARCHAR(6) NOT NULL,
    "birthday" DATE NOT NULL,
    "phone_number" VARCHAR(11) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "last_login" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gender" IS 'MALE: MALE\nFEMALE: FEMALE';
CREATE TABLE IF NOT EXISTS "chat_sessions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(200) NOT NULL DEFAULT '새 대화',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "chat_messages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "role" VARCHAR(10) NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "session_id" UUID NOT NULL REFERENCES "chat_sessions" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "chat_messages"."role" IS 'USER: user\nASSISTANT: assistant';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmm1v4jgQgP9KlE97Uq+CQClXnVbirbvcFjgVuF3tdhWZxAWricPGzrZoxX8/20mI89"
    "rQbcuL+qXAeCaxn5mMJ+P+Um3HhBY5bUEXGQv1QvmlYmBD9iUxcqKoYLmM5FxAwcwSqiDS"
    "mRHqAoMy6S2wCGQiExLDRUuKHMyk2LMsLnQMpojwPBJ5GP3woE6dOaQL6LKBb9+ZGGETPk"
    "AS/lze6bcIWmZsqsjk9xZyna6WQtbH9FIo8rvNdMOxPBtHyssVXTh4o40w5dI5xNAFFPLL"
    "U9fj0+ezC9YZrsifaaTiT1GyMeEt8CwqLbckA8PBnB+bDRELnPO7/KlV6+f1Zq1RbzIVMZ"
    "ON5HztLy9au28oCAwn6lqMAwp8DYEx4vYTuoRPKQWvswBuNj3JJIGQTTyJMARWxDAURBCj"
    "wHkmijZ40C2I55QHuHZ2VsDsv9Z152Pr+h3T+oOvxmHB7Mf4MBjS/DEONgLJH40tIAbqhw"
    "mwWqmUAMi0cgGKsThAdkcK/WcwDvGf8WiYDVEySYCcYrbAbyYy6IliIUK/7yfWAop81XzS"
    "NiE/LBneu0HrS5Jr52rUFhQcQueuuIq4QJsx5inz9k56+LlgBoy7e+CaemrE0Zw83fSQrd"
    "lJCcBgLljxFfP1BZvIlIiEntpchLxwa/GYBtmvnaWN5ke0ufylabXauVapNZpn9fPzs2Zl"
    "s8ukh4q2m3b/A99xYrH5+BYEbYCsbXLnxuAws2e9TPKs5+fOeip1LgBZQFNfAkLuHTcjXv"
    "NZZpgeJtWq1iyzJ2nN/D2Jj8XBis8taIb6h4lQKxOYWn5gaqnAZCs2/fSeJtjDni0o9tmU"
    "ADZgimZkvWOe6qB11btQ+N8bfNnzf/mf6hM4N0pgbuRSbiQhz5BLFyZYpTF3GZzsQJVtEn"
    "BZnoYU2fCUf9nPsC3g121Negk+S7Y6qLNom+WFYjajpN1hPtTVapm0WM3PitVkvCGisyIM"
    "/czIjG3HsSDAOYWRbJeAOWOGL0VzUzQ9d6y1R6OrWIne7ieKn+F00O4xvIIuU0I0VhPFmZ"
    "o2yngPfxRpaPaKRLetvneC1AKE6pYzz4LaDXJcNtW4ZVF65F9KQA4icD8y5KQ/6I0nrcG/"
    "Mc48b/IRTUhXCWlqO9pcRPncn3xU+E/l62jYS76EbvQmX1U+J+BRR8fOPQtbedmhOBTFGw"
    "Mu5Gh1kNEbKHZk3PIZHLmLbM7WYI6wtQri6EA8G4R8oWO9pflEx8Yt3xy7U8eKyW/RZZKe"
    "7AWgOoGEt5NJxtYXmF9+uoYWoNk956CNxMo4OvavtJ/uXocxHEplci/VdONUBowKEI2eVO"
    "9NHj4pasEJR9m+5lsr7nhbcS6rNZ/6th7a7vpdfTruXV8ovGl8g1vjcZ/lsuHkQgEsN/CZ"
    "06e8sVfLnXcUHHeUPu2YwIecaM4/7djbV9GiPa33ZVJ8vrHZ0q5Gww+hevLQY/1WKh5fRZ"
    "EuFYMiQc/aAabTfjfbqXGrhFM9D5mn3HY/nVngPPGU1HxvyJzFYjIO/FIY0wwvHReiOf4E"
    "V6kkf2T1FhO74H5TXCRihH1hy4N+T6HTGnda3Z663s2JqYw4p3iTPPBI8SZX2ftTvOU/us"
    "//yD5ewal/33rY4AwUcSf+p/5e3cUzXFSkUUTzqrRslhuD1ysb1BvPqBhN5cab1SqVG89s"
    "nNV/A2TynKrcQVXRSVW6IHsrHY6zdHjrMh2FY4PJS35lb3iZ9WBRR0AyerwtsCcefLXOQE"
    "Hh6JGss9Otq8bwn732j3LZclEKoG1rRamCkzppv9fylLp3h8P0BVqe6/8BbMn/LA=="
)
