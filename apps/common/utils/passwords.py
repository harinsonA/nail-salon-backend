import string

from django.core.exceptions import ValidationError

SPECIAL_CHARACTERS = frozenset(string.punctuation)


class PasswordPolicyValidator:
    min_length = 8
    max_length = 20
    min_uppercase = 1
    min_digits = 3
    min_special = 1

    def validate(self, password, user=None):
        message = self.password_policy_error(password)
        if message:
            raise ValidationError(message, code="password_policy")

    def get_help_text(self):
        return (
            f"Entre {self.min_length} y {self.max_length} caracteres, con al menos "
            f"{self.min_uppercase} mayúscula, {self.min_digits} números y "
            f"{self.min_special} carácter especial."
        )

    def password_policy_error(self, password):
        if not self.min_length <= len(password) <= self.max_length:
            return f"La contraseña debe tener entre {self.min_length} y {self.max_length} caracteres."
        missing = []
        if sum(character.isupper() for character in password) < self.min_uppercase:
            missing.append(f"{self.min_uppercase} mayúscula")
        if sum(character.isdigit() for character in password) < self.min_digits:
            missing.append(f"{self.min_digits} números")
        if sum(character in SPECIAL_CHARACTERS for character in password) < self.min_special:
            missing.append(f"{self.min_special} carácter especial")
        if not missing:
            return ""
        requirements = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} y {missing[-1]}"
        return f"La contraseña debe incluir al menos {requirements}."
