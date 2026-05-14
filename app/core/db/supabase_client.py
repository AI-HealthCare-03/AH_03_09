from supabase import Client, create_client

from app.core import config


def get_supabase() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


supabase: Client = get_supabase()
