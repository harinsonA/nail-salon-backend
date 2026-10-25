from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants


class Country(TextChoices):
    ARGENTINA = "AR", "Argentina"
    CHILE = "CL", "Chile"
    COLOMBIA = "CO", "Colombia"
    ECUADOR = "EC", "Ecuador"
    MEXICO = "MX", "México"
    PERU = "PE", "Perú"
    REPUBLICA_DOMINICANA = "DO", "República Dominicana"
    URUGUAY = "UY", "Uruguay"
    VENEZUELA = "VE", "Venezuela"


class CountryPhonePrefix(TextChoices):
    ARGENTINA = "+54", "AR (+54)"
    CHILE = "+56", "CL (+56)"
    COLOMBIA = "+57", "CO (+57)"
    ECUADOR = "+593", "EC (+593)"
    MEXICO = "+52", "MX (+52)"
    PERU = "+51", "PE (+51)"
    REPUBLICA_DOMINICANA = "+1-809", "DO (+1-809)"
    URUGUAY = "+598", "UY (+598)"
    VENEZUELA = "+58", "VE (+58)"


class CountryPhoneLength(TextChoices):
    ARGENTINA = CountryPhonePrefix.ARGENTINA, "10"
    CHILE = CountryPhonePrefix.CHILE, "8"
    COLOMBIA = CountryPhonePrefix.COLOMBIA, "7"
    ECUADOR = CountryPhonePrefix.ECUADOR, "8"
    MEXICO = CountryPhonePrefix.MEXICO, "10"
    PERU = CountryPhonePrefix.PERU, "8"
    REPUBLICA_DOMINICANA = CountryPhonePrefix.REPUBLICA_DOMINICANA, "7"
    URUGUAY = CountryPhonePrefix.URUGUAY, "7"
    VENEZUELA = CountryPhonePrefix.VENEZUELA, "7"


COUNTRY_OPERATOR_PREFIX = {
    CountryPhonePrefix.ARGENTINA: {"9"},
    CountryPhonePrefix.CHILE: {"9"},
    CountryPhonePrefix.COLOMBIA: {
        "300",
        "301",
        "302",
        "303",
        "304",
        "305",
        "310",
        "311",
        "312",
        "313",
        "314",
        "315",
        "316",
        "317",
        "318",
        "319",
        "320",
        "321",
        "322",
        "323",
        "324",
        "350",
        "351",
    },
    CountryPhonePrefix.ECUADOR: {"09"},
    CountryPhonePrefix.MEXICO: {},
    CountryPhonePrefix.PERU: {"9"},
    CountryPhonePrefix.REPUBLICA_DOMINICANA: {"809", "829", "849"},
    CountryPhonePrefix.URUGUAY: {"09"},
    CountryPhonePrefix.VENEZUELA: {"424", "414", "412", "416", "426"},
}


# endregion
"""========================================================================="""
