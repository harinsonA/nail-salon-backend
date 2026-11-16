class ApiRequest:
    PREFIX = "/api/"

    @classmethod
    def matches(cls, request) -> bool:
        return request.path_info.startswith(cls.PREFIX)
