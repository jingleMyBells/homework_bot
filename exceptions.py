class NoEnvVar(Exception):
    def __str__(self):
        return 'Нет переменных окружения'

class HWWrongStatus(Exception):
    pass
