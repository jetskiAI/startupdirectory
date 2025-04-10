from marshmallow import Schema, fields, validate


class FounderSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    title = fields.Str(validate=validate.Length(max=100))
    linkedin_url = fields.Str(validate=validate.Length(max=255))
    twitter_url = fields.Str(validate=validate.Length(max=255))
    startup_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class StartupSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str()
    year_founded = fields.Int(required=True)
    url = fields.Str(validate=validate.Length(max=255))
    logo_url = fields.Str(validate=validate.Length(max=255))
    source = fields.Str(validate=validate.Length(max=50))
    industry = fields.Str(validate=validate.Length(max=100))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested relationships
    founders = fields.List(fields.Nested(FounderSchema), dump_only=True)


class StartupQuerySchema(Schema):
    year = fields.Int()
    source = fields.Str()
    industry = fields.Str()
    page = fields.Int(missing=1)
    per_page = fields.Int(missing=20)
