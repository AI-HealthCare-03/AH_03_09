from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `chat_sessions` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(100) NOT NULL DEFAULT '새 대화',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_chat_ses_users_520002c0` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role` VARCHAR(9) NOT NULL COMMENT 'USER: USER\nASSISTANT: ASSISTANT',
    `content` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `session_id` BIGINT NOT NULL,
    CONSTRAINT `fk_chat_mes_chat_ses_0d4a2737` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `chat_sessions`;
        DROP TABLE IF EXISTS `chat_messages`;"""


MODELS_STATE = (
    "eJztmltz2joQgP8K46d2JqcDDrfkDQhpOQ3QCeS006bjEbYCmtgyteQmTIf/fiT5Jl9j0i"
    "Rchhcwq11b+rTeXa/5o1i2AU3yoQMdpC+U88ofBQMLsoPEyElFActlJOcCCmamUAWRzoxQ"
    "B+iUSe+ASSATGZDoDlpSZGMmxa5pcqGtM0WE55HIxeiXCzVqzyFdQIcN/PjJxAgb8BGS4O"
    "fyXrtD0DRiU0UGv7aQa3S1FLIBppdCkV9tpum26Vo4Ul6u6MLGoTbClEvnEEMHUMhPTx2X"
    "T5/Pzl9nsCJvppGKN0XJxoB3wDWptNySDHQbc35sNkQscM6v8o9aq7fq7dNmvc1UxExCSW"
    "vtLS9au2coCIymylqMAwo8DYEx4vYbOoRPKQWvtwBONj3JJIGQTTyJMABWxDAQRBAjx3kh"
    "ihZ41EyI55Q7uNpoFDD7r3Pd+9S5fse03vPV2MyZPR8f+UOqN8bBRiD5rbEBRF99PwHWqt"
    "USAJlWLkAxFgfIrkihdw/GIf47GY+yIUomCZA3mC3wh4F0elIxEaE/dxNrAUW+aj5pi5Bf"
    "pgzv3bDzLcm1dzXuCgo2oXNHnEWcoMsY85B5dy/d/FwwA/r9A3AMLTViq3aebnrIUq2kBG"
    "AwF6z4ivn6/CRyQ0RATyUXIS9MLS7TILuVWbpofkDJ5UxVT09bavW02W7UW61GuxpmmfRQ"
    "UbrpDj7yjBPzzadTELQAMjeJnaHBfkbPepngWc+PnfVU6FwAsoCGtgSEPNhOhr/ms8ww3U"
    "+qNbVdJiep7fycxMfiYMX3BjQD/f1EqJZxTDXfMdWUY7IVG154TxPsY9cSFAdsSgDrMEUz"
    "st4yT2XYueqfV/jnLb7se7+8b+UZnJslMDdzKTeTkGfIoQsDrNKYLxicbEeVbRJwWZyGFF"
    "nwAz/YTbct4HfRmfYTfJZsdVBj3jbLc8VsRkm7/bypa7UyYbGWHxVrSX9DRGNFGPqdERm7"
    "tm1CgHMKI9kuAXPGDF+LZlg0vbSvdcfjq1iJ3h0kip/RzbDbZ3gFXaaEaKwmijM1LJTxHP"
    "4k0sDsDYluWn1vBakJCNVMe54F9cKPcdlU45ZF4ZEflIDse+BuRMjpYNifTDvDLzHOPG7y"
    "EVVIVwlpKh2FJ6l8HUw/VfjPyvfxqJ98CA31pt8VPifgUlvD9gNzW3nZgTgQxRsDDuRoNZ"
    "DRGyjeyLjlC2zkNqI5W4MxxubK96M92Vnf5Qs31l0az9zYuOVxY7e6sWLyG3SZpDt7AahG"
    "IOHtZJKR+nzzy8/X0AQ0u+fst5FYGUcn3pl2c7vXgQ8HUpncazXdOJUhowJEoyfVe5OHT4"
    "pacGKjLE/z2Io73Facw2rN5z6tB7bbfla/mfSvzyv88xZ3JpMBi2Wj6XklPHzOE/tZiWeo"
    "s9xHqLPSrzqm8DHHlfNfdezsc2hRQut/mxa/3Ajz2dV49DFQT77xWB/rxMMrJ9J1ol8haJ"
    "uG/7jd02lgRzbyzTJBqmZLIU/zvrQdiOb4M1ylssGBFWZM7ICHsApJeBM7YMuDXvOh15n0"
    "Ohd9Zb2dV6sy4pwqT9qBJ6o8uRw/VnkHWeVRRPPKvGzCocHblR7KratX9Xbl1p2dVqu3rt"
    "Fs1JW/AP8G/185lh+HWX4c21QHsbH+5KV9JdDZuKaUjI4F5QYFpUuyXr5uXE0G/xbbPcpl"
    "y0jJgTatIaXKTmrF/V3PVGr/7Q/TV+iZrv8HRrcIXA=="
)
