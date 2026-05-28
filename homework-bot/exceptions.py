class ExceedCountHomeworkException(ValueError):
    pass


class VarAvailabilityException(Exception):
    pass


class ServerAvailabilityException(Exception):
    pass


class ResponseTypeException(TypeError):
    pass


class ResponseStructureException(Exception):
    pass


class NotNecessaryKeyException(KeyError):
    pass


class SendTelegramMessageException(Exception):
    pass
