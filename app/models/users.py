from tortoise import fields, models


class User(models.Model):
    id = fields.BigIntField(primary_key=True)
    kakao_id = fields.CharField(max_length=64, unique=True)
    email = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=50, null=True)
    gender = fields.CharField(max_length=10, null=True)  # "male" | "female"
    age_range = fields.CharField(max_length=20, null=True)  # "20~29" 등
    birthday = fields.CharField(max_length=4, null=True)  # "MMDD"
    birthyear = fields.CharField(max_length=4, null=True)  # "YYYY"
    phone_number = fields.CharField(max_length=30, null=True)
    is_active = fields.BooleanField(default=True)
    deleted_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
