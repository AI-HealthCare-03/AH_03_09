from tortoise import fields, models


class Medication(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="medications",
        on_delete=fields.CASCADE,
    )
    document = fields.ForeignKeyField(
        "models.MedicalDocument",
        related_name="medications",
        on_delete=fields.SET_NULL,
        null=True,
    )
    medication_name = fields.CharField(max_length=200)
    dosage = fields.CharField(max_length=100)
    frequency = fields.CharField(max_length=100)
    duration = fields.CharField(max_length=100)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    side_effects = fields.TextField(null=True)
    precautions = fields.TextField(null=True)
    interaction_warnings = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medications"
