import re
from abc import abstractmethod

class BaseEscaper:
    def __init__(self, escape_symbol: str):
        if len(escape_symbol) != 1:
            raise ValueError("Escape symbol must be a single character")
        self.escape_symbol = escape_symbol

    @abstractmethod
    def escape(self, text: str) -> str:
        pass


class EscapeError(Exception):
    pass


class EMailEscaper(BaseEscaper):
    def escape(self, text: str) -> str:
        splitted_text = text.split('@')
        if len(splitted_text) != 2:
            raise EscapeError(f"{text} is not a valid email address")
        return f'{self.escape_symbol * len(splitted_text[0])}@{splitted_text[1]}'


class PhoneEscaper(BaseEscaper):
    def __init__(self, escape_symbol: str, n: int):
        super().__init__(escape_symbol)
        self.n = n

    def escape(self, text: str) -> str:
        if not re.fullmatch(r'(?:\+7|8)(?:-? *\d){10}', text):
            #  можно усложнить регулярку на номер телефона, чтобы принимать больше форматов номеров
            raise EscapeError(f"{text} is not a valid phone number")
        text_ls = list(re.sub(r" +", " ", text))
        replaced = 0
        for i, char in reversed(list(enumerate(text_ls))):
            if char.isdigit():
                text_ls[i] = self.escape_symbol
                replaced += 1
            if replaced == self.n:
                break
        return ''.join(text_ls)


class SkypeEscaper(BaseEscaper):
    # предположительно никнейм в скайпе должен иметь от 6 до 32 символов
    # и состоять только из букв, чисел, и символов .,-_
    # (начинаться может только на букву)
    def escape(self, text: str) -> str:
        skype_re = re.compile(r"skype:[a-zA-Z][a-zA-Z0-9.,\-_]{5,31}")
        if not re.search(skype_re, text):
            raise EscapeError(f"valid skype link not found in {text}")
        return re.sub(skype_re, f"skype:{self.escape_symbol * 3}", text)
