from urllib.parse import quote, urlencode

"""========================================================================="""
# region ........ Constants

WHATSAPP_APP_URL = "https://wa.me"
WHATSAPP_WEB_URL = "https://web.whatsapp.com/send"


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Functions


def get_whatsapp_url(phone_number: str, message: str = "", app: bool = False) -> str:
    digits = "".join(character for character in phone_number if character.isdigit())
    params = {"text": message} if message else {}
    if app:
        url = f"{WHATSAPP_APP_URL}/{digits}"
    else:
        url = WHATSAPP_WEB_URL
        params = {"phone": digits, **params}
    if not params:
        return url
    return f"{url}?{urlencode(params, quote_via=quote)}"


# endregion
"""========================================================================="""
